-- Migration: Make model_name nullable in model_schedules table
-- Since we now use the schedule_models junction table for model associations,
-- the model_name column in model_schedules is deprecated but kept for backward compatibility

-- Make model_name nullable
ALTER TABLE model_schedules
ALTER COLUMN model_name DROP NOT NULL;

-- Add a comment explaining this column is deprecated
COMMENT ON COLUMN model_schedules.model_name IS 'Deprecated: Use schedule_models junction table instead. Kept for backward compatibility.';
