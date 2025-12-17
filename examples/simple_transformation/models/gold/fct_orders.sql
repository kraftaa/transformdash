{{ config(materialized='table') }}

-- Gold layer: Analytics-ready fact table with metrics

SELECT
    order_id,
    customer_id,
    customer_name,
    customer_email,
    order_date,
    total_amount,
    order_status,
    EXTRACT(YEAR FROM order_date) as order_year,
    EXTRACT(MONTH FROM order_date) as order_month,
    EXTRACT(DAY FROM order_date) as order_day,
    CASE
        WHEN total_amount < 100 THEN 'Small'
        WHEN total_amount < 300 THEN 'Medium'
        ELSE 'Large'
    END as order_size_category
FROM {{ ref('int_customer_orders') }}
