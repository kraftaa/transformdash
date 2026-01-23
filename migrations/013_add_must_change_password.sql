-- Migration: Add must_change_password flag for security
-- Created: 2026-01-22
-- Purpose: Force password change for default/initial credentials

-- Add must_change_password column
ALTER TABLE users
ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;

-- Set flag for existing admin user (default credentials)
UPDATE users SET must_change_password = TRUE WHERE username = 'admin';

COMMENT ON COLUMN users.must_change_password IS 'If TRUE, user must change password on next login';
