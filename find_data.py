"""
Find tables with data in the database
"""
from postgres import PostgresConnector

with PostgresConnector() as pg:
    print("Finding tables with data...\n")

    tables = pg.get_tables()
    print(f"Total tables found: {len(tables)}\n")

    tables_with_data = []

    for table in tables[:50]:  # Check first 50 tables
        try:
            result = pg.execute(f"SELECT COUNT(*) as count FROM {table};", fetch=True)
            count = result[0]['count']
            if count > 0:
                tables_with_data.append((table, count))
        except Exception as e:
            pass

    if tables_with_data:
        print(f"Found {len(tables_with_data)} tables with data:\n")
        for table, count in sorted(tables_with_data, key=lambda x: x[1], reverse=True):
            print(f"  {table:40s}: {count:,} rows")
    else:
        print("No tables with data found in first 50 tables")
        print("\nFirst 10 table names:")
        for i, table in enumerate(tables[:10], 1):
            print(f"  {i}. {table}")
