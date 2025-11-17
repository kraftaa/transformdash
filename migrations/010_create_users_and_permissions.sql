-- Migration: Create users and permissions tables
-- Created: 2025-11-17
-- Purpose: Add user authentication and role-based access control

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(100) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Roles table
CREATE TABLE IF NOT EXISTS roles (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Permissions table
CREATE TABLE IF NOT EXISTS permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    resource VARCHAR(100) NOT NULL,  -- e.g., 'dashboards', 'models', 'datasets'
    action VARCHAR(50) NOT NULL,     -- e.g., 'read', 'write', 'delete', 'execute'
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- User-Role junction table (many-to-many)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id)
);

-- Role-Permission junction table (many-to-many)
CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- Direct user permissions (for granular control)
CREATE TABLE IF NOT EXISTS user_permissions (
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER REFERENCES permissions(id) ON DELETE CASCADE,
    granted BOOLEAN DEFAULT TRUE,  -- TRUE = grant, FALSE = revoke (overrides role permissions)
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, permission_id)
);

-- Add indexes for performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_permissions_resource_action ON permissions(resource, action);

-- Add comments
COMMENT ON TABLE users IS 'Application users with authentication credentials';
COMMENT ON TABLE roles IS 'Role definitions for grouping permissions';
COMMENT ON TABLE permissions IS 'Granular permissions for resources and actions';
COMMENT ON TABLE user_roles IS 'Many-to-many relationship between users and roles';
COMMENT ON TABLE role_permissions IS 'Many-to-many relationship between roles and permissions';
COMMENT ON TABLE user_permissions IS 'Direct user permission grants/revokes (overrides role permissions)';

COMMENT ON COLUMN users.is_superuser IS 'Superusers bypass all permission checks';
COMMENT ON COLUMN user_permissions.granted IS 'TRUE = grant permission, FALSE = explicitly revoke (overrides role)';

-- Insert default roles
INSERT INTO roles (name, description) VALUES
    ('Admin', 'Full system access including user management'),
    ('Developer', 'Can create and edit models, dashboards, and datasets'),
    ('Analyst', 'Can view dashboards and run existing models'),
    ('Viewer', 'Read-only access to dashboards')
ON CONFLICT (name) DO NOTHING;

-- Insert default permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    -- Dashboard permissions
    ('view_dashboards', 'dashboards', 'read', 'View dashboards'),
    ('create_dashboards', 'dashboards', 'write', 'Create new dashboards'),
    ('edit_dashboards', 'dashboards', 'write', 'Edit existing dashboards'),
    ('delete_dashboards', 'dashboards', 'delete', 'Delete dashboards'),

    -- Chart permissions
    ('view_charts', 'charts', 'read', 'View charts'),
    ('create_charts', 'charts', 'write', 'Create new charts'),
    ('edit_charts', 'charts', 'write', 'Edit existing charts'),
    ('delete_charts', 'charts', 'delete', 'Delete charts'),

    -- Model permissions
    ('view_models', 'models', 'read', 'View transformation models'),
    ('create_models', 'models', 'write', 'Create new models'),
    ('edit_models', 'models', 'write', 'Edit existing models'),
    ('delete_models', 'models', 'delete', 'Delete models'),
    ('execute_models', 'models', 'execute', 'Execute transformation models'),

    -- Dataset permissions
    ('view_datasets', 'datasets', 'read', 'View datasets'),
    ('create_datasets', 'datasets', 'write', 'Create new datasets'),
    ('edit_datasets', 'datasets', 'write', 'Edit existing datasets'),
    ('delete_datasets', 'datasets', 'delete', 'Delete datasets'),
    ('upload_datasets', 'datasets', 'write', 'Upload CSV datasets'),

    -- Query permissions
    ('execute_queries', 'queries', 'execute', 'Execute SQL queries'),

    -- Schedule permissions
    ('view_schedules', 'schedules', 'read', 'View scheduled jobs'),
    ('manage_schedules', 'schedules', 'write', 'Create and edit schedules'),

    -- User management permissions
    ('view_users', 'users', 'read', 'View user list and details'),
    ('manage_users', 'users', 'write', 'Create, edit, and delete users'),
    ('manage_permissions', 'permissions', 'write', 'Assign roles and permissions'),

    -- System permissions
    ('view_system', 'system', 'read', 'View system monitor and logs'),
    ('manage_connections', 'connections', 'write', 'Manage database connections')
ON CONFLICT (name) DO NOTHING;

-- Assign permissions to Admin role (all permissions)
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Admin'
ON CONFLICT DO NOTHING;

-- Assign permissions to Developer role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Developer'
AND p.name IN (
    'view_dashboards', 'create_dashboards', 'edit_dashboards', 'delete_dashboards',
    'view_charts', 'create_charts', 'edit_charts', 'delete_charts',
    'view_models', 'create_models', 'edit_models', 'delete_models', 'execute_models',
    'view_datasets', 'create_datasets', 'edit_datasets', 'delete_datasets', 'upload_datasets',
    'execute_queries',
    'view_schedules', 'manage_schedules',
    'view_system'
)
ON CONFLICT DO NOTHING;

-- Assign permissions to Analyst role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Analyst'
AND p.name IN (
    'view_dashboards', 'create_dashboards', 'edit_dashboards',
    'view_charts', 'create_charts', 'edit_charts',
    'view_models', 'execute_models',
    'view_datasets', 'create_datasets', 'upload_datasets',
    'execute_queries',
    'view_schedules',
    'view_system'
)
ON CONFLICT DO NOTHING;

-- Assign permissions to Viewer role
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id
FROM roles r
CROSS JOIN permissions p
WHERE r.name = 'Viewer'
AND p.name IN (
    'view_dashboards',
    'view_charts',
    'view_models',
    'view_datasets'
)
ON CONFLICT DO NOTHING;

-- Create default admin user (password: 'admin' - CHANGE THIS!)
-- Password hash for 'admin' using bcrypt (rounds=12)
-- This should be changed immediately after first login
INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser)
VALUES (
    'admin',
    'admin@transformdash.local',
    '$2b$12$.WksX7QO4CDQ/6peFoXnru1KQOXBTqlQ24Nudz3bbzzvEkAbBSgWu',  -- password: 'admin'
    'System Administrator',
    TRUE,
    TRUE
)
ON CONFLICT (username) DO NOTHING;

-- Assign Admin role to admin user
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.username = 'admin' AND r.name = 'Admin'
ON CONFLICT DO NOTHING;
