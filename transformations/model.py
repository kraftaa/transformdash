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
        Supports Jinja-like {{ ref('model_name') }} syntax for referencing dependencies
        """
        from postgres import PostgresConnector
        import re

        # Process {{ ref('model_name') }} syntax
        # Replace with actual table references or CTEs from context
        processed_query = self.sql_query

        # Find all {{ ref('...') }} patterns
        ref_pattern = r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}"
        refs = re.findall(ref_pattern, self.sql_query)

        # Create CTEs from context data for referenced models
        ctes = []
        for ref_model in refs:
            if ref_model in context and isinstance(context[ref_model], pd.DataFrame):
                # Model result is a DataFrame - create a temporary table name
                temp_table = f"temp_{ref_model}"
                processed_query = re.sub(
                    r"\{\{\s*ref\(['\"]" + ref_model + r"['\"]\)\s*\}\}",
                    temp_table,
                    processed_query
                )
                # Note: We'll need to create temp tables in the database
                # For now, this documents the pattern
                ctes.append((ref_model, temp_table, context[ref_model]))

        # Execute SQL query
        with PostgresConnector() as pg:
            # Create temporary tables from context DataFrames
            for ref_model, temp_table, df in ctes:
                # This would ideally use CREATE TEMPORARY TABLE
                # For now, we skip this and use direct query execution
                pass

            # Execute the processed query
            result_df = pg.query_to_dataframe(processed_query)
            return result_df

    def __repr__(self):
        return f"Model(name={self.name}, type={self.model_type.value}, depends_on={self.depends_on}, status={self.status})"
