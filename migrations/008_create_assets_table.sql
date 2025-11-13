-- Migration: Create assets management tables
-- Created: 2025-01-12

-- Assets table to store metadata about uploaded files and resources
CREATE TABLE IF NOT EXISTS assets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    asset_type VARCHAR(50) NOT NULL, -- 'csv', 'excel', 'sql', 'python', 'json', 'yaml', 'markdown', 'image', 'pdf', 'other'
    file_path VARCHAR(500) NOT NULL, -- Relative path to the file
    file_size INTEGER, -- Size in bytes
    mime_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    tags TEXT[], -- Array of tags for categorization
    metadata JSONB, -- Additional metadata as JSON
    is_active BOOLEAN DEFAULT TRUE,
    UNIQUE(name)
);

-- Create index on asset_type for faster filtering
CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);

-- Create index on tags for searching
CREATE INDEX IF NOT EXISTS idx_assets_tags ON assets USING GIN(tags);

-- Create index on created_at for sorting
CREATE INDEX IF NOT EXISTS idx_assets_created ON assets(created_at DESC);

-- Add comments
COMMENT ON TABLE assets IS 'Stores metadata for uploaded assets (files, scripts, configs, etc.)';
COMMENT ON COLUMN assets.asset_type IS 'Type of asset: csv, excel, sql, python, json, yaml, markdown, image, pdf, other';
COMMENT ON COLUMN assets.file_path IS 'Relative path to the file from the assets root directory';
COMMENT ON COLUMN assets.tags IS 'Array of tags for categorization and search';
COMMENT ON COLUMN assets.metadata IS 'Additional metadata stored as JSON (e.g., column info for CSV, function names for Python)';
