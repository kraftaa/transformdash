{{ config(materialized='view') }}

-- Staging: Marketing Campaigns
-- Marketing campaign tracking

SELECT
    id as campaign_id,
    name as campaign_name,
    channel as marketing_channel,
    start_date as campaign_start,
    end_date as campaign_end,
    budget as campaign_budget,
    status as campaign_status,
    EXTRACT(DAY FROM (end_date::timestamp - start_date::timestamp)) as campaign_duration_days
FROM {{ source('raw', 'campaigns') }}
