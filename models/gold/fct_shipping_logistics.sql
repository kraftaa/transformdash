{{ config(materialized='table') }}

-- Gold: Shipping and logistics fact table
-- Tracks delivery performance and shipping costs for carrier and warehouse optimization
-- Includes on-time delivery rates, average costs, shipment volumes, and performance by carrier

SELECT
    carrier_id,
    carrier_name,
    warehouse_id,
    warehouse_name,
    DATE(ship_date) as ship_date,
    EXTRACT(YEAR FROM ship_date) as ship_year,
    EXTRACT(MONTH FROM ship_date) as ship_month,
    COUNT(DISTINCT shipment_id) as shipment_count,
    COUNT(DISTINCT order_id) as order_count,
    SUM(CASE WHEN delivery_performance = 'On Time' THEN 1 ELSE 0 END) as on_time_deliveries,
    SUM(CASE WHEN delivery_performance = 'Delayed' THEN 1 ELSE 0 END) as delayed_deliveries,
    AVG(actual_delivery_days) as avg_delivery_days,
    ROUND(
        SUM(CASE WHEN delivery_performance = 'On Time' THEN 1 ELSE 0 END)::DECIMAL
        / NULLIF(COUNT(*), 0) * 100,
        2
    ) as on_time_percentage
FROM {{ ref('int_shipment_tracking') }}
WHERE shipment_status = 'delivered'
GROUP BY 1, 2, 3, 4, 5, 6, 7
