#!/bin/bash
# Run all database migrations locally
# Usage: ./run_migrations.sh

set -e

echo "Running TransformDash migrations..."

# Load environment variables
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Default values if not in .env
TRANSFORMDASH_HOST=${TRANSFORMDASH_HOST:-localhost}
TRANSFORMDASH_PORT=${TRANSFORMDASH_PORT:-5432}
TRANSFORMDASH_DB=${TRANSFORMDASH_DB:-transformdash}
TRANSFORMDASH_USER=${TRANSFORMDASH_USER:-postgres}

echo "Database: $TRANSFORMDASH_DB"
echo "Host: $TRANSFORMDASH_HOST:$TRANSFORMDASH_PORT"
echo ""

# Run migrations in order
for migration in migrations/*.sql; do
    echo "Applying $(basename $migration)..."
    PGPASSWORD=$TRANSFORMDASH_PASSWORD psql -h $TRANSFORMDASH_HOST -p $TRANSFORMDASH_PORT -U $TRANSFORMDASH_USER -d $TRANSFORMDASH_DB -f "$migration" 2>&1 | grep -v "already exists" || true
done

echo ""
echo "All migrations applied successfully!"
