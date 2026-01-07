{{ config(
    materialized='table',
    indexes=[
        {"columns": ["warehouse_id"]},
    ])
}}

-- Gold: Inventory metrics fact table
-- Aggregates warehouse inventory levels and valuation for stock management decisions
-- Includes total units, inventory value, turnover rates, and stock levels by warehouse and category

SELECT
    warehouse_id,
    warehouse_name,
    warehouse_location,
    category as product_category,
    COUNT(DISTINCT product_id) as product_count,
    SUM(stock_quantity) as total_units,
    SUM(inventory_value) as total_inventory_value,
    AVG(unit_price) as avg_unit_price,
    MIN(stock_quantity) as min_stock,
    MAX(stock_quantity) as max_stock,
    AVG(stock_quantity) as avg_stock,
    SUM(CASE WHEN stock_quantity = 0 THEN 1 ELSE 0 END) as out_of_stock_count,
    SUM(CASE WHEN stock_quantity < 10 THEN 1 ELSE 0 END) as low_stock_count
FROM {{ ref('int_inventory_summary') }}
GROUP BY 1, 2, 3, 4
