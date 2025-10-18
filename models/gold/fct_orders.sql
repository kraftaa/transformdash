{{ config(materialized='table') }}

-- Gold layer: Final fact table for order analytics
-- Pattern: Business-ready fact table with all dimensions

with transformed_data as (
    select
        order_id,
        customer_id,
        customer_name,
        customer_email,
        order_date,
        total_amount,
        status,
        -- Derived metrics
        extract(year from order_date) as order_year,
        extract(month from order_date) as order_month,
        extract(day from order_date) as order_day,
        case
            when total_amount >= 1000 then 'High Value'
            when total_amount >= 100 then 'Medium Value'
            else 'Low Value'
        end as order_value_tier
    from {{ ref('int_customer_orders') }}
)

select * from transformed_data
