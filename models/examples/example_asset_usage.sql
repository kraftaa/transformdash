{{ config(
    materialized='table'
) }}

-- Example: Using a CSV asset as a lookup table
-- This model demonstrates how to reference uploaded assets in your models

-- First, we'll create some sample order data
WITH sample_orders AS (
    SELECT
        1 as order_id,
        'US-CA' as region_code,
        100.00 as amount
    UNION ALL
    SELECT 2, 'US-NY', 200.00
    UNION ALL
    SELECT 3, 'UK-LON', 150.00
    UNION ALL
    SELECT 4, 'CA-ON', 175.00
    UNION ALL
    SELECT 5, 'DE-BE', 225.00
)

-- Now join with the asset lookup table
SELECT
    o.order_id,
    o.region_code,
    l.region_name,
    l.currency,
    o.amount,
    l.tax_rate,
    ROUND(o.amount * l.tax_rate, 2) as tax_amount,
    ROUND(o.amount * (1 + l.tax_rate), 2) as total_with_tax
FROM sample_orders o
LEFT JOIN {{ asset('region_lookup.csv') }} l
    ON o.region_code = l.region_code
