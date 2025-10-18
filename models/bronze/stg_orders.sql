{{ config(materialized='view') }}

-- Bronze layer: Orders staging table
-- Pattern: Simple column aliasing from raw source

with transformed_data as (
    select
        id as order_id,
        customer_id,
        order_date,
        total_amount,
        status
    from {{ source('raw', 'orders') }}
)

select * from transformed_data
