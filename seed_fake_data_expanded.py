"""
Seed Fake Data - EXPANDED VERSION
Populate PostgreSQL with comprehensive retail/e-commerce dataset
Includes 24 tables across multiple domains:
- Core: customers, products, orders, order_items
- Inventory: warehouses, stock_levels, inventory_adjustments
- Suppliers: suppliers, purchase_orders, supplier_payments
- Shipping: shipments, carriers, tracking_events
- Returns: returns, return_items, refund_transactions
- Payments: payment_transactions, payment_methods
- Marketing: campaigns, promotions, customer_segments
- Employees: employees, sales_reps, commissions
"""
import random
from datetime import datetime, timedelta
from faker import Faker
import pandas as pd
from postgres import PostgresConnector

fake = Faker()
Faker.seed(42)  # For reproducibility
random.seed(42)

# ============================================================================
# CORE DOMAIN - Customers, Products, Orders
# ============================================================================

def generate_customers(n=100):
    """Generate fake customer data"""
    customers = []
    segments = ['VIP', 'Regular', 'New', 'At-Risk']
    for i in range(1, n + 1):
        customers.append({
            'id': i,
            'email': fake.email(),
            'name': fake.name(),
            'created_at': fake.date_time_between(start_date='-2y', end_date='now'),
            'country': fake.country_code(),
            'city': fake.city(),
            'phone': fake.phone_number(),
            'segment': random.choice(segments)
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
            'cost': round(random.uniform(5.0, 300.0), 2),
            'sku': fake.bothify(text='??-####'),
            'weight_kg': round(random.uniform(0.1, 10.0), 2)
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
            'status': random.choice(['completed', 'pending', 'cancelled', 'processing'])
        })
        order_id += 1

    return pd.DataFrame(orders), pd.DataFrame(order_items)


# ============================================================================
# INVENTORY DOMAIN - Warehouses, Stock, Adjustments
# ============================================================================

def generate_warehouses(n=5):
    """Generate warehouse locations"""
    warehouses = []
    for i in range(1, n + 1):
        warehouses.append({
            'id': i,
            'name': f"{fake.city()} Warehouse",
            'location': fake.address(),
            'capacity': random.randint(5000, 50000),
            'manager': fake.name()
        })
    return pd.DataFrame(warehouses)


def generate_stock_levels(products_df, warehouses_df):
    """Generate stock levels for each product in each warehouse"""
    stock_levels = []
    stock_id = 1
    for product_id in products_df['id']:
        for warehouse_id in warehouses_df['id']:
            stock_levels.append({
                'id': stock_id,
                'product_id': product_id,
                'warehouse_id': warehouse_id,
                'quantity': random.randint(0, 500),
                'last_updated': fake.date_time_between(start_date='-30d', end_date='now')
            })
            stock_id += 1
    return pd.DataFrame(stock_levels)


def generate_inventory_adjustments(stock_levels_df, n=100):
    """Generate inventory adjustment records"""
    adjustments = []
    reasons = ['Damaged', 'Lost', 'Found', 'Return', 'Correction']
    for i in range(1, n + 1):
        stock = stock_levels_df.sample(1).iloc[0]
        adjustments.append({
            'id': i,
            'product_id': stock['product_id'],
            'warehouse_id': stock['warehouse_id'],
            'adjustment_qty': random.randint(-50, 50),
            'reason': random.choice(reasons),
            'adjustment_date': fake.date_time_between(start_date='-6m', end_date='now'),
            'notes': fake.sentence()
        })
    return pd.DataFrame(adjustments)


# ============================================================================
# SUPPLIER DOMAIN - Suppliers, Purchase Orders, Payments
# ============================================================================

def generate_suppliers(n=15):
    """Generate supplier data"""
    suppliers = []
    for i in range(1, n + 1):
        suppliers.append({
            'id': i,
            'name': fake.company(),
            'contact_name': fake.name(),
            'email': fake.company_email(),
            'phone': fake.phone_number(),
            'country': fake.country(),
            'rating': round(random.uniform(3.0, 5.0), 1)
        })
    return pd.DataFrame(suppliers)


def generate_purchase_orders(suppliers_df, products_df, n=200):
    """Generate purchase orders from suppliers"""
    purchase_orders = []
    po_items = []
    po_id = 1

    for _ in range(n):
        supplier_id = random.choice(suppliers_df['id'].tolist())
        po_date = fake.date_time_between(start_date='-1y', end_date='now')
        expected_delivery = po_date + timedelta(days=random.randint(7, 30))
        num_items = random.randint(1, 5)

        po_total = 0
        for _ in range(num_items):
            product = products_df.sample(1).iloc[0]
            quantity = random.randint(50, 500)
            unit_cost = product['cost']
            total = quantity * unit_cost
            po_total += total

            po_items.append({
                'id': len(po_items) + 1,
                'purchase_order_id': po_id,
                'product_id': product['id'],
                'quantity': quantity,
                'unit_cost': unit_cost,
                'total': round(total, 2)
            })

        purchase_orders.append({
            'id': po_id,
            'supplier_id': supplier_id,
            'order_date': po_date,
            'expected_delivery': expected_delivery,
            'status': random.choice(['pending', 'received', 'cancelled']),
            'total_amount': round(po_total, 2)
        })
        po_id += 1

    return pd.DataFrame(purchase_orders), pd.DataFrame(po_items)


def generate_supplier_payments(purchase_orders_df, n=150):
    """Generate supplier payment records"""
    payments = []
    for i in range(1, n + 1):
        po = purchase_orders_df.sample(1).iloc[0]
        payments.append({
            'id': i,
            'purchase_order_id': po['id'],
            'payment_date': po['order_date'] + timedelta(days=random.randint(30, 90)),
            'amount': round(po['total_amount'] * random.uniform(0.8, 1.0), 2),
            'payment_method': random.choice(['Bank Transfer', 'Check', 'Wire']),
            'status': random.choice(['paid', 'pending', 'overdue'])
        })
    return pd.DataFrame(payments)


# ============================================================================
# SHIPPING DOMAIN - Carriers, Shipments, Tracking
# ============================================================================

def generate_carriers(n=5):
    """Generate shipping carrier data"""
    carrier_names = ['FedEx', 'UPS', 'DHL', 'USPS', 'Amazon Logistics']
    carriers = []
    for i in range(1, n + 1):
        carriers.append({
            'id': i,
            'name': carrier_names[i-1] if i <= len(carrier_names) else fake.company(),
            'contact_phone': fake.phone_number(),
            'rating': round(random.uniform(3.5, 5.0), 1)
        })
    return pd.DataFrame(carriers)


def generate_shipments(orders_df, carriers_df, warehouses_df):
    """Generate shipment records for completed orders"""
    completed_orders = orders_df[orders_df['status'] == 'completed']
    shipments = []

    for idx, order in completed_orders.iterrows():
        shipments.append({
            'id': len(shipments) + 1,
            'order_id': order['id'],
            'carrier_id': random.choice(carriers_df['id'].tolist()),
            'warehouse_id': random.choice(warehouses_df['id'].tolist()),
            'tracking_number': fake.bothify(text='??###########'),
            'ship_date': order['order_date'] + timedelta(days=random.randint(1, 3)),
            'estimated_delivery': order['order_date'] + timedelta(days=random.randint(5, 10)),
            'actual_delivery': order['order_date'] + timedelta(days=random.randint(4, 12)),
            'status': random.choice(['in_transit', 'delivered', 'delayed'])
        })

    return pd.DataFrame(shipments)


def generate_tracking_events(shipments_df, n=300):
    """Generate tracking events for shipments"""
    events = []
    event_types = ['Picked Up', 'In Transit', 'Out for Delivery', 'Delivered', 'Exception']

    for i in range(1, n + 1):
        shipment = shipments_df.sample(1).iloc[0]
        events.append({
            'id': i,
            'shipment_id': shipment['id'],
            'event_type': random.choice(event_types),
            'location': fake.city(),
            'event_date': shipment['ship_date'] + timedelta(days=random.randint(0, 7)),
            'notes': fake.sentence()
        })

    return pd.DataFrame(events)


# ============================================================================
# RETURNS DOMAIN - Returns, Return Items, Refunds
# ============================================================================

def generate_returns(orders_df, n=50):
    """Generate return records"""
    returns = []
    return_reasons = ['Defective', 'Wrong Item', 'Not as Described', 'Changed Mind', 'Size Issue']

    for i in range(1, n + 1):
        order = orders_df.sample(1).iloc[0]
        returns.append({
            'id': i,
            'order_id': order['id'],
            'return_date': order['order_date'] + timedelta(days=random.randint(5, 30)),
            'reason': random.choice(return_reasons),
            'status': random.choice(['pending', 'approved', 'rejected', 'completed']),
            'notes': fake.sentence()
        })

    return pd.DataFrame(returns)


def generate_return_items(returns_df, order_items_df):
    """Generate return item details"""
    return_items = []
    item_id = 1

    for _, return_record in returns_df.iterrows():
        # Get items from the original order
        order_items = order_items_df[order_items_df['order_id'] == return_record['order_id']]
        if len(order_items) > 0:
            # Return 1-3 items from the order
            num_items = min(random.randint(1, 3), len(order_items))
            items_to_return = order_items.sample(num_items)

            for _, item in items_to_return.iterrows():
                item_qty = int(item['quantity'])
                return_qty = random.randint(1, max(1, item_qty))
                return_items.append({
                    'id': item_id,
                    'return_id': return_record['id'],
                    'order_item_id': int(item['id']),
                    'product_id': int(item['product_id']),
                    'quantity': return_qty,
                    'refund_amount': round(float(item['price']) * return_qty, 2)
                })
                item_id += 1

    return pd.DataFrame(return_items)


def generate_refund_transactions(returns_df, return_items_df):
    """Generate refund transaction records"""
    refunds = []

    for _, return_record in returns_df.iterrows():
        if return_record['status'] in ['approved', 'completed']:
            # Calculate total refund from return items
            return_items = return_items_df[return_items_df['return_id'] == return_record['id']]
            total_refund = return_items['refund_amount'].sum()

            refunds.append({
                'id': len(refunds) + 1,
                'return_id': return_record['id'],
                'refund_date': return_record['return_date'] + timedelta(days=random.randint(1, 7)),
                'amount': round(total_refund, 2),
                'method': random.choice(['Original Payment', 'Store Credit', 'Check']),
                'status': random.choice(['processed', 'pending'])
            })

    return pd.DataFrame(refunds)


# ============================================================================
# PAYMENT DOMAIN - Payment Transactions, Payment Methods
# ============================================================================

def generate_payment_methods(customers_df):
    """Generate customer payment methods"""
    payment_methods = []
    method_id = 1

    for customer_id in customers_df['id']:
        # Each customer has 1-3 payment methods
        num_methods = random.randint(1, 3)
        for _ in range(num_methods):
            payment_methods.append({
                'id': method_id,
                'customer_id': customer_id,
                'type': random.choice(['Credit Card', 'Debit Card', 'PayPal', 'Bank Account']),
                'last_four': fake.bothify(text='####'),
                'expiry_date': fake.date_between(start_date='today', end_date='+3y'),
                'is_default': (_ == 0)  # First one is default
            })
            method_id += 1

    return pd.DataFrame(payment_methods)


def generate_payment_transactions(orders_df, payment_methods_df):
    """Generate payment transaction records"""
    transactions = []

    for _, order in orders_df.iterrows():
        if order['status'] in ['completed', 'processing']:
            # Find a payment method for this customer
            customer_methods = payment_methods_df[payment_methods_df['customer_id'] == order['customer_id']]
            if len(customer_methods) > 0:
                method = customer_methods.sample(1).iloc[0]
                transactions.append({
                    'id': len(transactions) + 1,
                    'order_id': order['id'],
                    'payment_method_id': method['id'],
                    'transaction_date': order['order_date'],
                    'amount': order['total_amount'],
                    'status': random.choice(['success', 'pending', 'failed']),
                    'transaction_id': fake.bothify(text='TXN-##########')
                })

    return pd.DataFrame(transactions)


# ============================================================================
# MARKETING DOMAIN - Campaigns, Promotions, Segments
# ============================================================================

def generate_campaigns(n=10):
    """Generate marketing campaign data"""
    campaigns = []
    channels = ['Email', 'Social Media', 'SMS', 'Display Ads', 'Search']

    for i in range(1, n + 1):
        start_date = fake.date_between(start_date='-1y', end_date='now')
        campaigns.append({
            'id': i,
            'name': fake.catch_phrase(),
            'channel': random.choice(channels),
            'start_date': start_date,
            'end_date': start_date + timedelta(days=random.randint(7, 60)),
            'budget': round(random.uniform(1000, 50000), 2),
            'status': random.choice(['active', 'completed', 'paused'])
        })

    return pd.DataFrame(campaigns)


def generate_promotions(n=20):
    """Generate promotion/discount data"""
    promotions = []
    promo_types = ['Percentage', 'Fixed Amount', 'BOGO', 'Free Shipping']

    for i in range(1, n + 1):
        start_date = fake.date_between(start_date='-6m', end_date='now')
        promotions.append({
            'id': i,
            'code': fake.bothify(text='????##'),
            'type': random.choice(promo_types),
            'discount_value': round(random.uniform(5, 50), 2),
            'start_date': start_date,
            'end_date': start_date + timedelta(days=random.randint(7, 90)),
            'usage_limit': random.randint(100, 10000),
            'times_used': random.randint(0, 500)
        })

    return pd.DataFrame(promotions)


def generate_customer_segments(customers_df):
    """Generate customer segment mapping"""
    segments = []
    segment_id = 1

    segment_names = ['High Value', 'Frequent Buyer', 'New Customer', 'At Risk', 'Dormant']

    for customer_id in customers_df['id']:
        # Assign customer to 1-2 segments
        num_segments = random.randint(1, 2)
        chosen_segments = random.sample(segment_names, num_segments)

        for segment_name in chosen_segments:
            segments.append({
                'id': segment_id,
                'customer_id': customer_id,
                'segment_name': segment_name,
                'assigned_date': fake.date_between(start_date='-1y', end_date='now')
            })
            segment_id += 1

    return pd.DataFrame(segments)


# ============================================================================
# EMPLOYEE DOMAIN - Employees, Sales Reps, Commissions
# ============================================================================

def generate_employees(n=25):
    """Generate employee data"""
    employees = []
    departments = ['Sales', 'Marketing', 'Operations', 'Customer Service', 'IT']

    for i in range(1, n + 1):
        employees.append({
            'id': i,
            'name': fake.name(),
            'email': fake.company_email(),
            'department': random.choice(departments),
            'position': fake.job(),
            'hire_date': fake.date_between(start_date='-5y', end_date='-1m'),
            'salary': round(random.uniform(40000, 120000), 2)
        })

    return pd.DataFrame(employees)


def generate_sales_reps(employees_df):
    """Generate sales representative assignments"""
    sales_employees = employees_df[employees_df['department'] == 'Sales']
    return sales_employees[['id', 'name', 'email']].rename(columns={'id': 'sales_rep_id'})


def generate_commissions(orders_df, sales_reps_df):
    """Generate commission records for sales"""
    commissions = []

    # Assign random sales rep to each completed order
    for _, order in orders_df[orders_df['status'] == 'completed'].iterrows():
        if len(sales_reps_df) > 0:
            sales_rep = sales_reps_df.sample(1).iloc[0]
            commission_rate = random.uniform(0.03, 0.08)
            commission_amount = order['total_amount'] * commission_rate

            commissions.append({
                'id': len(commissions) + 1,
                'order_id': order['id'],
                'sales_rep_id': sales_rep['sales_rep_id'],
                'commission_rate': round(commission_rate, 4),
                'commission_amount': round(commission_amount, 2),
                'paid_date': order['order_date'] + timedelta(days=random.randint(30, 60)),
                'status': random.choice(['paid', 'pending'])
            })

    return pd.DataFrame(commissions)


# ============================================================================
# DATABASE SCHEMA CREATION
# ============================================================================

def create_expanded_schema(pg):
    """Create all schemas and tables for expanded dataset"""
    print("📦 Creating raw schema and all tables...")

    # Create schema
    pg.execute("CREATE SCHEMA IF NOT EXISTS raw")

    # Drop all tables in reverse dependency order
    print("  → Dropping existing tables...")
    tables_to_drop = [
        'commissions', 'sales_reps', 'employees',
        'customer_segments', 'promotions', 'campaigns',
        'payment_transactions', 'payment_methods',
        'refund_transactions', 'return_items', 'returns',
        'tracking_events', 'shipments', 'carriers',
        'supplier_payments', 'purchase_order_items', 'purchase_orders', 'suppliers',
        'inventory_adjustments', 'stock_levels', 'warehouses',
        'order_items', 'orders', 'customers', 'products'
    ]

    for table in tables_to_drop:
        pg.execute(f"DROP TABLE IF EXISTS raw.{table} CASCADE")

    print("  → Creating core tables...")

    # Core tables
    pg.execute("""
        CREATE TABLE raw.customers (
            id INTEGER PRIMARY KEY,
            email VARCHAR(255) UNIQUE,
            name VARCHAR(255),
            created_at TIMESTAMP,
            country VARCHAR(10),
            city VARCHAR(255),
            phone VARCHAR(50),
            segment VARCHAR(50)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.products (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            category VARCHAR(100),
            price DECIMAL(10, 2),
            cost DECIMAL(10, 2),
            sku VARCHAR(50),
            weight_kg DECIMAL(10, 2)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.orders (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES raw.customers(id),
            order_date TIMESTAMP,
            total_amount DECIMAL(10, 2),
            status VARCHAR(50)
        )
    """)

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

    print("  → Creating inventory tables...")

    # Inventory tables
    pg.execute("""
        CREATE TABLE raw.warehouses (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            location TEXT,
            capacity INTEGER,
            manager VARCHAR(255)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.stock_levels (
            id INTEGER PRIMARY KEY,
            product_id INTEGER REFERENCES raw.products(id),
            warehouse_id INTEGER REFERENCES raw.warehouses(id),
            quantity INTEGER,
            last_updated TIMESTAMP
        )
    """)

    pg.execute("""
        CREATE TABLE raw.inventory_adjustments (
            id INTEGER PRIMARY KEY,
            product_id INTEGER REFERENCES raw.products(id),
            warehouse_id INTEGER REFERENCES raw.warehouses(id),
            adjustment_qty INTEGER,
            reason VARCHAR(100),
            adjustment_date TIMESTAMP,
            notes TEXT
        )
    """)

    print("  → Creating supplier tables...")

    # Supplier tables
    pg.execute("""
        CREATE TABLE raw.suppliers (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            contact_name VARCHAR(255),
            email VARCHAR(255),
            phone VARCHAR(50),
            country VARCHAR(100),
            rating DECIMAL(2, 1)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.purchase_orders (
            id INTEGER PRIMARY KEY,
            supplier_id INTEGER REFERENCES raw.suppliers(id),
            order_date TIMESTAMP,
            expected_delivery TIMESTAMP,
            status VARCHAR(50),
            total_amount DECIMAL(10, 2)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.purchase_order_items (
            id INTEGER PRIMARY KEY,
            purchase_order_id INTEGER REFERENCES raw.purchase_orders(id),
            product_id INTEGER REFERENCES raw.products(id),
            quantity INTEGER,
            unit_cost DECIMAL(10, 2),
            total DECIMAL(10, 2)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.supplier_payments (
            id INTEGER PRIMARY KEY,
            purchase_order_id INTEGER REFERENCES raw.purchase_orders(id),
            payment_date TIMESTAMP,
            amount DECIMAL(10, 2),
            payment_method VARCHAR(50),
            status VARCHAR(50)
        )
    """)

    print("  → Creating shipping tables...")

    # Shipping tables
    pg.execute("""
        CREATE TABLE raw.carriers (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            contact_phone VARCHAR(50),
            rating DECIMAL(2, 1)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.shipments (
            id INTEGER PRIMARY KEY,
            order_id INTEGER REFERENCES raw.orders(id),
            carrier_id INTEGER REFERENCES raw.carriers(id),
            warehouse_id INTEGER REFERENCES raw.warehouses(id),
            tracking_number VARCHAR(100),
            ship_date TIMESTAMP,
            estimated_delivery TIMESTAMP,
            actual_delivery TIMESTAMP,
            status VARCHAR(50)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.tracking_events (
            id INTEGER PRIMARY KEY,
            shipment_id INTEGER REFERENCES raw.shipments(id),
            event_type VARCHAR(100),
            location VARCHAR(255),
            event_date TIMESTAMP,
            notes TEXT
        )
    """)

    print("  → Creating returns tables...")

    # Returns tables
    pg.execute("""
        CREATE TABLE raw.returns (
            id INTEGER PRIMARY KEY,
            order_id INTEGER REFERENCES raw.orders(id),
            return_date TIMESTAMP,
            reason VARCHAR(100),
            status VARCHAR(50),
            notes TEXT
        )
    """)

    pg.execute("""
        CREATE TABLE raw.return_items (
            id INTEGER PRIMARY KEY,
            return_id INTEGER REFERENCES raw.returns(id),
            order_item_id INTEGER REFERENCES raw.order_items(id),
            product_id INTEGER REFERENCES raw.products(id),
            quantity INTEGER,
            refund_amount DECIMAL(10, 2)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.refund_transactions (
            id INTEGER PRIMARY KEY,
            return_id INTEGER REFERENCES raw.returns(id),
            refund_date TIMESTAMP,
            amount DECIMAL(10, 2),
            method VARCHAR(100),
            status VARCHAR(50)
        )
    """)

    print("  → Creating payment tables...")

    # Payment tables
    pg.execute("""
        CREATE TABLE raw.payment_methods (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES raw.customers(id),
            type VARCHAR(50),
            last_four VARCHAR(4),
            expiry_date DATE,
            is_default BOOLEAN
        )
    """)

    pg.execute("""
        CREATE TABLE raw.payment_transactions (
            id INTEGER PRIMARY KEY,
            order_id INTEGER REFERENCES raw.orders(id),
            payment_method_id INTEGER REFERENCES raw.payment_methods(id),
            transaction_date TIMESTAMP,
            amount DECIMAL(10, 2),
            status VARCHAR(50),
            transaction_id VARCHAR(100)
        )
    """)

    print("  → Creating marketing tables...")

    # Marketing tables
    pg.execute("""
        CREATE TABLE raw.campaigns (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            channel VARCHAR(100),
            start_date DATE,
            end_date DATE,
            budget DECIMAL(10, 2),
            status VARCHAR(50)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.promotions (
            id INTEGER PRIMARY KEY,
            code VARCHAR(20),
            type VARCHAR(50),
            discount_value DECIMAL(10, 2),
            start_date DATE,
            end_date DATE,
            usage_limit INTEGER,
            times_used INTEGER
        )
    """)

    pg.execute("""
        CREATE TABLE raw.customer_segments (
            id INTEGER PRIMARY KEY,
            customer_id INTEGER REFERENCES raw.customers(id),
            segment_name VARCHAR(100),
            assigned_date DATE
        )
    """)

    print("  → Creating employee tables...")

    # Employee tables
    pg.execute("""
        CREATE TABLE raw.employees (
            id INTEGER PRIMARY KEY,
            name VARCHAR(255),
            email VARCHAR(255),
            department VARCHAR(100),
            position VARCHAR(255),
            hire_date DATE,
            salary DECIMAL(10, 2)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.sales_reps (
            sales_rep_id INTEGER PRIMARY KEY REFERENCES raw.employees(id),
            name VARCHAR(255),
            email VARCHAR(255)
        )
    """)

    pg.execute("""
        CREATE TABLE raw.commissions (
            id INTEGER PRIMARY KEY,
            order_id INTEGER REFERENCES raw.orders(id),
            sales_rep_id INTEGER REFERENCES raw.sales_reps(sales_rep_id),
            commission_rate DECIMAL(6, 4),
            commission_amount DECIMAL(10, 2),
            paid_date TIMESTAMP,
            status VARCHAR(50)
        )
    """)

    print("✓ All schemas and tables created")


# ============================================================================
# MAIN SEEDING FUNCTION
# ============================================================================

def seed_expanded_data():
    """Main function to seed all expanded fake data"""
    print("\n" + "=" * 70)
    print("🌱 SEEDING EXPANDED FAKE DATA - 24 TABLES")
    print("=" * 70 + "\n")

    # Generate core data
    print("🎲 Generating core data...")
    customers_df = generate_customers(100)
    print(f"  ✓ Generated {len(customers_df)} customers")

    products_df = generate_products(50)
    print(f"  ✓ Generated {len(products_df)} products")

    orders_df, order_items_df = generate_orders(customers_df, products_df, 500)
    print(f"  ✓ Generated {len(orders_df)} orders with {len(order_items_df)} items")

    # Generate inventory data
    print("\n📦 Generating inventory data...")
    warehouses_df = generate_warehouses(5)
    print(f"  ✓ Generated {len(warehouses_df)} warehouses")

    stock_levels_df = generate_stock_levels(products_df, warehouses_df)
    print(f"  ✓ Generated {len(stock_levels_df)} stock level records")

    inventory_adjustments_df = generate_inventory_adjustments(stock_levels_df, 100)
    print(f"  ✓ Generated {len(inventory_adjustments_df)} inventory adjustments")

    # Generate supplier data
    print("\n🏭 Generating supplier data...")
    suppliers_df = generate_suppliers(15)
    print(f"  ✓ Generated {len(suppliers_df)} suppliers")

    purchase_orders_df, po_items_df = generate_purchase_orders(suppliers_df, products_df, 200)
    print(f"  ✓ Generated {len(purchase_orders_df)} purchase orders with {len(po_items_df)} items")

    supplier_payments_df = generate_supplier_payments(purchase_orders_df, 150)
    print(f"  ✓ Generated {len(supplier_payments_df)} supplier payments")

    # Generate shipping data
    print("\n🚚 Generating shipping data...")
    carriers_df = generate_carriers(5)
    print(f"  ✓ Generated {len(carriers_df)} carriers")

    shipments_df = generate_shipments(orders_df, carriers_df, warehouses_df)
    print(f"  ✓ Generated {len(shipments_df)} shipments")

    tracking_events_df = generate_tracking_events(shipments_df, 300)
    print(f"  ✓ Generated {len(tracking_events_df)} tracking events")

    # Generate returns data
    print("\n↩️  Generating returns data...")
    returns_df = generate_returns(orders_df, 50)
    print(f"  ✓ Generated {len(returns_df)} returns")

    return_items_df = generate_return_items(returns_df, order_items_df)
    print(f"  ✓ Generated {len(return_items_df)} return items")

    refund_transactions_df = generate_refund_transactions(returns_df, return_items_df)
    print(f"  ✓ Generated {len(refund_transactions_df)} refund transactions")

    # Generate payment data
    print("\n💳 Generating payment data...")
    payment_methods_df = generate_payment_methods(customers_df)
    print(f"  ✓ Generated {len(payment_methods_df)} payment methods")

    payment_transactions_df = generate_payment_transactions(orders_df, payment_methods_df)
    print(f"  ✓ Generated {len(payment_transactions_df)} payment transactions")

    # Generate marketing data
    print("\n📢 Generating marketing data...")
    campaigns_df = generate_campaigns(10)
    print(f"  ✓ Generated {len(campaigns_df)} campaigns")

    promotions_df = generate_promotions(20)
    print(f"  ✓ Generated {len(promotions_df)} promotions")

    customer_segments_df = generate_customer_segments(customers_df)
    print(f"  ✓ Generated {len(customer_segments_df)} customer segment assignments")

    # Generate employee data
    print("\n👥 Generating employee data...")
    employees_df = generate_employees(25)
    print(f"  ✓ Generated {len(employees_df)} employees")

    sales_reps_df = generate_sales_reps(employees_df)
    print(f"  ✓ Generated {len(sales_reps_df)} sales reps")

    commissions_df = generate_commissions(orders_df, sales_reps_df)
    print(f"  ✓ Generated {len(commissions_df)} commission records")

    # Connect to database
    print("\n📡 Connecting to PostgreSQL...")
    with PostgresConnector() as pg:
        # Create schema and tables
        create_expanded_schema(pg)

        # Insert data in dependency order
        print("\n💾 Loading data into PostgreSQL...")

        print("  → Inserting core data...")
        pg.insert_dataframe(customers_df, 'raw.customers')
        pg.insert_dataframe(products_df, 'raw.products')
        pg.insert_dataframe(orders_df, 'raw.orders')
        pg.insert_dataframe(order_items_df, 'raw.order_items')

        print("  → Inserting inventory data...")
        pg.insert_dataframe(warehouses_df, 'raw.warehouses')
        pg.insert_dataframe(stock_levels_df, 'raw.stock_levels')
        pg.insert_dataframe(inventory_adjustments_df, 'raw.inventory_adjustments')

        print("  → Inserting supplier data...")
        pg.insert_dataframe(suppliers_df, 'raw.suppliers')
        pg.insert_dataframe(purchase_orders_df, 'raw.purchase_orders')
        pg.insert_dataframe(po_items_df, 'raw.purchase_order_items')
        pg.insert_dataframe(supplier_payments_df, 'raw.supplier_payments')

        print("  → Inserting shipping data...")
        pg.insert_dataframe(carriers_df, 'raw.carriers')
        pg.insert_dataframe(shipments_df, 'raw.shipments')
        pg.insert_dataframe(tracking_events_df, 'raw.tracking_events')

        print("  → Inserting returns data...")
        pg.insert_dataframe(returns_df, 'raw.returns')
        pg.insert_dataframe(return_items_df, 'raw.return_items')
        pg.insert_dataframe(refund_transactions_df, 'raw.refund_transactions')

        print("  → Inserting payment data...")
        pg.insert_dataframe(payment_methods_df, 'raw.payment_methods')
        pg.insert_dataframe(payment_transactions_df, 'raw.payment_transactions')

        print("  → Inserting marketing data...")
        pg.insert_dataframe(campaigns_df, 'raw.campaigns')
        pg.insert_dataframe(promotions_df, 'raw.promotions')
        pg.insert_dataframe(customer_segments_df, 'raw.customer_segments')

        print("  → Inserting employee data...")
        pg.insert_dataframe(employees_df, 'raw.employees')
        pg.insert_dataframe(sales_reps_df, 'raw.sales_reps')
        pg.insert_dataframe(commissions_df, 'raw.commissions')

        print("\n✅ Data loading complete!")

        # Show summary
        print("\n" + "=" * 70)
        print("📊 DATA SUMMARY - 24 TABLES")
        print("=" * 70)

        tables = [
            'customers', 'products', 'orders', 'order_items',
            'warehouses', 'stock_levels', 'inventory_adjustments',
            'suppliers', 'purchase_orders', 'purchase_order_items', 'supplier_payments',
            'carriers', 'shipments', 'tracking_events',
            'returns', 'return_items', 'refund_transactions',
            'payment_methods', 'payment_transactions',
            'campaigns', 'promotions', 'customer_segments',
            'employees', 'sales_reps', 'commissions'
        ]

        for i in range(0, len(tables), 3):
            batch = tables[i:i+3]
            counts = []
            for table in batch:
                result = pg.query_to_dataframe(f"SELECT COUNT(*) as count FROM raw.{table}")
                counts.append(f"{table}: {result['count'][0]}")
            print(f"  {' | '.join(counts)}")

        print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        seed_expanded_data()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
