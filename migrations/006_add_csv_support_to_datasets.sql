-- Migration: Add CSV file support to datasets table

-- Add column to store CSV file path
ALTER TABLE datasets
ADD COLUMN IF NOT EXISTS file_path TEXT;

-- Add column to store original filename
ALTER TABLE datasets
ADD COLUMN IF NOT EXISTS original_filename VARCHAR(500);

-- Add column to store file size
ALTER TABLE datasets
ADD COLUMN IF NOT EXISTS file_size_bytes BIGINT;

COMMENT ON COLUMN datasets.file_path IS 'Path to uploaded CSV file on server';
COMMENT ON COLUMN datasets.original_filename IS 'Original name of the uploaded file';
COMMENT ON COLUMN datasets.file_size_bytes IS 'Size of the uploaded file in bytes';
