"""
Transformation Model - Defines a single data transformation step
"""
import re
from enum import Enum
from typing import List, Dict, Any, Callable, Optional
import pandas as pd
from psycopg2 import sql as psycopg2_sql


def validate_sql_identifier(name: str) -> str:
    """Validate that a string is a safe SQL identifier"""
    if not name:
        raise ValueError("SQL identifier cannot be empty")
    if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
        raise ValueError(f"Invalid SQL identifier '{name}': must contain only letters, numbers, and underscores")
    return name

class ModelType(Enum):
    SQL = "sql"
    PYTHON = "python"

class TransformationModel:
    def __init__(
        self,
        name: str,
        model_type: ModelType,
        depends_on: List[str] = None,
        sql_query: str = None,
        python_func: Callable = None,
        source_connector: str = None,
        destination: str = None
    ):
        self.name = name
        self.model_type = model_type
        self.depends_on = depends_on or []
        self.sql_query = sql_query
        self.python_func = python_func
        self.source_connector = source_connector
        self.destination = destination
        self.result = None
        self.status = "pending"  # pending, running, completed, failed
        self.error = None

    def execute(self, context: Dict[str, Any]) -> Any:
        """
        Execute the transformation
        context: Dictionary containing results from dependent models
        """
        self.status = "running"
        try:
            if self.model_type == ModelType.PYTHON:
                if self.python_func:
                    self.result = self.python_func(context)
                    # Write Python model results to database
                    self._write_python_result_to_db()
                else:
                    raise ValueError(f"No Python function defined for model {self.name}")
            elif self.model_type == ModelType.SQL:
                if self.sql_query:
                    # For MVP, we'll simulate SQL execution
                    # In production, this would connect to actual DB
                    self.result = self._execute_sql(context)
                else:
                    raise ValueError(f"No SQL query defined for model {self.name}")

            self.status = "completed"
            return self.result
        except Exception as e:
            self.status = "failed"
            self.error = str(e)
            raise

    def _execute_sql(self, context: Dict[str, Any]) -> pd.DataFrame:
        """
        Execute SQL query against database
        Renders Jinja2 templates and creates views/tables based on materialization
        """
        from postgres import PostgresConnector
        from jinja2 import Template
        import re
        import ast

        # Step 1: Extract config from SQL before rendering
        config_match = re.search(r'\{\{.*?config\((.*?)\).*?\}\}', self.sql_query, flags=re.DOTALL)
        parsed_config = {}
        if config_match:
            try:
                # Extract the config parameters
                config_str = config_match.group(1)
                # Parse kwargs-style config (key=value) into dict
                # Convert key=value to "key": value for JSON parsing
                config_str = config_str.strip()
                # Replace key= with "key": for JSON format
                config_str = re.sub(r'(\w+)=', r'"\1":', config_str)
                # Replace single quotes with double quotes for JSON
                config_str = config_str.replace("'", '"')
                # Remove trailing commas before ] or } (JSON doesn't allow them)
                config_str = re.sub(r',(\s*[\]}])', r'\1', config_str)
                # Parse as JSON
                import json
                parsed_config = json.loads(f"{{{config_str}}}")
            except Exception as e:
                # If parsing fails, silently continue without config
                import logging
                logging.debug(f"Failed to parse config: {e}")
                pass

        # Step 2: Render Jinja2 templates
        # Create Jinja2 environment with our custom functions
        template = Template(self.sql_query)

        # Define helper functions for Jinja2
        def ref(model_name):
            # Validate model_name to prevent SQL injection
            validate_sql_identifier(model_name)
            # For views/tables created by previous models, reference schema.name
            if hasattr(self, '_schema'):
                schema = self._schema
                validate_sql_identifier(schema)
                return f"{schema}.{model_name}"
            return f"public.{model_name}"

        def source(schema_name, table_name):
            # Validate identifiers to prevent SQL injection
            validate_sql_identifier(schema_name)
            validate_sql_identifier(table_name)
            # Reference raw source tables
            return f"{schema_name}.{table_name}"

        def config(**kwargs):
            # config() is stripped out - just return empty string
            return ""

        def is_incremental():
            # Check if model already exists for incremental logic
            return False  # For now, always do full refresh

        def asset(asset_name):
            """
            Load an asset by name and return a reference to it
            For CSV/Excel files: creates a temp table and returns table name
            For SQL files: returns the SQL content
            For Python files: returns import-ready path
            """
            from connection_manager import connection_manager
            import logging

            try:
                # Get asset from database
                with connection_manager.get_connection('transformdash') as pg:
                    result = pg.execute("""
                        SELECT id, name, asset_type, file_path, metadata
                        FROM assets
                        WHERE name = %s AND is_active = TRUE
                    """, (asset_name,), fetch=True)

                    if not result:
                        raise ValueError(f"Asset '{asset_name}' not found")

                    asset_info = result[0]
                    asset_type = asset_info['asset_type']
                    file_path = Path(__file__).parent.parent / "assets" / asset_info['file_path']

                    if not file_path.exists():
                        raise ValueError(f"Asset file not found: {file_path}")

                    # Handle different asset types
                    if asset_type in ['csv', 'excel']:
                        # Load CSV/Excel as a temp table
                        import pandas as pd
                        df = pd.read_csv(file_path) if asset_type == 'csv' else pd.read_excel(file_path)

                        # Create temp table name - sanitize to ensure valid SQL identifier
                        safe_asset_name = re.sub(r'[^a-zA-Z0-9_]', '_', asset_name)
                        temp_table = f"_asset_{asset_info['id']}_{safe_asset_name}"
                        # Validate the constructed identifier
                        validate_sql_identifier(temp_table)

                        # Drop if exists and create temp table using safe SQL construction
                        with PostgresConnector() as pg_conn:
                            drop_query = psycopg2_sql.SQL("DROP TABLE IF EXISTS {}").format(
                                psycopg2_sql.Identifier(temp_table)
                            )
                            pg_conn.execute(drop_query)

                            # Write dataframe to temp table
                            from sqlalchemy import create_engine
                            import os
                            db_host = os.getenv("POSTGRES_HOST", "localhost")
                            db_port = os.getenv("POSTGRES_PORT", "5432")
                            db_name = os.getenv("POSTGRES_DB", "transformdash")
                            db_user = os.getenv("POSTGRES_USER", "postgres")
                            db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")
                            engine = create_engine(f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

                            df.to_sql(temp_table, engine, if_exists='replace', index=False)
                            engine.dispose()

                            logging.info(f"Loaded asset '{asset_name}' as table '{temp_table}'")

                        return temp_table

                    elif asset_type == 'sql':
                        # Return SQL content
                        with open(file_path, 'r') as f:
                            sql_content = f.read()
                        logging.info(f"Loaded SQL asset '{asset_name}'")
                        return sql_content

                    elif asset_type in ['python', 'json', 'yaml']:
                        # Return file path for import/loading
                        logging.info(f"Loaded asset '{asset_name}' from {file_path}")
                        return str(file_path)

                    else:
                        # For other types, return file path
                        return str(file_path)

            except Exception as e:
                import logging
                logging.error(f"Error loading asset '{asset_name}': {str(e)}")
                raise ValueError(f"Failed to load asset '{asset_name}': {str(e)}")

        # Import ML functions
        from ml.jinja_functions import ML_JINJA_FUNCTIONS

        # Render the template
        rendered_sql = template.render(
            ref=ref,
            source=source,
            config=config,
            is_incremental=is_incremental,
            asset=asset,
            this=f"public.{self.name}",  # {{ this }} refers to current model
            **ML_JINJA_FUNCTIONS  # Add all ML functions
        )

        # Step 3: Clean up the SQL (remove config lines, extra whitespace)
        # Remove any standalone config() calls
        rendered_sql = re.sub(r'\{\{.*?config\(.*?\).*?\}\}', '', rendered_sql, flags=re.DOTALL)
        rendered_sql = rendered_sql.strip()

        # Step 4: Execute based on materialization strategy
        mat_type = getattr(self, 'config', {}).get('materialized', parsed_config.get('materialized', 'view'))

        # Validate model name before using in DDL statements
        validate_sql_identifier(self.name)

        with PostgresConnector() as pg:
            if mat_type == 'view':
                # Create or replace view using safe SQL construction
                create_sql = psycopg2_sql.SQL("CREATE OR REPLACE VIEW public.{} AS\n").format(
                    psycopg2_sql.Identifier(self.name)
                ).as_string(pg.conn) + rendered_sql
                pg.execute(create_sql)
                # Return a sample of the data
                select_query = psycopg2_sql.SQL("SELECT * FROM public.{} LIMIT 5").format(
                    psycopg2_sql.Identifier(self.name)
                ).as_string(pg.conn)
                result_df = pg.query_to_dataframe(select_query)

            elif mat_type == 'table':
                # Create or replace table using safe SQL construction
                drop_sql = psycopg2_sql.SQL("DROP TABLE IF EXISTS public.{}").format(
                    psycopg2_sql.Identifier(self.name)
                )
                create_sql = psycopg2_sql.SQL("CREATE TABLE public.{} AS\n").format(
                    psycopg2_sql.Identifier(self.name)
                ).as_string(pg.conn) + rendered_sql
                pg.execute(drop_sql)
                pg.execute(create_sql)

                # Create indexes if specified in config
                if 'indexes' in parsed_config:
                    self._create_indexes(pg, parsed_config['indexes'])

                select_query = psycopg2_sql.SQL("SELECT * FROM public.{} LIMIT 5").format(
                    psycopg2_sql.Identifier(self.name)
                ).as_string(pg.conn)
                result_df = pg.query_to_dataframe(select_query)

            elif mat_type == 'incremental':
                # For now, treat as table (full refresh)
                # TODO: Implement true incremental logic
                drop_sql = psycopg2_sql.SQL("DROP TABLE IF EXISTS public.{}").format(
                    psycopg2_sql.Identifier(self.name)
                )
                create_sql = psycopg2_sql.SQL("CREATE TABLE public.{} AS\n").format(
                    psycopg2_sql.Identifier(self.name)
                ).as_string(pg.conn) + rendered_sql
                pg.execute(drop_sql)
                pg.execute(create_sql)
                select_query = psycopg2_sql.SQL("SELECT * FROM public.{} LIMIT 5").format(
                    psycopg2_sql.Identifier(self.name)
                ).as_string(pg.conn)
                result_df = pg.query_to_dataframe(select_query)

            else:
                # Default: just execute and return results
                result_df = pg.query_to_dataframe(rendered_sql)

            return result_df

    def _create_indexes(self, pg, indexes: List[Dict[str, Any]]) -> None:
        """
        Create indexes on the table based on dbt config
        indexes format: [{"columns": ["col1", "col2"], "unique": True}, ...]
        """
        for idx, index_config in enumerate(indexes):
            columns = index_config.get('columns', [])
            if not columns:
                continue

            # Validate all column names
            for col in columns:
                validate_sql_identifier(col)

            is_unique = index_config.get('unique', False)

            # Generate index name: tablename_col1_col2_idx
            columns_str = '_'.join(columns)
            index_name = f"{self.name}_{columns_str}_idx"
            validate_sql_identifier(index_name)

            # Build CREATE INDEX SQL using safe construction
            unique_prefix = psycopg2_sql.SQL("UNIQUE ") if is_unique else psycopg2_sql.SQL("")
            column_identifiers = psycopg2_sql.SQL(', ').join(
                [psycopg2_sql.Identifier(col) for col in columns]
            )
            create_index_sql = psycopg2_sql.SQL("CREATE {}INDEX IF NOT EXISTS {} ON public.{} ({})").format(
                unique_prefix,
                psycopg2_sql.Identifier(index_name),
                psycopg2_sql.Identifier(self.name),
                column_identifiers
            )

            try:
                import logging
                logging.info(f"Attempting to create index: {index_name}")
                pg.execute(create_index_sql, fetch=False)
                # Explicitly commit to ensure index is persisted
                pg.conn.commit()
                logging.info(f"Successfully created and committed index {index_name}")
                print(f"Created index {index_name} on {self.name}({', '.join(columns)})")

                # Verify index was created using parameterized query
                check_sql = "SELECT indexname FROM pg_indexes WHERE tablename = %s AND indexname = %s"
                result = pg.execute(check_sql, (self.name, index_name), fetch=True)
                if result:
                    logging.info(f"Verified index exists: {result}")
                else:
                    error_msg = f"Index verification failed - index {index_name} not found in pg_indexes"
                    logging.error(error_msg)
                    raise RuntimeError(error_msg)
            except RuntimeError:
                # Re-raise verification errors
                raise
            except Exception as e:
                error_msg = f"Failed to create index {index_name}: {str(e)}"
                logging.error(f"Index creation error: {error_msg}")
                raise RuntimeError(error_msg)

    def _write_python_result_to_db(self) -> None:
        """
        Write Python model DataFrame result to database
        Creates a table or view based on materialization strategy
        """
        if not isinstance(self.result, pd.DataFrame):
            raise ValueError(f"Python model {self.name} result must be a pandas DataFrame")

        from postgres import PostgresConnector

        # Validate model name before using in DDL statements
        validate_sql_identifier(self.name)

        mat_type = getattr(self, 'config', {}).get('materialized', 'table')

        with PostgresConnector() as pg:
            if mat_type == 'view':
                # For views, we need to store the DataFrame as a temp table first,
                # then create a view referencing it
                # For simplicity, we'll just create a table for Python models
                # TODO: Implement proper view creation for Python models
                mat_type = 'table'

            if mat_type == 'table' or mat_type == 'incremental':
                # Drop existing table using safe SQL construction
                drop_sql = psycopg2_sql.SQL("DROP TABLE IF EXISTS public.{}").format(
                    psycopg2_sql.Identifier(self.name)
                )
                pg.execute(drop_sql)

                # Write DataFrame to database using pandas to_sql
                # This requires sqlalchemy engine
                from sqlalchemy import create_engine
                import os

                db_host = os.getenv("POSTGRES_HOST", "localhost")
                db_port = os.getenv("POSTGRES_PORT", "5432")
                db_name = os.getenv("POSTGRES_DB", "transformdash")
                db_user = os.getenv("POSTGRES_USER", "postgres")
                db_pass = os.getenv("POSTGRES_PASSWORD", "postgres")

                engine = create_engine(f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}")

                # Write DataFrame to table
                self.result.to_sql(
                    name=self.name,
                    con=engine,
                    schema='public',
                    if_exists='replace',
                    index=False
                )

                engine.dispose()

    def __repr__(self):
        return f"Model(name={self.name}, type={self.model_type.value}, depends_on={self.depends_on}, status={self.status})"
