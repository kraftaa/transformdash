{{ config(materialized='view') }}

-- Staging: Products
-- Clean and standardize product catalog data

SELECT
    id as product_id,
    name as product_name,
    category,
    price,
    cost,
    sku,
    weight_kg,
    (price - cost) as profit_margin,
    ROUND((price - cost) / NULLIF(price, 0) * 100, 2) as margin_percentage
FROM {{ source('raw', 'products') }}
WHERE price > 0
