-- Migration 012: Create demo user for public demo
-- This user has Analyst role (can view and run, but not delete)

-- Create demo user (password: 'demo')
-- Password hash for 'demo' using bcrypt (rounds=12)
INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser)
VALUES (
    'demo',
    'demo@transformdash.demo',
    '$2b$12$gVK0OQ.3dfqKaTZFicqP.OwWHsgAaMoMFLZY4Vlluv4Shm3gWQWFm',  -- password: 'demo'
    'Demo User',
    TRUE,
    FALSE
)
ON CONFLICT (username) DO UPDATE SET
    password_hash = EXCLUDED.password_hash,
    is_active = TRUE;

-- Assign Analyst role to demo user (can view and run, but not delete)
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id
FROM users u
CROSS JOIN roles r
WHERE u.username = 'demo' AND r.name = 'Analyst'
ON CONFLICT DO NOTHING;
