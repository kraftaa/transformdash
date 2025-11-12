"""
Transformation Model - Defines a single data transformation step
"""
from enum import Enum
from typing import List, Dict, Any, Callable, Optional
import pandas as pd

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
            # For views/tables created by previous models, reference schema.name
            if hasattr(self, '_schema'):
                return f"{self._schema}.{model_name}"
            return f"public.{model_name}"

        def source(schema_name, table_name):
            # Reference raw source tables
            return f"{schema_name}.{table_name}"

        def config(**kwargs):
            # config() is stripped out - just return empty string
            return ""

        def is_incremental():
            # Check if model already exists for incremental logic
            return False  # For now, always do full refresh

        # Render the template
        rendered_sql = template.render(
            ref=ref,
            source=source,
            config=config,
            is_incremental=is_incremental,
            this=f"public.{self.name}"  # {{ this }} refers to current model
        )

        # Step 3: Clean up the SQL (remove config lines, extra whitespace)
        # Remove any standalone config() calls
        rendered_sql = re.sub(r'\{\{.*?config\(.*?\).*?\}\}', '', rendered_sql, flags=re.DOTALL)
        rendered_sql = rendered_sql.strip()

        # Step 4: Execute based on materialization strategy
        mat_type = getattr(self, 'config', {}).get('materialized', parsed_config.get('materialized', 'view'))

        with PostgresConnector() as pg:
            if mat_type == 'view':
                # Create or replace view
                create_sql = f"CREATE OR REPLACE VIEW public.{self.name} AS\n{rendered_sql}"
                pg.execute(create_sql)
                # Return a sample of the data
                result_df = pg.query_to_dataframe(f"SELECT * FROM public.{self.name} LIMIT 5")

            elif mat_type == 'table':
                # Create or replace table
                drop_sql = f"DROP TABLE IF EXISTS public.{self.name}"
                create_sql = f"CREATE TABLE public.{self.name} AS\n{rendered_sql}"
                pg.execute(drop_sql)
                pg.execute(create_sql)

                # Create indexes if specified in config
                if 'indexes' in parsed_config:
                    self._create_indexes(pg, parsed_config['indexes'])

                result_df = pg.query_to_dataframe(f"SELECT * FROM public.{self.name} LIMIT 5")

            elif mat_type == 'incremental':
                # For now, treat as table (full refresh)
                # TODO: Implement true incremental logic
                drop_sql = f"DROP TABLE IF EXISTS public.{self.name}"
                create_sql = f"CREATE TABLE public.{self.name} AS\n{rendered_sql}"
                pg.execute(drop_sql)
                pg.execute(create_sql)
                result_df = pg.query_to_dataframe(f"SELECT * FROM public.{self.name} LIMIT 5")

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

            is_unique = index_config.get('unique', False)
            unique_str = 'UNIQUE ' if is_unique else ''

            # Generate index name: tablename_col1_col2_idx
            columns_str = '_'.join(columns)
            index_name = f"{self.name}_{columns_str}_idx"

            # Build column list for index
            columns_list = ', '.join(columns)

            # Create index SQL
            create_index_sql = f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON public.{self.name} ({columns_list})"

            try:
                pg.execute(create_index_sql)
                print(f"Created index {index_name} on {self.name}({columns_list})")
            except Exception as e:
                print(f"Warning: Failed to create index {index_name}: {str(e)}")

    def _write_python_result_to_db(self) -> None:
        """
        Write Python model DataFrame result to database
        Creates a table or view based on materialization strategy
        """
        if not isinstance(self.result, pd.DataFrame):
            raise ValueError(f"Python model {self.name} result must be a pandas DataFrame")

        from postgres import PostgresConnector

        mat_type = getattr(self, 'config', {}).get('materialized', 'table')

        with PostgresConnector() as pg:
            if mat_type == 'view':
                # For views, we need to store the DataFrame as a temp table first,
                # then create a view referencing it
                # For simplicity, we'll just create a table for Python models
                # TODO: Implement proper view creation for Python models
                mat_type = 'table'

            if mat_type == 'table' or mat_type == 'incremental':
                # Drop existing table
                drop_sql = f"DROP TABLE IF EXISTS public.{self.name}"
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
