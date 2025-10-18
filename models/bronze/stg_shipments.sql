{{ config(materialized='view') }}

-- Staging: Shipments
-- Shipping and delivery tracking

SELECT
    id as shipment_id,
    order_id,
    carrier_id,
    warehouse_id,
    tracking_number,
    ship_date,
    estimated_delivery,
    actual_delivery,
    status as shipment_status,
    CASE
        WHEN actual_delivery <= estimated_delivery THEN 'On Time'
        WHEN actual_delivery > estimated_delivery THEN 'Delayed'
        ELSE 'In Transit'
    END as delivery_performance
FROM {{ source('raw', 'shipments') }}
