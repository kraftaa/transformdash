# Asset Referencing in TransformDash Models

Assets are files (CSV, Excel, SQL, Python, etc.) that you upload through the TransformDash UI and can reference in your dbt models using the `{{ asset('filename') }}` function.

## How to Use Assets

### Step 1: Upload an Asset

1. Go to the **Assets** tab in TransformDash
2. Click **"Upload Asset"**
3. Fill in the form:
   - **Name**: `region_lookup.csv` (this is what you'll reference in models)
   - **Description**: Optional description
   - **Type**: Select the file type (CSV, Excel, SQL, etc.)
   - **Tags**: Optional tags for organization
   - **File**: Choose your file
4. Click **Upload**

### Step 2: Reference the Asset in Your Model

Use the `{{ asset('asset_name') }}` function in your SQL:

```sql
{{ config(materialized='table') }}

SELECT
    o.order_id,
    o.customer_id,
    l.region_name,
    l.tax_rate
FROM orders o
LEFT JOIN {{ asset('region_lookup.csv') }} l
    ON o.region_code = l.region_code
```

## Supported Asset Types

### 1. CSV/Excel Files (as Lookup Tables)

**Use Case:** Reference data, dimension tables, mapping tables

**Example:**
```sql
-- Upload: country_codes.csv with columns: code, name, continent
{{ config(materialized='table') }}

SELECT
    u.user_id,
    u.country_code,
    c.name as country_name,
    c.continent
FROM users u
JOIN {{ asset('country_codes.csv') }} c
    ON u.country_code = c.code
```

**How it works:**
- TransformDash loads the CSV/Excel into a temporary table
- Returns the table name that you can JOIN with
- Automatic data type inference

### 2. SQL Files (as Reusable CTEs or Macros)

**Use Case:** Common SQL logic, date spines, utility functions

**Example:**
```sql
-- Upload: date_spine.sql containing a date generation query
{{ config(materialized='table') }}

WITH dates AS (
    {{ asset('date_spine.sql') }}
),
orders_by_date AS (
    SELECT
        DATE(order_date) as order_date,
        COUNT(*) as order_count
    FROM orders
    GROUP BY 1
)
SELECT
    d.date,
    COALESCE(o.order_count, 0) as orders
FROM dates d
LEFT JOIN orders_by_date o ON d.date = o.order_date
```

**How it works:**
- Returns the SQL content as a string
- Injects directly into your query
- Perfect for CTEs and subqueries

### 3. Python Files (for Custom Logic)

**Use Case:** Custom transformations, data quality checks, complex calculations

**Example:**
```python
# Upload: data_validators.py
def validate_email(email):
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def calculate_customer_score(recency, frequency, monetary):
    # Custom scoring logic
    return (recency * 0.3 + frequency * 0.3 + monetary * 0.4)
```

Then in your model:
```sql
-- Note: Python integration requires additional setup
{{ config(materialized='table') }}

-- For now, reference the path for documentation
-- Full Python integration coming soon
SELECT
    customer_id,
    email,
    recency_days,
    order_frequency,
    total_spent
FROM customers
-- Custom scoring logic from {{ asset('data_validators.py') }}
```

### 4. JSON/YAML Files (for Configuration)

**Use Case:** Model configurations, parameter sets, feature flags

**Example:**
```yaml
# Upload: model_config.yaml
customer_segments:
  high_value: 1000
  medium_value: 500
  low_value: 100
retention_days: 90
```

Use in model:
```sql
{{ config(materialized='table') }}

-- Load config (returns file path)
-- Use with custom Jinja2 macro to parse YAML
SELECT
    customer_id,
    total_spent,
    CASE
        WHEN total_spent >= 1000 THEN 'high_value'
        WHEN total_spent >= 500 THEN 'medium_value'
        ELSE 'low_value'
    END as segment
FROM customers
```

## Complete Example

### Example 1: Sales with Regional Tax Calculation

**1. Upload CSV Asset:**

File: `tax_rates.csv`
```csv
region_code,region_name,tax_rate,currency
US-CA,California,0.0725,USD
US-NY,New York,0.0400,USD
UK-LON,London,0.2000,GBP
```

**2. Create Model:**

File: `models/gold/fct_sales_with_tax.sql`
```sql
{{ config(
    materialized='table',
    indexes=[
        {"columns": ["order_id"]},
        {"columns": ["region_code"]}
    ]
) }}

-- Calculate sales with region-specific tax rates
SELECT
    s.order_id,
    s.order_date,
    s.customer_id,
    s.region_code,
    t.region_name,
    t.currency,
    s.amount,
    t.tax_rate,
    ROUND(s.amount * t.tax_rate, 2) as tax_amount,
    ROUND(s.amount * (1 + t.tax_rate), 2) as total_amount
FROM {{ ref('stg_sales') }} s
LEFT JOIN {{ asset('tax_rates.csv') }} t
    ON s.region_code = t.region_code
```

**3. Run the Model:**
- Go to **Models** tab
- Find `fct_sales_with_tax`
- Click **Run**
- TransformDash will automatically load the CSV asset and create the table

### Example 2: Common Date Logic

**1. Upload SQL Asset:**

File: `date_spine_macro.sql`
```sql
-- Generate a sequence of dates
SELECT
    generate_series(
        DATE '2024-01-01',
        DATE '2024-12-31',
        INTERVAL '1 day'
    )::DATE as date
```

**2. Use in Multiple Models:**

```sql
{{ config(materialized='table') }}

WITH all_dates AS (
    {{ asset('date_spine_macro.sql') }}
),
daily_metrics AS (
    SELECT
        DATE(created_at) as date,
        COUNT(*) as event_count
    FROM events
    GROUP BY 1
)
SELECT
    d.date,
    COALESCE(m.event_count, 0) as events
FROM all_dates d
LEFT JOIN daily_metrics m ON d.date = m.date
```

## Best Practices

1. **Naming Convention:**
   - Use descriptive names: `region_tax_rates.csv` not `data.csv`
   - Include version if needed: `product_categories_v2.csv`

2. **Asset Organization:**
   - Use tags to group related assets: `lookup`, `config`, `reference`
   - Add descriptions to explain what the asset contains

3. **CSV Structure:**
   - First row must be column headers
   - Use consistent data types in columns
   - Avoid special characters in column names

4. **Performance:**
   - CSV assets are loaded into temporary tables (fast for small-medium files)
   - For large datasets (>100MB), consider using regular models instead
   - Asset tables are cached during model execution

5. **Version Control:**
   - When updating an asset, consider creating a new version
   - Document changes in the description field
   - Test models after asset updates

## Limitations

- **File Size:** Best for files under 100MB
- **Asset Lifespan:** Asset tables exist only during model execution
- **Python Assets:** Path reference only (full Python integration planned)
- **Not for Source Data:** Use dbt sources for primary data ingestion

## Troubleshooting

**Error: "Asset 'filename' not found"**
- Check the exact filename (case-sensitive)
- Verify the asset is uploaded and active in Assets tab

**Error: "Asset file not found"**
- Asset was deleted from filesystem
- Re-upload the asset

**CSV columns not matching**
- Ensure your JOIN columns exist in the CSV
- Check for leading/trailing spaces in column names

## Next Steps

1. Upload your first asset in the **Assets** tab
2. Create a test model using the example above
3. Run the model and verify it works
4. Explore more complex use cases with SQL assets

---

**Need Help?** Check the examples in `models/examples/` or create an issue on GitHub.
