# Simple Transformation Example

A basic example showing TransformDash's three-layer transformation pipeline with real e-commerce data.

## What This Example Does

Transforms raw e-commerce data through three layers:
- **Bronze**: Stage raw customer and order data
- **Silver**: Join customers with orders
- **Gold**: Create analytics-ready fact table with metrics

## Quick Start

1. **Load sample data**:
```bash
python seed_fake_data_expanded.py
```

2. **Run transformations**:
```bash
python run_transformations.py
```

Or via UI:
- Visit http://localhost:8000
- Click "▶️ Run Models"
- View results in the Models or Lineage tabs

## Example Models

The transformation pipeline uses these models from the main project:

**Bronze Layer** (in `models/bronze/`):
- `stg_customers.sql` - Stage customers with minimal transformation
- `stg_orders.sql` - Stage orders with minimal transformation

**Silver Layer** (in `models/silver/`):
- `int_customer_orders.sql` - Join customers with orders

**Gold Layer** (in `models/gold/`):
- `fct_orders.sql` - Analytics-ready fact table with metrics

## Expected Output

After running transformations with the seeded data:
- `stg_customers` (view) - 100 customers
- `stg_orders` (view) - 500 orders
- `int_customer_orders` (table) - 500 joined records
- `fct_orders` (table) - Analytics fact table with order metrics, year/month breakdowns
