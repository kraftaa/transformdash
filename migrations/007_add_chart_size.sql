-- Migration: Add size column to dashboard_charts for chart resizing
-- Created: 2025-01-12

-- Add size column to dashboard_charts
-- Size options: 'small' (1/4 width), 'medium' (1/2 width), 'large' (3/4 width), 'full' (full width)
ALTER TABLE dashboard_charts
ADD COLUMN IF NOT EXISTS size VARCHAR(20) DEFAULT 'medium';

-- Add comment
COMMENT ON COLUMN dashboard_charts.size IS 'Chart display size: small, medium, large, or full';
