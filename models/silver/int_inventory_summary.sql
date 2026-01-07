{{ config(materialized='incremental') }}

-- Silver: Inventory levels by location
-- Current stock quantities with product details and warehouse information
-- Includes on-hand inventory, unit prices, and product categories across all warehouses

SELECT
    sl.stock_id,
    sl.product_id,
    p.product_name,
    p.category,
    sl.warehouse_id,
    w.warehouse_name,
    w.location as warehouse_location,
    sl.stock_quantity,
    p.price as unit_price,
    sl.stock_quantity * p.price as inventory_value,
    sl.last_updated
FROM {{ ref('stg_stock_levels') }} sl
INNER JOIN {{ ref('stg_products') }} p ON sl.product_id = p.product_id
INNER JOIN {{ ref('stg_warehouses') }} w ON sl.warehouse_id = w.warehouse_id

{% if is_incremental() %}
WHERE sl.last_updated > (SELECT MAX(last_updated) FROM {{ this }})
{% endif %}
