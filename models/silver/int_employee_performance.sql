{{ config(materialized='incremental') }}

-- Silver: Employee Performance
-- Combine employee data with department metrics

SELECT
    e.employee_id,
    e.employee_name,
    e.employee_email,
    e.department,
    e.position,
    e.hire_date,
    e.salary,
    e.years_of_service,
    CASE
        WHEN e.years_of_service >= 5 THEN 'Senior'
        WHEN e.years_of_service >= 2 THEN 'Mid-Level'
        ELSE 'Junior'
    END as seniority_level,
    CASE
        WHEN e.salary >= 100000 THEN 'High'
        WHEN e.salary >= 60000 THEN 'Medium'
        ELSE 'Entry'
    END as salary_band
FROM {{ ref('stg_employees') }} e

{% if is_incremental() %}
WHERE e.hire_date > (SELECT MAX(hire_date) FROM {{ this }})
{% endif %}
