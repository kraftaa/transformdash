{{ config(
    materialized='incremental',
    unique_key='order_id'
) }}

-- Silver: Customer order history
-- Combines customer details with order data for purchase analysis
-- Includes order totals, status, and customer contact information with incremental updates

with transformed_data as (
    select
        o.order_id,
        o.customer_id,
        c.customer_name,
        c.email as customer_email,
        o.order_date,
        o.total_amount,
        o.status
    from {{ ref('stg_orders') }} o
    join {{ ref('stg_customers') }} c
        on o.customer_id = c.customer_id

    {% if is_incremental() %}
        -- Only process new/updated orders on incremental runs
        where o.order_date > (select max(order_date) from {{ this }})
    {% endif %}
)

select * from transformed_data
