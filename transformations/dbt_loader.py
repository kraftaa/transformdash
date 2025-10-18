"""
DBT-Style Model Loader
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


class DBTModelLoader:
    """Loads and parses DBT-style SQL models"""

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
        Parse a SQL model file and extract config and dependencies
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
            'file_path': str(file_path)
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
        Load all SQL models from a directory (bronze, silver, gold)
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

                # Store config for later use
                model.config = parsed['config']
                model.file_path = parsed['file_path']

                models.append(model)

        return models

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
