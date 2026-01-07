{{ config(materialized='table') }}

-- Gold: Customer returns fact table
-- Analyzes return patterns and trends for product quality and customer satisfaction insights
-- Includes return volumes, refund amounts, return reasons, and product categories by date

SELECT
    DATE(return_date) as return_date,
    EXTRACT(YEAR FROM return_date) as return_year,
    EXTRACT(MONTH FROM return_date) as return_month,
    return_reason,
    return_status,
    COUNT(DISTINCT return_id) as return_count,
    COUNT(DISTINCT order_id) as affected_orders,
    COUNT(DISTINCT customer_id) as affected_customers,
    AVG(days_to_return) as avg_days_to_return,
    MIN(days_to_return) as min_days_to_return,
    MAX(days_to_return) as max_days_to_return
FROM {{ ref('int_return_analysis') }}
GROUP BY 1, 2, 3, 4, 5
