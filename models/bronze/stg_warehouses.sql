{{ config(materialized='view') }}

-- Staging: Warehouses
-- Warehouse location and capacity data

SELECT
    id as warehouse_id,
    name as warehouse_name,
    location,
    capacity,
    manager as warehouse_manager
FROM {{ source('raw', 'warehouses') }}
