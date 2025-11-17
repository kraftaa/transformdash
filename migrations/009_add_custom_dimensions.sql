-- Migration: Add custom_width and custom_height columns for drag-to-resize functionality
-- Created: 2025-11-17
-- Purpose: Allow users to set custom dimensions for charts by dragging resize handles

-- Add custom dimension columns to dashboard_charts table
ALTER TABLE dashboard_charts
ADD COLUMN IF NOT EXISTS custom_width INTEGER,
ADD COLUMN IF NOT EXISTS custom_height INTEGER;

-- Add CHECK constraints to ensure reasonable values (250-5000px range)
ALTER TABLE dashboard_charts
ADD CONSTRAINT check_custom_width CHECK (custom_width IS NULL OR (custom_width >= 250 AND custom_width <= 5000));

ALTER TABLE dashboard_charts
ADD CONSTRAINT check_custom_height CHECK (custom_height IS NULL OR (custom_height >= 200 AND custom_height <= 5000));

-- Add comments for documentation
COMMENT ON COLUMN dashboard_charts.custom_width IS 'Custom chart width in pixels (overrides size presets when set)';
COMMENT ON COLUMN dashboard_charts.custom_height IS 'Custom chart height in pixels (overrides size presets when set)';

-- Note: NULL values mean "use default size based on size column"
-- When custom_width/custom_height are set, they take precedence over the size preset
