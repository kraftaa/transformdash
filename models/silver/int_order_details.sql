{{ config(materialized='incremental') }}

-- Silver: Order line item details
-- Complete order breakdown with product information and pricing at line-item level
-- Includes quantities, unit prices, discounts, and product categories for each order item

SELECT
    oi.order_item_id,
    o.order_id,
    o.customer_id,
    o.order_date,
    o.status as order_status,
    oi.product_id,
    p.product_name,
    p.category as product_category,
    oi.quantity,
    oi.unit_price,
    oi.line_total,
    p.cost as unit_cost,
    (oi.unit_price - p.cost) * oi.quantity as line_profit
FROM {{ ref('stg_order_items') }} oi
INNER JOIN {{ ref('stg_orders') }} o ON oi.order_id = o.order_id
INNER JOIN {{ ref('stg_products') }} p ON oi.product_id = p.product_id

{% if is_incremental() %}
WHERE o.order_date > (SELECT MAX(order_date) FROM {{ this }})
{% endif %}
