"""
Parser to extract TransformDash models into searchable knowledge base
"""
import re
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)


class ModelParser:
    """Parse TransformDash SQL/Python models into knowledge base"""

    def __init__(self, models_dir: Path):
        self.models_dir = Path(models_dir)

    def parse(self) -> Dict[str, Any]:
        """
        Parse all models in models_dir into knowledge base

        Returns:
            Dict mapping model names to their metadata
        """
        knowledge = {}

        # Find all .sql files in models directory
        for sql_file in self.models_dir.rglob("*.sql"):
            try:
                model_data = self._parse_sql_file(sql_file)
                if model_data:
                    model_name = sql_file.stem
                    knowledge[model_name] = model_data
            except Exception as e:
                logger.warning(f"Failed to parse {sql_file}: {e}")

        return knowledge

    def _parse_sql_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a single SQL model file

        Extracts:
        - Name (from filename)
        - Description (from comments)
        - Config (materialization type)
        - Dependencies (ref(), source())
        - Columns (from inline docs or schema.yml)
        """
        with open(file_path, 'r') as f:
            content = f.read()

        # Extract description from header comment
        description = self._extract_description(content)

        # Extract config
        config = self._extract_config(content)

        # Extract dependencies
        dependencies = self._extract_dependencies(content)

        # Determine layer from path or filename prefix
        layer = self._determine_layer(file_path)

        return {
            "name": file_path.stem,
            "type": "model",
            "description": description,
            "materialized": config.get("materialized", "view"),
            "layer": layer,
            "depends_on": dependencies.get("refs", []),
            "sources": dependencies.get("sources", []),
            "file_path": str(file_path.relative_to(self.models_dir.parent))
        }

    def _extract_description(self, content: str) -> str:
        """Extract description from SQL comments, skipping config blocks"""
        lines = content.split('\n')
        description_lines = []

        for line in lines:
            stripped = line.strip()
            # Skip config blocks and empty lines
            if stripped.startswith('{{') or not stripped:
                continue
            # Collect comment lines
            if stripped.startswith('--'):
                desc_text = stripped.lstrip('-').strip()
                if desc_text:
                    description_lines.append(desc_text)
            else:
                # Stop at first non-comment SQL line
                break

        return ' '.join(description_lines)

    def _extract_config(self, content: str) -> Dict[str, str]:
        """Extract {{ config(...) }} from SQL"""
        config_match = re.search(
            r'\{\{\s*config\((.*?)\)\s*\}\}',
            content,
            flags=re.DOTALL
        )
        if config_match:
            config_str = config_match.group(1)
            # Parse key=value pairs
            config = {}
            for match in re.finditer(r'(\w+)\s*=\s*[\'"]([^\'"]+)[\'"]', config_str):
                config[match.group(1)] = match.group(2)
            return config
        return {}

    def _extract_dependencies(self, content: str) -> Dict[str, list]:
        """Extract {{ ref() }} and {{ source() }} references"""
        # Find all ref() calls
        refs = re.findall(r'\{\{\s*ref\([\'"](\w+)[\'"]\)\s*\}\}', content)

        # Find all source() calls
        sources = re.findall(
            r'\{\{\s*source\([\'"](\w+)[\'"],\s*[\'"](\w+)[\'"]\)\s*\}\}',
            content
        )
        source_refs = [f"{schema}.{table}" for schema, table in sources]

        return {
            "refs": refs,
            "sources": source_refs
        }

    def _determine_layer(self, file_path: Path) -> str:
        """Determine which layer (bronze/silver/gold) the model belongs to"""
        path_str = str(file_path).lower()
        name = file_path.stem.lower()

        if 'staging' in path_str or name.startswith('stg_'):
            return 'bronze'
        elif 'intermediate' in path_str or name.startswith('int_'):
            return 'silver'
        elif 'marts' in path_str or name.startswith(('fct_', 'dim_')):
            return 'gold'
        else:
            return 'unknown'
