-- Migration: Create schedules table
-- Description: Add support for scheduling model runs with cron expressions

CREATE TABLE IF NOT EXISTS model_schedules (
    id SERIAL PRIMARY KEY,
    schedule_name VARCHAR(500) NOT NULL,
    model_name VARCHAR(500) NOT NULL,
    cron_expression VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    timezone VARCHAR(50) DEFAULT 'UTC',

    -- Execution settings
    max_retries INTEGER DEFAULT 0,
    retry_delay_seconds INTEGER DEFAULT 300,
    timeout_seconds INTEGER DEFAULT 3600,

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255),
    last_run_at TIMESTAMP,
    next_run_at TIMESTAMP,

    -- Constraints
    CONSTRAINT unique_schedule_name UNIQUE(schedule_name)
);

CREATE TABLE IF NOT EXISTS schedule_runs (
    id SERIAL PRIMARY KEY,
    schedule_id INTEGER REFERENCES model_schedules(id) ON DELETE CASCADE,
    model_name VARCHAR(500) NOT NULL,
    status VARCHAR(50) NOT NULL, -- 'running', 'completed', 'failed', 'timeout'

    -- Execution details
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    execution_time_seconds FLOAT,

    -- Results
    dependencies_run INTEGER DEFAULT 0,
    models_completed INTEGER DEFAULT 0,
    models_failed INTEGER DEFAULT 0,
    models_skipped INTEGER DEFAULT 0,

    -- Error tracking
    error_message TEXT,
    error_traceback TEXT,

    -- Retry tracking
    retry_count INTEGER DEFAULT 0,
    is_retry BOOLEAN DEFAULT FALSE
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_schedules_active ON model_schedules(is_active);
CREATE INDEX IF NOT EXISTS idx_schedules_model ON model_schedules(model_name);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON model_schedules(next_run_at);
CREATE INDEX IF NOT EXISTS idx_schedule_runs_schedule_id ON schedule_runs(schedule_id);
CREATE INDEX IF NOT EXISTS idx_schedule_runs_status ON schedule_runs(status);
CREATE INDEX IF NOT EXISTS idx_schedule_runs_started_at ON schedule_runs(started_at DESC);

-- Create view for schedule status with last run info
CREATE OR REPLACE VIEW v_schedule_status AS
SELECT
    s.id,
    s.schedule_name,
    s.model_name,
    s.cron_expression,
    s.description,
    s.is_active,
    s.timezone,
    s.created_at,
    s.updated_at,
    s.last_run_at,
    s.next_run_at,

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

COMMENT ON TABLE model_schedules IS 'Stores scheduling configuration for transformation models';
COMMENT ON TABLE schedule_runs IS 'Logs all scheduled execution runs and their results';
COMMENT ON VIEW v_schedule_status IS 'Combined view of schedules with their latest run status';
