"""
Seed Fake Data - Populate PostgreSQL with realistic sample data
Uses Faker library to generate customers, orders, products
"""
import random
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd
from postgres import PostgresConnector

fake = Faker()
Faker.seed(42)  # For reproducibility
random.seed(42)


def generate_customers(n=100):
    """Generate fake customer data"""
    customers = []
    for i in range(1, n + 1):
        customers.append({
            'id': i,
            'email': fake.email(),
            'name': fake.name(),
            'created_at': fake.date_time_between(start_date='-2y', end_date='now'),
            'country': fake.country_code(),
            'city': fake.city(),
            'phone': fake.phone_number()
        })
    return pd.DataFrame(customers)


def generate_products(n=50):
    """Generate fake product catalog"""
    categories = ['Electronics', 'Clothing', 'Books', 'Home & Garden', 'Sports', 'Toys']
    products = []
    for i in range(1, n + 1):
        products.append({
            'id': i,
            'name': fake.catch_phrase(),
            'category': random.choice(categories),
            'price': round(random.uniform(10.0, 500.0), 2),
            'stock': random.randint(0, 1000)
        })
    return pd.DataFrame(products)


def generate_orders(customers_df, products_df, n=500):
    """Generate fake order data"""
    orders = []
    order_items = []
    order_id = 1

    for _ in range(n):
        customer_id = random.choice(customers_df['id'].tolist())
        order_date = fake.date_time_between(start_date='-1y', end_date='now')
        num_items = random.randint(1, 5)

        order_total = 0
        for item_num in range(num_items):
            product = products_df.sample(1).iloc[0]
            quantity = random.randint(1, 3)
            item_total = product['price'] * quantity
            order_total += item_total

            order_items.append({
                'id': len(order_items) + 1,
                'order_id': order_id,
                'product_id': product['id'],
                'quantity': quantity,
                'price': product['price'],
                'total': item_total
            })

        orders.append({
            'id': order_id,
            'customer_id': customer_id,
            'order_date': order_date,
            'total_amount': round(order_total, 2),
            'status': random.choice(['completed', 'pending', 'cancelled'])
        })
        order_id += 1

    return pd.DataFrame(orders), pd.DataFrame(order_items)


def create_raw_schema(pg):
    """Create raw schema and tables in PostgreSQL"""
    print("📦 Creating raw schema and tables...")

    # Create schema
    pg.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # Drop existing tables
    pg.execute("DROP TABLE IF EXISTS raw.order_items CASCADE")
    pg.execute("DROP TABLE IF EXISTS raw.orders CASCADE")
    pg.execute("DROP TABLE IF EXISTS raw.customers CASCADE")
    pg.execute("DROP TABLE IF EXISTS raw.products CASCADE")

    # Create customers table
    pg.execute("""
        CREATE TABLE raw.customers (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            name VARCHAR(255),
            created_at TIMESTAMP,
            country VARCHAR(10),
            city VARCHAR(255),
            phone VARCHAR(50)
        )
    """)

    # Create products table
    pg.execute("""
        CREATE TABLE raw.products (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            category VARCHAR(100),
            price DECIMAL(10, 2),
            stock INTEGER
        )
    """)

    # Create orders table
    pg.execute("""
        CREATE TABLE raw.orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES raw.customers(id),
            order_date TIMESTAMP,
            total_amount DECIMAL(10, 2),
            status VARCHAR(50)
        )
    """)

    # Create order_items table
    pg.execute("""
        CREATE TABLE raw.order_items (
            id INTEGER PRIMARY KEY,
            order_id INTEGER REFERENCES raw.orders(id),
            product_id INTEGER REFERENCES raw.products(id),
            quantity INTEGER,
            price DECIMAL(10, 2),
            total DECIMAL(10, 2)
        )
    """)

    print("✓ Schema and tables created")


def seed_data():
    """Main function to seed all fake data"""
    print("\n" + "=" * 60)
    print("🌱 SEEDING FAKE DATA")
    print("=" * 60 + "\n")

    # Generate data
    print("🎲 Generating fake data...")
    customers_df = generate_customers(100)
    print(f"  ✓ Generated {len(customers_df)} customers")

    products_df = generate_products(50)
    print(f"  ✓ Generated {len(products_df)} products")

    orders_df, order_items_df = generate_orders(customers_df, products_df, 500)
    print(f"  ✓ Generated {len(orders_df)} orders with {len(order_items_df)} items")

    # Connect to database
    print("\n📡 Connecting to PostgreSQL...")
    with PostgresConnector() as pg:
        # Create schema and tables
        create_raw_schema(pg)

        # Insert data
        print("\n💾 Loading data into PostgreSQL...")

        print("  → Inserting customers...")
        pg.insert_dataframe(customers_df, 'raw.customers')

        print("  → Inserting products...")
        pg.insert_dataframe(products_df, 'raw.products')

        print("  → Inserting orders...")
        pg.insert_dataframe(orders_df, 'raw.orders')

        print("  → Inserting order items...")
        pg.insert_dataframe(order_items_df, 'raw.order_items')

        print("\n✅ Data loading complete!")

        # Show summary
        print("\n" + "=" * 60)
        print("📊 DATA SUMMARY")
        print("=" * 60)
        result = pg.query_to_dataframe("""
            SELECT
                (SELECT COUNT(*) FROM raw.customers) as customers,
                (SELECT COUNT(*) FROM raw.products) as products,
                (SELECT COUNT(*) FROM raw.orders) as orders,
                (SELECT COUNT(*) FROM raw.order_items) as order_items
        """)
        print(result.to_string(index=False))
        print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        seed_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        raise
