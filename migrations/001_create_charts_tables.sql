-- Migration: Create charts and dashboard_charts tables
-- Description: Move chart storage from YAML to database tables for proper global chart management
-- Date: 2025-11-06

-- Create charts table for global chart definitions
CREATE TABLE IF NOT EXISTS charts (
    id VARCHAR(255) PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'bar', 'line', 'pie', 'table', 'metric', etc.
    model VARCHAR(255) NOT NULL, -- The data model/table to query
    x_axis VARCHAR(255), -- X-axis field
    y_axis VARCHAR(255), -- Y-axis field
    aggregation VARCHAR(50) DEFAULT 'sum', -- Aggregation function
    columns JSONB, -- For table charts, array of column names
    category VARCHAR(255), -- For stacked charts
    config JSONB, -- Additional configuration options
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create junction table for dashboard-chart relationships (many-to-many)
CREATE TABLE IF NOT EXISTS dashboard_charts (
    id SERIAL PRIMARY KEY,
    dashboard_id VARCHAR(255) NOT NULL, -- References dashboard ID from dashboards.yml
    chart_id VARCHAR(255) NOT NULL REFERENCES charts(id) ON DELETE CASCADE,
    tab_id VARCHAR(255), -- NULL means unassigned to any tab
    position INTEGER DEFAULT 0, -- Order within the tab
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(dashboard_id, chart_id, tab_id) -- A chart can only appear once per tab
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_dashboard_charts_dashboard ON dashboard_charts(dashboard_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_charts_chart ON dashboard_charts(chart_id);
CREATE INDEX IF NOT EXISTS idx_dashboard_charts_tab ON dashboard_charts(tab_id);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger to auto-update updated_at
CREATE TRIGGER update_charts_updated_at BEFORE UPDATE ON charts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Add comment to tables
COMMENT ON TABLE charts IS 'Global chart definitions independent of dashboards';
COMMENT ON TABLE dashboard_charts IS 'Junction table mapping charts to dashboards and tabs';
COMMENT ON COLUMN dashboard_charts.tab_id IS 'NULL indicates chart is unassigned (in dashboard but not in any tab)';
