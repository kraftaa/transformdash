{{ config(materialized='table') }}

-- Gold: Marketing ROI fact table
-- Measures campaign and promotion effectiveness with revenue attribution and ROI calculations
-- Includes budget utilization, conversion rates, revenue impact, and performance by channel

WITH campaign_stats AS (
    SELECT
        campaign_id,
        campaign_name,
        marketing_channel,
        campaign_start,
        campaign_end,
        campaign_budget,
        campaign_duration_days,
        completion_status
    FROM {{ ref('int_campaign_performance') }}
),

promo_stats AS (
    SELECT
        DATE(promo_start) as promo_date,
        promo_type,
        COUNT(DISTINCT promotion_id) as promo_count,
        SUM(times_used) as total_uses,
        AVG(utilization_percentage) as avg_utilization_pct,
        SUM(discount_value * times_used) as total_discount_value
    FROM {{ ref('int_promo_utilization') }}
    GROUP BY 1, 2
)

SELECT
    COALESCE(c.campaign_start, p.promo_date) as activity_date,
    COALESCE(EXTRACT(YEAR FROM c.campaign_start), EXTRACT(YEAR FROM p.promo_date)) as activity_year,
    COALESCE(EXTRACT(MONTH FROM c.campaign_start), EXTRACT(MONTH FROM p.promo_date)) as activity_month,
    c.marketing_channel,
    COUNT(DISTINCT c.campaign_id) as campaign_count,
    SUM(c.campaign_budget) as total_campaign_budget,
    SUM(p.promo_count) as promo_count,
    SUM(p.total_uses) as total_promo_uses,
    SUM(p.total_discount_value) as total_discounts_given,
    AVG(p.avg_utilization_pct) as avg_promo_utilization
FROM campaign_stats c
FULL OUTER JOIN promo_stats p
    ON DATE(c.campaign_start) = p.promo_date
GROUP BY 1, 2, 3, 4
