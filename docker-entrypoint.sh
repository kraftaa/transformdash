#!/bin/bash
set -e

echo "Starting TransformDash..."

# Wait for postgres to be ready
echo "Waiting for PostgreSQL to be ready..."
while ! pg_isready -h "$TRANSFORMDASH_HOST" -p "$TRANSFORMDASH_PORT" -U "$TRANSFORMDASH_USER" > /dev/null 2>&1; do
    sleep 1
done
echo "PostgreSQL is ready"

# Check if this is first startup by checking if visualization tables exist
echo "Checking if database is initialized..."
if ! python -c "
from postgres import PostgresConnector
try:
    with PostgresConnector() as pg:
        pg.execute('SELECT 1 FROM data_connections LIMIT 1')
    print('already_initialized')
except:
    print('needs_initialization')
" | grep -q "already_initialized"; then
    echo "First startup detected - initializing database..."

    # Run visualization setup (creates data_connections table)
    echo "Setting up visualization schema..."
    python setup_visualization_db.py

    # Run migrations (creates users, charts, datasets, schedules tables)
    echo "Running database migrations..."
    for migration in /app/migrations/*.sql; do
        echo "Applying $(basename $migration)..."
        PGPASSWORD=$TRANSFORMDASH_PASSWORD psql -h $TRANSFORMDASH_HOST -p $TRANSFORMDASH_PORT -U $TRANSFORMDASH_USER -d $TRANSFORMDASH_DB -f "$migration" 2>&1 | grep -v "already exists" || true
    done

    # Run sample data seeding
    echo "Seeding sample e-commerce data..."
    python seed_fake_data_expanded.py

    echo "Database initialization complete"
else
    echo "Database already initialized, skipping setup"
fi

# In demo mode, always ensure sample data is loaded
if [ "$DEMO_MODE" = "true" ]; then
    echo "Demo mode detected - checking if sample data exists..."
    if ! python -c "
from postgres import PostgresConnector
try:
    with PostgresConnector() as pg:
        result = pg.execute('SELECT COUNT(*) FROM raw.customers')
        count = result[0][0] if result else 0
        print('has_data' if count > 0 else 'needs_data')
except:
    print('needs_data')
" | grep -q "has_data"; then
        echo "No sample data found - seeding now..."
        python seed_fake_data_expanded.py
        echo "Sample data seeding complete!"
    else
        echo "Sample data already exists, skipping seeding"
    fi

    # Set up read-only permissions for demo safety
    echo "Configuring read-only protections for raw schema..."
    PGPASSWORD=$TRANSFORMDASH_PASSWORD psql -h $TRANSFORMDASH_HOST -p $TRANSFORMDASH_PORT -U $TRANSFORMDASH_USER -d $TRANSFORMDASH_DB << 'EOF'
    -- Create demo database user if not exists
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_user WHERE usename = 'demo') THEN
            CREATE USER demo WITH PASSWORD 'demo';
        END IF;
    END
    $$;

    -- Grant basic connection
    GRANT CONNECT ON DATABASE transformdash TO demo;

    -- Grant schema usage
    GRANT USAGE ON SCHEMA raw, public TO demo;

    -- raw schema: READ-ONLY (protect source data)
    GRANT SELECT ON ALL TABLES IN SCHEMA raw TO demo;
    ALTER DEFAULT PRIVILEGES IN SCHEMA raw GRANT SELECT ON TABLES TO demo;
    REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON ALL TABLES IN SCHEMA raw FROM demo;

    -- public schema: READ-WRITE (allow transformations, dashboards)
    GRANT ALL ON SCHEMA public TO demo;
    GRANT ALL ON ALL TABLES IN SCHEMA public TO demo;
    GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO demo;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO demo;
    ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO demo;

    -- Create demo application user
    INSERT INTO users (username, email, password_hash, full_name, is_active, is_superuser)
    VALUES (
        'demo',
        'demo@transformdash.demo',
        '\$2b\$12\$gVK0OQ.3dfqKaTZFicqP.OwWHsgAaMoMFLZY4Vlluv4Shm3gWQWFm',
        'Demo User',
        TRUE,
        FALSE
    )
    ON CONFLICT (username) DO UPDATE SET
        password_hash = EXCLUDED.password_hash,
        is_active = TRUE;

    -- Assign Analyst role to demo user (can view and run, but not delete)
    INSERT INTO user_roles (user_id, role_id)
    SELECT u.id, r.id FROM users u, roles r
    WHERE u.username = 'demo' AND r.name = 'Analyst'
    ON CONFLICT DO NOTHING;
EOF
    echo "Read-only protections configured - raw schema is protected!"
    echo "Demo user created: demo / demo"
fi

# Start the application
echo "Starting TransformDash application..."
exec python ui/app.py
