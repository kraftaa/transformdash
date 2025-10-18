"""
Configuration Module - Loads environment variables for database connections
"""
import os
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env file
env_path = Path(__file__).parent / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    """Application configuration loaded from environment variables"""

    # PostgreSQL Configuration
    POSTGRES_HOST = os.getenv('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = int(os.getenv('POSTGRES_PORT', 5432))
    POSTGRES_DB = os.getenv('POSTGRES_DB', 'postgres')
    POSTGRES_USER = os.getenv('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD', '')

    # MongoDB Configuration
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017')
    MONGO_DB = os.getenv('MONGO_DB', 'testdb')

    # Redis Configuration
    REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
    REDIS_DB = int(os.getenv('REDIS_DB', 0))

    @classmethod
    def get_postgres_uri(cls) -> str:
        """Get PostgreSQL connection URI"""
        return f"postgresql://{cls.POSTGRES_USER}:{cls.POSTGRES_PASSWORD}@{cls.POSTGRES_HOST}:{cls.POSTGRES_PORT}/{cls.POSTGRES_DB}"

    @classmethod
    def get_postgres_params(cls) -> dict:
        """Get PostgreSQL connection parameters as dictionary"""
        return {
            'host': cls.POSTGRES_HOST,
            'port': cls.POSTGRES_PORT,
            'dbname': cls.POSTGRES_DB,
            'user': cls.POSTGRES_USER,
            'password': cls.POSTGRES_PASSWORD
        }

    @classmethod
    def validate(cls) -> bool:
        """Validate that required configuration is present"""
        required = [
            ('POSTGRES_HOST', cls.POSTGRES_HOST),
            ('POSTGRES_USER', cls.POSTGRES_USER),
            ('POSTGRES_DB', cls.POSTGRES_DB)
        ]

        missing = [name for name, value in required if not value]

        if missing:
            raise ValueError(f"Missing required configuration: {', '.join(missing)}")

        return True


# Create a singleton instance
config = Config()

if __name__ == "__main__":
    # Test configuration loading
    print("Configuration loaded successfully!")
    print(f"PostgreSQL: {config.POSTGRES_USER}@{config.POSTGRES_HOST}:{config.POSTGRES_PORT}/{config.POSTGRES_DB}")
    print(f"MongoDB: {config.MONGO_URI}")
    print(f"Redis: {config.REDIS_HOST}:{config.REDIS_PORT}")
