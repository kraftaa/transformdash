# Writing Model Descriptions for AI Search

Good descriptions make AI search more effective. The AI combines your model name, description, and layer to understand what each model does.

## Quick Reference

```sql
-- [Layer]: [Model Type]
-- [What it does - business purpose]
-- [Key metrics/details - optional]

{{ config(materialized='table') }}

SELECT ...
```

## Examples

### ✅ Good Descriptions

**Staging Model:**
```sql
-- Bronze: Customer staging table
-- Standardizes raw customer data from CRM system
-- Includes contact info, account status, and customer segments

{{ config(materialized='view') }}

SELECT
    id as customer_id,
    email,
    name as customer_name,
    created_at
FROM {{ source('raw', 'customers') }}
```

**Fact Table:**
```sql
-- Gold: Daily sales fact table
-- Revenue and unit sales aggregated by product, store, and date
-- Includes profit margins, discounts, and tax calculations

{{ config(materialized='table') }}

WITH ...
```

**Intermediate Model:**
```sql
-- Silver: Customer order aggregations
-- Combines customer and order data with lifetime value calculations
-- Enriched with order counts, average order value, and recency metrics

{{ config(materialized='table') }}

SELECT ...
```

### ❌ Weak Descriptions

**Too Generic:**
```sql
-- Customers table
SELECT * FROM {{ source('raw', 'customers') }}
```

**Missing Context:**
```sql
-- stg_orders
{{ config(materialized='view') }}
SELECT * FROM {{ source('raw', 'orders') }}
```

**Just Repeating the Name:**
```sql
-- Marketing ROI
-- Marketing ROI data
SELECT ...
```

## Description Formula

### Line 1: Layer + Model Type
- `Bronze: [Entity] staging table`
- `Silver: [Business concept] aggregations`
- `Gold: [Business metric] fact table`
- `Gold: [Entity] dimension table`

### Line 2: Business Purpose (What it Does)
Focus on the **why** and **what**, not the **how**:
- ✅ "Tracks customer purchase behavior across all channels"
- ❌ "Joins customers with orders table"

### Line 3: Key Details (Optional)
What makes this model unique or important:
- Metrics included: "Includes revenue, margins, returns"
- Data source: "Sourced from Shopify and Stripe"
- Grain: "Daily aggregation at product-store level"
- Special logic: "Excludes test orders and refunds"

## AI Search Examples

With good descriptions, users can search naturally:

**Query**: "customer revenue models"
**Finds**:
- `fct_customer_revenue` (87% match) - "Daily customer revenue with LTV"
- `int_customer_orders` (65% match) - "Customer order aggregations"
- `stg_customers` (45% match) - "Customer master data"

**Query**: "staging tables for orders"
**Finds**:
- `stg_orders` (91% match) - "Order staging from e-commerce platform"
- `stg_order_items` (78% match) - "Line item details for each order"

**Query**: "inventory tracking"
**Finds**:
- `fct_inventory_metrics` (82% match) - "Daily inventory levels and turnover"
- `int_warehouse_stock` (71% match) - "Warehouse inventory by location"

## Common Patterns

### Staging (Bronze Layer)
```sql
-- Bronze: [Source] staging table
-- [What data it contains] from [source system]
```

Example:
```sql
-- Bronze: Order staging table
-- Raw order data from Shopify including line items and customer info
```

### Intermediate (Silver Layer)
```sql
-- Silver: [Business concept]
-- [What transformations applied] with [key calculations]
```

Example:
```sql
-- Silver: Customer lifetime value
-- Combines purchase history and engagement metrics with predictive LTV scoring
```

### Marts (Gold Layer)

**Fact Tables:**
```sql
-- Gold: [Metric] fact table
-- [Business metrics] aggregated by [grain]
```

Example:
```sql
-- Gold: Sales performance fact table
-- Revenue and units sold by product, store, and day with year-over-year comparisons
```

**Dimension Tables:**
```sql
-- Gold: [Entity] dimension
-- [Type of entity] with [enrichment details]
```

Example:
```sql
-- Gold: Product dimension
-- Complete product catalog with categories, attributes, and current pricing
```

## Tips

1. **Be Specific**: "Daily revenue by customer segment" > "Customer revenue"
2. **Include Business Terms**: Use language your team uses ("churn rate" not "customer_left")
3. **Mention Sources**: If sourcing from important systems (Salesforce, Stripe, etc.)
4. **Update When Logic Changes**: Keep descriptions in sync with the actual SQL
5. **Think Search First**: Write descriptions someone would search for

## Testing Your Descriptions

Good test: Can someone find this model by describing what they need?

**User wants**: "models showing which products are selling well"
**Should find**: `fct_product_performance` with description like:
```sql
-- Gold: Product sales performance
-- Top selling products by revenue and units with trend analysis
```

## Quick Audit

Run through your models and check:
- [ ] Does every model have at least 2 comment lines?
- [ ] Does the description explain the business purpose?
- [ ] Would a new team member understand what this model does?
- [ ] Can you search for this model using natural language?

## Adding Descriptions to Existing Models

**Priority Order:**
1. **Gold layer fact tables** - Most searched, highest value
2. **Gold layer dimensions** - Frequently referenced
3. **Silver layer** - Important intermediate logic
4. **Bronze layer** - Can be brief, usually obvious from source

**Time estimate**: ~2-3 minutes per model

**Quick script** to find models missing descriptions:
```bash
for f in models/**/*.sql; do
  if ! grep -q "^--" "$f"; then
    echo "Missing description: $f"
  fi
done
```

## Impact

With good descriptions:
- **More accurate search results** - AI understands context
- **Faster model discovery** - Find what you need in seconds
- **Better documentation** - Comments serve dual purpose
- **Easier onboarding** - New team members find models intuitively

The 2-3 minutes spent writing a good description saves hours of searching later!
