# Simple Transformation Example

A basic example showing how to create a three-layer transformation pipeline in TransformDash.

## What This Example Does

Transforms raw e-commerce data through three layers:
- **Bronze**: Stage raw customer and order data
- **Silver**: Join customers with orders
- **Gold**: Create analytics-ready fact table with metrics

## Setup

1. **Load sample data**:
```bash
psql -h localhost -U postgres -d production -f sample_data.sql
```

2. **Copy models to your project**:
```bash
cp -r models/* /path/to/your/transformdash/models/
```

3. **Run transformations**:
- Visit http://localhost:8000
- Click "▶️ Run Models"
- View results in the Models or Lineage tabs

## File Structure

```
simple_transformation/
├── README.md                    # This file
├── sample_data.sql              # Sample data setup
└── models/
    ├── sources.yml              # Define raw data sources
    ├── bronze/
    │   ├── stg_customers.sql    # Stage customers
    │   └── stg_orders.sql       # Stage orders
    ├── silver/
    │   └── int_customer_orders.sql  # Join customers + orders
    └── gold/
        └── fct_orders.sql       # Analytics fact table
```

## Expected Output

After running, you'll have:
- `stg_customers` (view) - 100 customers
- `stg_orders` (view) - 500 orders
- `int_customer_orders` (table) - 500 joined records
- `fct_orders` (table) - 500 records with order metrics
