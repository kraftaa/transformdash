{{ config(materialized='view') }}

-- Staging: Promotions
-- Discount codes and promotional offers

SELECT
    id as promotion_id,
    code as promo_code,
    type as promo_type,
    discount_value,
    start_date as promo_start,
    end_date as promo_end,
    usage_limit,
    times_used,
    ROUND((times_used::DECIMAL / NULLIF(usage_limit, 0) * 100), 2) as utilization_percentage
FROM {{ source('raw', 'promotions') }}
