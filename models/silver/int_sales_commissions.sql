{{ config(materialized='incremental') }}

-- Silver: Sales commission tracking
-- Calculates earned commissions by linking employee performance to order revenue
-- Includes commission rates, earned amounts, order values, and employee information

SELECT
    c.commission_id,
    c.order_id,
    o.customer_id,
    o.order_date,
    o.total_amount as order_amount,
    c.sales_rep_id,
    e.employee_name as sales_rep_name,
    e.department,
    c.commission_rate,
    c.commission_amount,
    c.paid_date,
    c.commission_status,
    EXTRACT(DAY FROM (c.paid_date - o.order_date)) as days_to_pay_commission
FROM {{ ref('stg_commissions') }} c
INNER JOIN {{ ref('stg_orders') }} o ON c.order_id = o.order_id
INNER JOIN {{ ref('stg_employees') }} e ON c.sales_rep_id = e.employee_id

{% if is_incremental() %}
WHERE c.paid_date > (SELECT MAX(paid_date) FROM {{ this }})
{% endif %}
