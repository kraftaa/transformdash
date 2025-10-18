{{ config(materialized='view') }}

-- Staging: Returns
-- Customer return requests

SELECT
    id as return_id,
    order_id,
    return_date,
    reason as return_reason,
    status as return_status,
    notes as return_notes
FROM {{ source('raw', 'returns') }}
