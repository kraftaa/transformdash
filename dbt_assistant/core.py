"""
Core DbtAssistant class for semantic search over TransformDash models
"""
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from .parser import ModelParser
from .embed_search import EmbeddingSearch

logger = logging.getLogger(__name__)


class DbtAssistant:
    """
    AI-powered assistant for searching TransformDash models

    Args:
        models_dir: Path to models/ directory
        use_llm: Whether to use LLM for re-ranking (requires OpenAI API key)
    """

    def __init__(self, models_dir: str = "./models", use_llm: bool = False):
        self.models_dir = Path(models_dir)
        self.use_llm = use_llm

        # Parse TransformDash models into knowledge base
        logger.info(f"Parsing models from {self.models_dir}")
        self.parser = ModelParser(self.models_dir)
        self.knowledge = self.parser.parse()

        logger.info(f"Loaded {len(self.knowledge)} models")

        # Initialize embedding search
        self.searcher = EmbeddingSearch(self.knowledge)

        # Initialize LLM if requested
        self.llm = None
        if use_llm:
            try:
                from .llm_ranker import LLMRanker
                self.llm = LLMRanker()
                logger.info("LLM ranker initialized")
            except Exception as e:
                logger.warning(f"LLM not available: {e}")

    def search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Search for models using natural language query

        Args:
            query: Natural language search query
            top_k: Number of results to return

        Returns:
            Dictionary with search results
        """
        # Get embedding-based matches
        embed_results = self.searcher.search(query, top_k=top_k)

        # Optionally use LLM to re-rank
        llm_suggestion = None
        if self.llm:
            try:
                llm_suggestion = self.llm.rank(query, embed_results)
            except Exception as e:
                logger.warning(f"LLM ranking failed: {e}")

        return {
            "query": query,
            "embedding_matches": embed_results,
            "llm_suggestion": llm_suggestion,
            "total_results": len(embed_results)
        }

    def get_model_details(self, model_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model"""
        return self.knowledge.get(model_name)
