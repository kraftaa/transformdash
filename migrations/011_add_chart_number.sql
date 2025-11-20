-- Migration: Add chart_number column to charts table
-- Created: 2025-11-20
-- Purpose: Add sequential chart numbering for ordering

-- Add chart_number column with auto-increment
ALTER TABLE charts
ADD COLUMN IF NOT EXISTS chart_number SERIAL NOT NULL;

-- Create index for ordering
CREATE INDEX IF NOT EXISTS idx_charts_chart_number ON charts(chart_number);

-- Backfill chart_number for existing charts (ordered by created_at)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM charts WHERE chart_number IS NULL) THEN
        WITH numbered_charts AS (
            SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) as new_number
            FROM charts
        )
        UPDATE charts c
        SET chart_number = nc.new_number
        FROM numbered_charts nc
        WHERE c.id = nc.id;
    END IF;
END $$;
