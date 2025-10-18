import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
from typing import Optional, List, Dict, Any
from config import config

class PostgresConnector:
    """
    Enhanced PostgreSQL connector with environment config support
    Supports both direct parameters and automatic config loading
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        use_config: bool = True
    ):
        """
        Initialize PostgreSQL connector
        If use_config=True and parameters are None, loads from environment config
        """
        if use_config:
            self.conn_params = {
                "host": host or config.POSTGRES_HOST,
                "port": port or config.POSTGRES_PORT,
                "dbname": dbname or config.POSTGRES_DB,
                "user": user or config.POSTGRES_USER,
                "password": password or config.POSTGRES_PASSWORD,
            }
        else:
            self.conn_params = {
                "host": host,
                "port": port,
                "dbname": dbname,
                "user": user,
                "password": password,
            }
        self.conn = None

    def connect(self):
        """Establish database connection"""
        if self.conn is None or self.conn.closed:
            self.conn = psycopg2.connect(**self.conn_params)
        return self

    def execute(self, query: str, params: Optional[tuple] = None, fetch: bool = False) -> Optional[List[Dict]]:
        """
        Execute a SQL query
        Returns list of dicts if fetch=True, None otherwise
        """
        if not self.conn or self.conn.closed:
            raise ConnectionError("Not connected to database. Call connect() first.")

        with self.conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(query, params)
            if fetch:
                return cur.fetchall()
            else:
                self.conn.commit()
                return None

    def query_to_dataframe(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute query and return results as pandas DataFrame
        Perfect for data transformation pipelines
        """
        if not self.conn or self.conn.closed:
            raise ConnectionError("Not connected to database. Call connect() first.")

        return pd.read_sql_query(query, self.conn, params=params)

    def get_tables(self) -> List[str]:
        """Get list of all tables in current database"""
        query = """
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename;
        """
        results = self.execute(query, fetch=True)
        return [row['tablename'] for row in results]

    def get_table_info(self, table_name: str) -> pd.DataFrame:
        """Get column information for a specific table"""
        query = """
            SELECT
                column_name,
                data_type,
                is_nullable,
                column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
        """
        return self.query_to_dataframe(query, (table_name,))

    def test_connection(self) -> bool:
        """Test if connection is working"""
        try:
            result = self.execute("SELECT 1 as test;", fetch=True)
            return result[0]['test'] == 1
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def close(self):
        """Close database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()

    def __enter__(self):
        """Context manager entry"""
        return self.connect()

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


# Usage example
if __name__ == "__main__":
    print("Testing PostgreSQL Connector with Environment Config\n")
    print("=" * 60)

    # Option 1: Use environment config (recommended)
    with PostgresConnector() as pg:
        print("✓ Connected using environment config")
        print(f"  Database: {pg.conn_params['dbname']}")
        print(f"  User: {pg.conn_params['user']}")
        print(f"  Host: {pg.conn_params['host']}")

        if pg.test_connection():
            print("\n✓ Connection test passed!")

            # Get list of tables
            tables = pg.get_tables()
            print(f"\n📋 Found {len(tables)} tables in database")
            for i, table in enumerate(tables[:5], 1):
                print(f"  {i}. {table}")
            if len(tables) > 5:
                print(f"  ... and {len(tables) - 5} more")
        else:
            print("\n✗ Connection test failed")
