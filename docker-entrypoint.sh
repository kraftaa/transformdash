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

# Start the application
echo "Starting TransformDash application..."
exec python ui/app.py
