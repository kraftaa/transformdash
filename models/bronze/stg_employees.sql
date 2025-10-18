{{ config(materialized='view') }}

-- Staging: Employees
-- Employee information and organization

SELECT
    id as employee_id,
    name as employee_name,
    email as employee_email,
    department,
    position,
    hire_date,
    salary,
    EXTRACT(YEAR FROM AGE(CURRENT_DATE, hire_date)) as years_of_service
FROM {{ source('raw', 'employees') }}
