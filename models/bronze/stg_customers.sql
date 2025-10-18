{{ config(materialized='view') }}

-- Bronze layer: Direct extraction from raw source with minimal transformation
-- Pattern: Column aliasing and standardization

with transformed_data as (
    select
        id as customer_id,
        email,
        name as customer_name,
        created_at
    from {{ source('raw', 'customers') }}
)

select * from transformed_data
