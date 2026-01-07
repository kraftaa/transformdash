{{ config(materialized='incremental') }}

-- Silver: Promotion usage and effectiveness
-- Tracks promo code utilization against capacity with discount performance
-- Includes redemption rates, remaining capacity, and discount amounts by promotion

SELECT
    p.promotion_id,
    p.promo_code,
    p.promo_type,
    p.discount_value,
    p.promo_start,
    p.promo_end,
    p.usage_limit,
    p.times_used,
    p.utilization_percentage,
    p.usage_limit - p.times_used as remaining_uses,
    CASE
        WHEN p.times_used >= p.usage_limit THEN 'Exhausted'
        WHEN p.utilization_percentage >= 80 THEN 'High'
        WHEN p.utilization_percentage >= 50 THEN 'Medium'
        ELSE 'Low'
    END as utilization_status,
    EXTRACT(DAY FROM (p.promo_end::timestamp - p.promo_start::timestamp)) as promo_duration_days
FROM {{ ref('stg_promotions') }} p

{% if is_incremental() %}
WHERE p.promo_start > (SELECT MAX(promo_start) FROM {{ this }})
{% endif %}
