{{ config(materialized='view') }}

-- Staging: Suppliers
-- Supplier and vendor information

SELECT
    id as supplier_id,
    name as supplier_name,
    contact_name,
    email as supplier_email,
    phone as supplier_phone,
    country as supplier_country,
    rating as supplier_rating
FROM {{ source('raw', 'suppliers') }}
