"""
Explore database to find tables with data
"""
from postgres import PostgresConnector

with PostgresConnector() as pg:
    print("Checking table row counts...\n")

    tables_to_check = [
        'proposals', 'currencies', 'providers', 'users',
        'organizations', 'purchase_orders', 'invoices',
        'milestones', 'addresses', 'quotes_wares'
    ]

    for table in tables_to_check:
        try:
            result = pg.execute(f"SELECT COUNT(*) as count FROM {table};", fetch=True)
            count = result[0]['count']
            print(f"  {table:30s}: {count:,} rows")
        except Exception as e:
            print(f"  {table:30s}: Error - {e}")
