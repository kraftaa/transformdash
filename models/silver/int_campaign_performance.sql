{{ config(materialized='incremental') }}

-- Silver: Marketing campaign performance
-- Tracks campaign effectiveness with budget utilization and completion status
-- Includes spend analysis, duration metrics, and channel performance by campaign

SELECT
    c.campaign_id,
    c.campaign_name,
    c.marketing_channel,
    c.campaign_start,
    c.campaign_end,
    c.campaign_budget,
    c.campaign_status,
    c.campaign_duration_days,
    CASE
        WHEN c.campaign_duration_days > 0
        THEN ROUND(c.campaign_budget / c.campaign_duration_days, 2)
        ELSE 0
    END as daily_budget,
    CASE
        WHEN c.campaign_status = 'completed' THEN 'Yes'
        WHEN CURRENT_DATE > c.campaign_end THEN 'Overdue'
        ELSE 'Active'
    END as completion_status
FROM {{ ref('stg_campaigns') }} c

{% if is_incremental() %}
WHERE c.campaign_start > (SELECT MAX(campaign_start) FROM {{ this }})
{% endif %}
