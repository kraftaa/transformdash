-- Migration: Add support for multiple models per schedule
-- Description: Create junction table for many-to-many relationship between schedules and models

-- Create junction table for schedule-model relationship
CREATE TABLE IF NOT EXISTS schedule_models (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES model_schedules(id) ON DELETE CASCADE,
    model_name VARCHAR(500) NOT NULL,
    execution_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure no duplicate models in the same schedule
    CONSTRAINT unique_schedule_model UNIQUE(schedule_id, model_name)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_schedule_models_schedule_id ON schedule_models(schedule_id);
CREATE INDEX IF NOT EXISTS idx_schedule_models_order ON schedule_models(schedule_id, execution_order);

-- Migrate existing schedules to use the new table
-- For each existing schedule with a model_name, create an entry in schedule_models
INSERT INTO schedule_models (schedule_id, model_name, execution_order)
SELECT id, model_name, 0
FROM model_schedules
WHERE model_name IS NOT NULL
ON CONFLICT (schedule_id, model_name) DO NOTHING;

-- Drop and recreate the view to include model list
DROP VIEW IF EXISTS v_schedule_status;
CREATE VIEW v_schedule_status AS
SELECT
    s.id,
    s.schedule_name,
    s.model_name as legacy_model_name, -- Keep for backward compatibility
    s.cron_expression,
    s.description,
    s.is_active,
    s.timezone,
    s.created_at,
    s.updated_at,
    s.last_run_at,
    s.next_run_at,

    -- Model list (comma-separated)
    COALESCE(
        (SELECT string_agg(sm.model_name, ', ' ORDER BY sm.execution_order, sm.model_name)
         FROM schedule_models sm
         WHERE sm.schedule_id = s.id),
        s.model_name
    ) as models,

    -- Model count
    COALESCE(
        (SELECT COUNT(*) FROM schedule_models sm WHERE sm.schedule_id = s.id),
        CASE WHEN s.model_name IS NOT NULL THEN 1 ELSE 0 END
    ) as model_count,

    -- Last run details
    lr.id as last_run_id,
    lr.status as last_run_status,
    lr.started_at as last_run_started_at,
    lr.completed_at as last_run_completed_at,
    lr.execution_time_seconds as last_run_duration,
    lr.error_message as last_run_error,

    -- Statistics
    (SELECT COUNT(*) FROM schedule_runs WHERE schedule_id = s.id) as total_runs,
    (SELECT COUNT(*) FROM schedule_runs WHERE schedule_id = s.id AND status = 'completed') as successful_runs,
    (SELECT COUNT(*) FROM schedule_runs WHERE schedule_id = s.id AND status = 'failed') as failed_runs
FROM model_schedules s
LEFT JOIN LATERAL (
    SELECT * FROM schedule_runs
    WHERE schedule_id = s.id
    ORDER BY started_at DESC
    LIMIT 1
) lr ON true
ORDER BY s.created_at DESC;

COMMENT ON TABLE schedule_models IS 'Junction table for many-to-many relationship between schedules and models';
COMMENT ON COLUMN schedule_models.execution_order IS 'Order in which models should be executed (0 = automatic based on dependencies)';
