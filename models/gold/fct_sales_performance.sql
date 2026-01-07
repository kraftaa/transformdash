{{ config(materialized='table') }}

-- Gold: Sales performance fact table
-- Daily sales metrics with multi-dimensional analysis for revenue tracking and forecasting
-- Includes revenue, units sold, average order value, and product performance by date and category

WITH daily_sales AS (
    SELECT
        DATE(order_date) as sale_date,
        EXTRACT(YEAR FROM order_date) as sale_year,
        EXTRACT(MONTH FROM order_date) as sale_month,
        EXTRACT(QUARTER FROM order_date) as sale_quarter,
        EXTRACT(DOW FROM order_date) as day_of_week,
        product_category,
        COUNT(DISTINCT order_id) as order_count,
        SUM(line_total) as revenue,
        SUM(line_profit) as profit,
        SUM(quantity) as units_sold,
        AVG(unit_price) as avg_unit_price,
        COUNT(DISTINCT customer_id) as unique_customers
    FROM {{ ref('int_order_details') }}
    WHERE order_status = 'completed'
    GROUP BY 1, 2, 3, 4, 5, 6
)

SELECT
    *,
    ROUND(profit / NULLIF(revenue, 0) * 100, 2) as profit_margin_pct,
    ROUND(revenue / NULLIF(order_count, 0), 2) as avg_order_value,
    ROUND(revenue / NULLIF(unique_customers, 0), 2) as revenue_per_customer
FROM daily_sales
