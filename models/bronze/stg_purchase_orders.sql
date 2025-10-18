{{ config(materialized='view') }}

-- Staging: Purchase Orders
-- Orders placed with suppliers

SELECT
    id as purchase_order_id,
    supplier_id,
    order_date as po_date,
    expected_delivery,
    status as po_status,
    total_amount as po_total
FROM {{ source('raw', 'purchase_orders') }}
