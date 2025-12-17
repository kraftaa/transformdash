{{ config(materialized='view') }}

-- Bronze layer: Stage orders with minimal transformation

SELECT
    order_id,
    customer_id,
    order_date,
    total_amount,
    status as order_status
FROM {{ source('raw', 'raw_orders') }}
