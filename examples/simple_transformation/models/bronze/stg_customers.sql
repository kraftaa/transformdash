{{ config(materialized='view') }}

-- Bronze layer: Stage customers with minimal transformation

SELECT
    id as customer_id,
    email,
    name as customer_name,
    created_at
FROM {{ source('raw', 'raw_customers') }}
