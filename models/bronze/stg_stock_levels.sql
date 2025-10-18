{{ config(materialized='view') }}

-- Staging: Stock Levels
-- Current inventory levels by product and warehouse

SELECT
    id as stock_id,
    product_id,
    warehouse_id,
    quantity as stock_quantity,
    last_updated
FROM {{ source('raw', 'stock_levels') }}
