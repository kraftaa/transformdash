{{ config(materialized='incremental') }}

-- Silver: Payment transaction reconciliation
-- Matches successful payments with order details for financial reporting
-- Includes transaction IDs, payment amounts, methods, and order totals for audit trails

SELECT
    pt.transaction_id,
    pt.order_id,
    o.customer_id,
    c.customer_name,
    pt.transaction_date,
    pt.transaction_amount,
    o.total_amount as order_amount,
    pt.transaction_amount - o.total_amount as amount_difference,
    CASE
        WHEN ABS(pt.transaction_amount - o.total_amount) < 0.01 THEN 'Matched'
        WHEN pt.transaction_amount < o.total_amount THEN 'Underpaid'
        ELSE 'Overpaid'
    END as reconciliation_status
FROM {{ ref('stg_payment_transactions') }} pt
INNER JOIN {{ ref('stg_orders') }} o ON pt.order_id = o.order_id
INNER JOIN {{ ref('stg_customers') }} c ON o.customer_id = c.customer_id

{% if is_incremental() %}
WHERE pt.transaction_date > (SELECT MAX(transaction_date) FROM {{ this }})
{% endif %}
