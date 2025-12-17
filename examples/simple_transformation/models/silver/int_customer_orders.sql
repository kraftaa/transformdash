{{ config(materialized='table') }}

-- Silver layer: Join customers with orders

SELECT
    o.order_id,
    o.customer_id,
    c.customer_name,
    c.email as customer_email,
    o.order_date,
    o.total_amount,
    o.order_status
FROM {{ ref('stg_orders') }} o
JOIN {{ ref('stg_customers') }} c
    ON o.customer_id = c.customer_id
