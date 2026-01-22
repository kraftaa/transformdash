-- Migration: Add data source columns to charts table
-- Created: 2026-01-22
-- Purpose: Support connection_id, dataset_id, data_source_type, and python_code for charts

-- Add connection_id for linking charts to data connections
ALTER TABLE charts
ADD COLUMN IF NOT EXISTS connection_id VARCHAR(255);

-- Add dataset_id for linking charts to datasets
ALTER TABLE charts
ADD COLUMN IF NOT EXISTS dataset_id VARCHAR(255);

-- Add data_source_type to specify how chart gets its data
ALTER TABLE charts
ADD COLUMN IF NOT EXISTS data_source_type VARCHAR(50) DEFAULT 'sql';

-- Add python_code for Python-based chart data sources
ALTER TABLE charts
ADD COLUMN IF NOT EXISTS python_code TEXT;

-- Create index for connection lookups
CREATE INDEX IF NOT EXISTS idx_charts_connection ON charts(connection_id);
CREATE INDEX IF NOT EXISTS idx_charts_dataset ON charts(dataset_id);

COMMENT ON COLUMN charts.connection_id IS 'Reference to data_connections table';
COMMENT ON COLUMN charts.dataset_id IS 'Reference to datasets table';
COMMENT ON COLUMN charts.data_source_type IS 'Type of data source: sql, python, dataset';
COMMENT ON COLUMN charts.python_code IS 'Python code for generating chart data';
