{{ config(materialized='incremental') }}

-- Silver: Supplier Purchase Orders
-- Enrich purchase orders with supplier details

SELECT
    po.purchase_order_id,
    po.supplier_id,
    s.supplier_name,
    s.supplier_country,
    s.supplier_rating,
    po.po_date,
    po.expected_delivery,
    po.po_status,
    po.po_total,
    EXTRACT(DAY FROM (po.expected_delivery - po.po_date)) as lead_time_days
FROM {{ ref('stg_purchase_orders') }} po
INNER JOIN {{ ref('stg_suppliers') }} s ON po.supplier_id = s.supplier_id

{% if is_incremental() %}
WHERE po.po_date > (SELECT MAX(po_date) FROM {{ this }})
{% endif %}
