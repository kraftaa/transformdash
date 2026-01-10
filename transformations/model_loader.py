"""
Model Loader
Loads SQL models from files with Jinja templating support
"""
import os
import yaml
import re
from pathlib import Path
from typing import Dict, List, Any
from jinja2 import Environment, FileSystemLoader, Template
try:
    from .model import TransformationModel, ModelType
except ImportError:
    from model import TransformationModel, ModelType


class ModelLoader:
    """Loads and parses SQL models with Jinja templating"""

    def __init__(self, models_dir: str, sources_file: str = None):
        self.models_dir = Path(models_dir)
        self.sources_file = sources_file or self.models_dir / "sources.yml"
        self.sources = {}
        self.models = {}

        # Load sources configuration
        if self.sources_file and Path(self.sources_file).exists():
            self._load_sources()

    def _load_sources(self):
        """Load sources from sources.yml"""
        with open(self.sources_file, 'r') as f:
            config = yaml.safe_load(f)

        if 'sources' in config:
            for source in config['sources']:
                source_name = source['name']
                self.sources[source_name] = {
                    'database': source.get('database', ''),
                    'schema': source.get('schema', 'public'),
                    'tables': {table['name']: table for table in source.get('tables', [])}
                }

    def source(self, source_name: str, table_name: str) -> str:
        """
        DBT source() macro implementation
        Returns the fully qualified table name
        """
        if source_name in self.sources:
            source_config = self.sources[source_name]
            schema = source_config['schema']
            return f"{schema}.{table_name}"
        else:
            # Fallback to simple table name
            return table_name

    def ref(self, model_name: str) -> str:
        """
        DBT ref() macro implementation
        Returns reference to another model (for dependencies)
        """
        # In actual execution, this would be replaced with temp table or CTE
        return f"{{{{ ref('{model_name}') }}}}"

    def config(self, **kwargs) -> Dict[str, Any]:
        """
        DBT config() macro implementation
        Returns configuration dictionary
        """
        return kwargs

    def parse_sql_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a SQL model file and extract config, dependencies, and description
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract config block
        config_match = re.search(r'\{\{\s*config\((.*?)\)\s*\}\}', content, re.DOTALL)
        config = {}
        if config_match:
            config_str = config_match.group(1)
            # Parse simple key=value pairs
            for match in re.finditer(r"(\w+)\s*=\s*['\"]?([^,'\"]+)['\"]?", config_str):
                key, value = match.groups()
                config[key] = value

        # Extract description from leading comments
        description = ""
        lines = content.split('\n')
        description_lines = []
        for line in lines:
            line = line.strip()
            # Skip config line
            if line.startswith('{{') or not line:
                continue
            # Collect comment lines
            if line.startswith('--'):
                desc_text = line.lstrip('-').strip()
                if desc_text:
                    description_lines.append(desc_text)
            else:
                # Stop at first non-comment, non-empty, non-config line
                break
        description = ' '.join(description_lines)

        # Extract dependencies from {{ ref('model_name') }}
        ref_pattern = r"\{\{\s*ref\(['\"]([^'\"]+)['\"]\)\s*\}\}"
        depends_on = list(set(re.findall(ref_pattern, content)))

        # Extract source dependencies from {{ source('source', 'table') }}
        source_pattern = r"\{\{\s*source\(['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\)\s*\}\}"
        source_refs = re.findall(source_pattern, content)

        return {
            'config': config,
            'depends_on': depends_on,
            'source_refs': source_refs,
            'content': content,
            'file_path': str(file_path),
            'description': description
        }

    def parse_python_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a Python model file and extract config and dependencies
        Expected format:

        def config():
            return {'materialized': 'table'}

        def model(dbt):
            # Access upstream models via dbt.ref('model_name')
            df = dbt.ref('upstream_model')
            # ... transformations ...
            return result_df
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract config by parsing the config() function
        config = {}
        config_pattern = r"def\s+config\s*\(\s*\):\s*\n\s*return\s+(\{[^}]+\})"
        config_match = re.search(config_pattern, content, re.MULTILINE)
        if config_match:
            try:
                # Safely evaluate the config dict
                import ast
                config = ast.literal_eval(config_match.group(1))
            except:
                pass

        # Extract dependencies from ref('model_name') calls
        ref_pattern = r"\.ref\(['\"]([^'\"]+)['\"]\)"
        depends_on = list(set(re.findall(ref_pattern, content)))

        # Extract source dependencies from source('source', 'table') calls
        source_pattern = r"\.source\(['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\)"
        source_refs = re.findall(source_pattern, content)

        return {
            'config': config,
            'depends_on': depends_on,
            'source_refs': source_refs,
            'content': content,
            'file_path': str(file_path),
            'description': ''  # TODO: Extract from Python docstrings
        }

    def render_sql(self, content: str, context: Dict[str, Any] = None) -> str:
        """
        Render SQL with Jinja templating
        Supports {{ source() }}, {{ ref() }}, {{ config() }}, {% if %} blocks
        """
        context = context or {}

        # Create Jinja environment with custom functions
        env = Environment()
        env.globals['source'] = self.source
        env.globals['ref'] = self.ref
        env.globals['config'] = self.config
        env.globals['is_incremental'] = lambda: context.get('is_incremental', False)
        env.globals['this'] = context.get('this', 'current_table')

        # Render the template
        template = env.from_string(content)
        rendered = template.render(**context)

        return rendered

    def load_models_from_directory(self, layer: str = None) -> List[TransformationModel]:
        """
        Load all SQL and Python models from a directory (bronze, silver, gold)
        Returns list of TransformationModel objects
        """
        models = []

        # Determine which directories to scan
        if layer:
            scan_dirs = [self.models_dir / layer]
        else:
            scan_dirs = [
                self.models_dir / 'bronze',
                self.models_dir / 'silver',
                self.models_dir / 'gold'
            ]

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue

            # Load SQL models
            for sql_file in scan_dir.glob('*.sql'):
                parsed = self.parse_sql_file(sql_file)
                model_name = sql_file.stem  # filename without extension

                # Create TransformationModel
                model = TransformationModel(
                    name=model_name,
                    model_type=ModelType.SQL,
                    sql_query=parsed['content'],
                    depends_on=parsed['depends_on']
                )

                # Store config and metadata for later use
                model.config = parsed['config']
                model.file_path = parsed['file_path']
                model.description = parsed.get('description', '')

                models.append(model)

            # Load Python models
            for py_file in scan_dir.glob('*.py'):
                parsed = self.parse_python_file(py_file)
                model_name = py_file.stem  # filename without extension

                # Create a Python function wrapper that will be executed
                def create_python_func(file_path, content):
                    def python_func(context):
                        # Execute the Python model
                        return self._execute_python_model(file_path, content, context)
                    return python_func

                # Create TransformationModel
                model = TransformationModel(
                    name=model_name,
                    model_type=ModelType.PYTHON,
                    python_func=create_python_func(py_file, parsed['content']),
                    depends_on=parsed['depends_on']
                )

                # Store config and metadata for later use
                model.config = parsed['config']
                model.file_path = parsed['file_path']
                model.description = parsed.get('description', '')

                models.append(model)

        return models

    def _execute_python_model(self, file_path: Path, content: str, context: Dict[str, Any]) -> Any:
        """
        Execute a Python model file
        Provides dbt-style interface with ref() and source() functions
        """
        import pandas as pd
        from postgres import PostgresConnector

        # Create a dbt-like context object
        class DBTContext:
            def __init__(self, loader, context):
                self.loader = loader
                self.context = context
                self.pg = PostgresConnector()

            def ref(self, model_name: str) -> pd.DataFrame:
                """
                Reference another model - returns DataFrame from that model's table
                """
                # Check if model result is in context (already executed in this run)
                if model_name in self.context.get('models', {}):
                    result = self.context['models'][model_name]
                    if isinstance(result, pd.DataFrame):
                        return result

                # Otherwise, read from database table
                with self.pg as pg:
                    query = f"SELECT * FROM public.{model_name}"
                    df = pg.query_to_dataframe(query)
                return df

            def source(self, source_name: str, table_name: str) -> pd.DataFrame:
                """
                Reference a source table - returns DataFrame from raw source
                """
                with self.pg as pg:
                    schema = self.loader.sources.get(source_name, {}).get('schema', 'public')
                    query = f"SELECT * FROM {schema}.{table_name}"
                    df = pg.query_to_dataframe(query)
                return df

        # Create execution namespace
        namespace = {
            'pd': pd,
            'dbt': DBTContext(self, context),
            '__name__': '__main__',
            '__file__': str(file_path)
        }

        # Execute the Python file
        exec(content, namespace)

        # Call the model() function
        if 'model' not in namespace:
            raise ValueError(f"Python model {file_path.name} must define a model(dbt) function")

        model_func = namespace['model']
        result_df = model_func(namespace['dbt'])

        if not isinstance(result_df, pd.DataFrame):
            raise ValueError(f"Python model {file_path.name} must return a pandas DataFrame")

        return result_df

    def load_all_models(self) -> List[TransformationModel]:
        """Load all models from bronze, silver, and gold layers"""
        return self.load_models_from_directory()


# Example usage
if __name__ == "__main__":
    loader = DBTModelLoader(
        models_dir="/Users/maria/Documents/GitHub/transformdash/models",
        sources_file="/Users/maria/Documents/GitHub/transformdash/models/sources.example.yml"
    )

    # Load all models
    models = loader.load_all_models()

    print(f"Loaded {len(models)} models:\n")
    for model in models:
        print(f"  • {model.name}")
        print(f"    - Type: {model.model_type.value}")
        print(f"    - Depends on: {model.depends_on if model.depends_on else 'None'}")
        print(f"    - Config: {getattr(model, 'config', {})}")
        print()
