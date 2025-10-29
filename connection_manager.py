"""
Connection Manager - Handles multiple database connections
"""
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from postgres import PostgresConnector


class ConnectionManager:
    """Manages multiple database connections from connections.yml"""

    def __init__(self, config_path: str = "connections.yml"):
        """Initialize connection manager and load connections config"""
        self.config_path = Path(config_path)
        self.connections = {}
        self.default_connection_id = None
        self._load_connections()

    def _load_connections(self):
        """Load connections from YAML config file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Connections config not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        if not config or 'connections' not in config:
            raise ValueError("Invalid connections.yml format: missing 'connections' key")

        for conn_config in config['connections']:
            conn_id = conn_config['id']
            self.connections[conn_id] = conn_config

            # Set default connection
            if conn_config.get('default', False):
                self.default_connection_id = conn_id

        # If no default set, use first connection
        if not self.default_connection_id and self.connections:
            self.default_connection_id = list(self.connections.keys())[0]

    def get_connection(self, connection_id: Optional[str] = None) -> PostgresConnector:
        """
        Get a PostgresConnector for the specified connection
        If connection_id is None, returns default connection
        """
        if connection_id is None:
            connection_id = self.default_connection_id

        if connection_id not in self.connections:
            raise ValueError(f"Connection '{connection_id}' not found in connections.yml")

        conn_config = self.connections[connection_id]

        return PostgresConnector(
            host=conn_config['host'],
            port=conn_config['port'],
            dbname=conn_config['database'],
            user=conn_config['user'],
            password=conn_config['password'],
            use_config=False  # Don't use environment config
        )

    def list_connections(self) -> List[Dict]:
        """
        Get list of all available connections (without passwords)
        Returns simplified connection info for UI
        """
        return [
            {
                'id': conn_id,
                'name': conn_config['name'],
                'database': conn_config['database'],
                'description': conn_config.get('description', ''),
                'default': conn_config.get('default', False)
            }
            for conn_id, conn_config in self.connections.items()
        ]

    def get_connection_info(self, connection_id: str) -> Optional[Dict]:
        """Get connection info (without password) for a specific connection"""
        if connection_id not in self.connections:
            return None

        conn_config = self.connections[connection_id]
        return {
            'id': connection_id,
            'name': conn_config['name'],
            'host': conn_config['host'],
            'port': conn_config['port'],
            'database': conn_config['database'],
            'user': conn_config['user'],
            'description': conn_config.get('description', ''),
            'default': conn_config.get('default', False)
        }

    def get_default_connection_id(self) -> str:
        """Get the ID of the default connection"""
        return self.default_connection_id


# Create a singleton instance
connection_manager = ConnectionManager()


if __name__ == "__main__":
    # Test connection manager
    print("Testing Connection Manager\n")
    print("=" * 60)

    cm = ConnectionManager()

    # List all connections
    print("\n📋 Available Connections:")
    for conn in cm.list_connections():
        default_marker = " (default)" if conn['default'] else ""
        print(f"  • {conn['name']}{default_marker}")
        print(f"    ID: {conn['id']}")
        print(f"    Database: {conn['database']}")
        if conn['description']:
            print(f"    Description: {conn['description']}")
        print()

    # Test default connection
    print(f"\n🔧 Testing default connection: {cm.get_default_connection_id()}")
    with cm.get_connection() as pg:
        if pg.test_connection():
            print("✓ Default connection successful!")
        else:
            print("✗ Default connection failed")
