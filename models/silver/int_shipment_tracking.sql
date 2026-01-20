{{ config(materialized='incremental') }}

-- Silver: Shipment tracking and logistics
-- Monitors shipment status with carrier information and delivery timelines
-- Includes tracking numbers, estimated delivery dates, carrier details, and shipment costs

SELECT
    sh.shipment_id,
    sh.order_id,
    o.customer_id,
    sh.carrier_id,
    c.carrier_name,
    c.carrier_rating,
    sh.warehouse_id,
    w.warehouse_name,
    sh.tracking_number,
    sh.ship_date,
    sh.estimated_delivery,
    sh.actual_delivery,
    sh.shipment_status,
    sh.delivery_performance,
    CASE
        WHEN sh.actual_delivery IS NOT NULL
        THEN EXTRACT(DAY FROM (sh.actual_delivery - sh.ship_date))
        ELSE NULL
    END as actual_delivery_days
FROM {{ ref('stg_shipments') }} sh
INNER JOIN {{ ref('stg_orders') }} o ON sh.order_id = o.order_id
INNER JOIN {{ ref('stg_carriers') }} c ON sh.carrier_id = c.carrier_id
INNER JOIN {{ ref('stg_warehouses') }} w ON sh.warehouse_id = w.warehouse_id

{% if is_incremental() %}
WHERE sh.ship_date > (SELECT MAX(ship_date) FROM {{ this }})
{% endif %}
