-- Migration: Create datasets table
-- Description: Datasets are reusable data sources that can be queried by charts and SQL Lab
-- Date: 2025-11-06

-- Create datasets table
CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(500) NOT NULL,
    description TEXT,
    connection_id VARCHAR(255) REFERENCES data_connections(id),

    -- Dataset source (can be a table/model or custom SQL)
    source_type VARCHAR(50) NOT NULL DEFAULT 'table', -- 'table' or 'sql'
    table_name VARCHAR(255), -- For source_type='table'
    sql_query TEXT, -- For source_type='sql'

    -- Schema and metadata
    schema_name VARCHAR(255),
    columns JSONB, -- Array of column definitions with types
    filters JSONB, -- Default filters to apply

    -- Configuration
    config JSONB, -- Additional settings (cache, refresh, etc.)

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_datasets_connection ON datasets(connection_id);
CREATE INDEX IF NOT EXISTS idx_datasets_table ON datasets(table_name);
CREATE INDEX IF NOT EXISTS idx_datasets_source_type ON datasets(source_type);

-- Update trigger for datasets
DROP TRIGGER IF EXISTS update_datasets_updated_at ON datasets;
CREATE TRIGGER update_datasets_updated_at BEFORE UPDATE ON datasets
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment to table
COMMENT ON TABLE datasets IS 'Reusable data sources for charts and queries';
COMMENT ON COLUMN datasets.source_type IS 'Type of data source: table (reference to a table/model) or sql (custom SQL query)';
COMMENT ON COLUMN datasets.columns IS 'Array of available columns with metadata (name, type, description)';
COMMENT ON COLUMN datasets.filters IS 'Default filters that can be applied to the dataset';
