{{ config(materialized='view') }}

-- Staging: Order Items
-- Line-level order details

SELECT
    id as order_item_id,
    order_id,
    product_id,
    quantity,
    price as unit_price,
    total as line_total,
    CURRENT_TIMESTAMP as loaded_at
FROM {{ source('raw', 'order_items') }}
WHERE quantity > 0
