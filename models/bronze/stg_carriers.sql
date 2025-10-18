{{ config(materialized='view') }}

-- Staging: Carriers
-- Shipping carrier information

SELECT
    id as carrier_id,
    name as carrier_name,
    contact_phone as carrier_phone,
    rating as carrier_rating
FROM {{ source('raw', 'carriers') }}
