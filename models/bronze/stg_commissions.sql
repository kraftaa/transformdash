{{ config(materialized='view') }}

-- Staging: Sales Commissions
-- Commission tracking for sales team

SELECT
    id as commission_id,
    order_id,
    sales_rep_id,
    commission_rate,
    commission_amount,
    paid_date,
    status as commission_status
FROM {{ source('raw', 'commissions') }}
