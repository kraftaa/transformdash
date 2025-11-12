-- Migration: Add description field to charts table

ALTER TABLE charts
ADD COLUMN IF NOT EXISTS description TEXT;

COMMENT ON COLUMN charts.description IS 'Optional description for the chart explaining what it shows';
