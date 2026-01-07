"""
dbt_assistant - AI-powered semantic search for TransformDash models

Optional module that enables natural language search for data models.
Requires: sentence-transformers, faiss-cpu, openai (optional)

Usage:
    from dbt_assistant import DbtAssistant

    assistant = DbtAssistant(models_dir="./models")
    results = assistant.search("Find models related to customer revenue")
"""

try:
    from .core import DbtAssistant
    AVAILABLE = True
except ImportError as e:
    AVAILABLE = False
    IMPORT_ERROR = str(e)

    class DbtAssistant:
        """Dummy class when dependencies not installed"""
        def __init__(self, *args, **kwargs):
            raise ImportError(
                f"dbt_assistant dependencies not installed: {IMPORT_ERROR}\n"
                "Install with: pip install sentence-transformers faiss-cpu"
            )

__all__ = ['DbtAssistant', 'AVAILABLE']
