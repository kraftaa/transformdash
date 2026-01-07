{{ config(materialized='incremental') }}

-- Silver: Product return analysis
-- Analyzes return patterns with order and product details for quality insights
-- Includes return reasons, refund amounts, product categories, and return rates

SELECT
    r.return_id,
    r.order_id,
    o.customer_id,
    c.customer_name,
    r.return_date,
    r.return_reason,
    r.return_status,
    o.order_date,
    EXTRACT(DAY FROM (r.return_date - o.order_date)) as days_to_return
FROM {{ ref('stg_returns') }} r
INNER JOIN {{ ref('stg_orders') }} o ON r.order_id = o.order_id
INNER JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id

{% if is_incremental() %}
WHERE r.return_date > (SELECT MAX(return_date) FROM {{ this }})
{% endif %}
