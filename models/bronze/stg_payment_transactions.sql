{{ config(materialized='view') }}

-- Staging: Payment Transactions
-- Payment processing records

SELECT
    id as transaction_id,
    order_id,
    payment_method_id,
    transaction_date,
    amount as transaction_amount,
    status as payment_status,
    transaction_id as external_transaction_id
FROM {{ source('raw', 'payment_transactions') }}
WHERE status = 'success'
