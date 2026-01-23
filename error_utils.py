"""
Error Handling Utilities
Provides secure error handling that logs details server-side
and returns safe messages to users without leaking internal info.
"""
import logging
import traceback
import uuid
from fastapi import HTTPException


def log_and_raise_error(operation: str, error: Exception, status_code: int = 500) -> None:
    """
    Log error details server-side and raise a safe HTTPException.
    Returns generic message with error ID to avoid leaking internal details.

    Args:
        operation: Description of what operation was being attempted
        error: The exception that was caught
        status_code: HTTP status code to return (default 500)
    """
    error_id = str(uuid.uuid4())[:8]
    logging.error(f"[{error_id}] Error in {operation}: {error}\n{traceback.format_exc()}")
    raise HTTPException(
        status_code=status_code,
        detail=f"An internal error occurred. Reference ID: {error_id}"
    )
