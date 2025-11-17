"""
Authentication and Authorization Module
Handles JWT tokens, password hashing, and permission checks
"""
from datetime import datetime, timedelta
from typing import Optional, List
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a hash"""
    # Bcrypt has a 72 byte limit - truncate if necessary
    plain_password_bytes = plain_password.encode('utf-8')[:72]
    hashed_password_bytes = hashed_password.encode('utf-8') if isinstance(hashed_password, str) else hashed_password
    return bcrypt.checkpw(plain_password_bytes, hashed_password_bytes)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Bcrypt has a 72 byte limit - truncate if necessary
    password_bytes = password.encode('utf-8')[:72]
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    return hashed.decode('utf-8')


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(request: Request):
    """
    Get the current authenticated user from the request
    Supports both Authorization header and session cookie
    """
    from connection_manager import connection_manager

    token = None

    # Try to get token from Authorization header
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # Try to get token from cookie
    if not token:
        token = request.cookies.get("access_token")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode token
    payload = decode_token(token)
    username: str = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

    # Get user from database
    with connection_manager.get_connection() as pg:
        users = pg.execute("""
            SELECT id, username, email, full_name, is_active, is_superuser
            FROM users
            WHERE username = %s
        """, (username,), fetch=True)

        if not users:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        user = dict(users[0])

        # Check if user is active
        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        # Get user roles
        roles = pg.execute("""
            SELECT r.id, r.name
            FROM roles r
            INNER JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = %s
        """, (user['id'],), fetch=True)

        user['roles'] = [dict(r) for r in roles] if roles else []

        # Get user permissions (from roles)
        permissions = pg.execute("""
            SELECT DISTINCT p.name, p.resource, p.action
            FROM permissions p
            INNER JOIN role_permissions rp ON p.id = rp.permission_id
            INNER JOIN user_roles ur ON rp.role_id = ur.role_id
            WHERE ur.user_id = %s
        """, (user['id'],), fetch=True)

        user['permissions'] = [dict(p) for p in permissions] if permissions else []

        return user


async def get_optional_user(request: Request):
    """
    Get the current user if authenticated, otherwise return None
    Use this for endpoints that work with or without authentication
    """
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


def require_permission(resource: str, action: str):
    """
    Dependency to require a specific permission
    Usage: @app.get("/api/something", dependencies=[Depends(require_permission("resource", "action"))])
    """
    async def permission_checker(request: Request):
        user = await get_current_user(request)

        # Superusers bypass all permission checks
        if user.get('is_superuser'):
            return user

        # Check if user has the required permission
        has_permission = any(
            p['resource'] == resource and p['action'] == action
            for p in user.get('permissions', [])
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires {resource}:{action}"
            )

        return user

    return permission_checker


def require_any_permission(permissions: List[tuple]):
    """
    Dependency to require any of the specified permissions
    Usage: require_any_permission([("dashboards", "read"), ("dashboards", "write")])
    """
    async def permission_checker(request: Request):
        user = await get_current_user(request)

        # Superusers bypass all permission checks
        if user.get('is_superuser'):
            return user

        # Check if user has any of the required permissions
        has_permission = any(
            any(p['resource'] == resource and p['action'] == action for p in user.get('permissions', []))
            for resource, action in permissions
        )

        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: requires one of {permissions}"
            )

        return user

    return permission_checker


def require_role(role_name: str):
    """
    Dependency to require a specific role
    Usage: @app.get("/api/something", dependencies=[Depends(require_role("Admin"))])
    """
    async def role_checker(request: Request):
        user = await get_current_user(request)

        # Superusers bypass all checks
        if user.get('is_superuser'):
            return user

        # Check if user has the required role
        has_role = any(r['name'] == role_name for r in user.get('roles', []))

        if not has_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: requires {role_name} role"
            )

        return user

    return role_checker


async def authenticate_user(username: str, password: str):
    """
    Authenticate a user with username and password
    Returns user dict if successful, None otherwise
    """
    from connection_manager import connection_manager

    with connection_manager.get_connection() as pg:
        users = pg.execute("""
            SELECT id, username, email, password_hash, full_name, is_active, is_superuser
            FROM users
            WHERE username = %s
        """, (username,), fetch=True)

        if not users:
            return None

        user = dict(users[0])

        # Verify password
        if not verify_password(password, user['password_hash']):
            return None

        # Check if user is active
        if not user['is_active']:
            return None

        # Update last login
        pg.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (user['id'],))

        # Remove password hash from returned user
        del user['password_hash']

        return user
