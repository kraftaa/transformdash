"""
Embedding-based semantic search using FAISS and sentence-transformers
"""
import logging
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class EmbeddingSearch:
    """
    Semantic search using sentence embeddings and FAISS

    Uses lightweight all-MiniLM-L6-v2 model (~80MB) for fast embedding generation
    """

    def __init__(self, knowledge: Dict[str, Any], embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding search

        Args:
            knowledge: Dictionary of models from ModelParser
            embedding_model: HuggingFace model name for embeddings
        """
        self.knowledge = knowledge

        # Lazy import to allow module to load even if dependencies not installed
        try:
            import faiss
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise ImportError(
                f"Required dependencies not installed: {e}\n"
                "Install with: pip install sentence-transformers faiss-cpu"
            )

        logger.info(f"Loading embedding model: {embedding_model}")
        self.model = SentenceTransformer(embedding_model)

        # Build FAISS index
        self.index = None
        self.id_to_key = []
        self._build_index()

        logger.info(f"Built FAISS index with {len(self.knowledge)} models")

    def _build_index(self):
        """Build FAISS index from model names and descriptions"""
        import faiss

        texts = []
        self.id_to_key = []

        for key, item in self.knowledge.items():
            # Combine name, description, and layer for better search
            text_parts = [
                item.get('name', ''),
                item.get('description', ''),
                item.get('layer', ''),
            ]
            text = ' '.join(filter(None, text_parts))
            texts.append(text)
            self.id_to_key.append(key)

        if not texts:
            logger.warning("No models to index")
            return

        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

        # Normalize for cosine similarity
        embeddings = embeddings / np.linalg.norm(embeddings, axis=1, keepdims=True)

        # Create FAISS index (IndexFlatIP = inner product, which equals cosine for normalized vectors)
        dim = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        self.index.add(embeddings.astype('float32'))

    def search(self, query: str, top_k: int = 5, min_score: float = 0.25) -> List[Dict[str, Any]]:
        """
        Search for models using natural language query

        Args:
            query: Natural language search query
            top_k: Number of results to return
            min_score: Minimum similarity score threshold (0-1), default 0.25

        Returns:
            List of matching models with similarity scores above threshold
        """
        if self.index is None or len(self.id_to_key) == 0:
            return []

        # Encode query
        query_vec = self.model.encode(query, convert_to_numpy=True)
        query_vec = query_vec / np.linalg.norm(query_vec)  # Normalize
        query_vec = query_vec.astype('float32').reshape(1, -1)

        # Search FAISS index (search more to account for filtering)
        search_k = min(top_k * 2, len(self.id_to_key))
        scores, indices = self.index.search(query_vec, search_k)

        # Build results, filtering by minimum score
        results = []
        for idx, score in zip(indices[0], scores[0]):
            if idx >= 0 and idx < len(self.id_to_key) and score >= min_score:
                key = self.id_to_key[idx]
                model_info = self.knowledge[key]

                results.append({
                    "name": key,
                    "type": model_info.get("type", "model"),
                    "description": model_info.get("description", ""),
                    "layer": model_info.get("layer", "unknown"),
                    "materialized": model_info.get("materialized", "view"),
                    "depends_on": model_info.get("depends_on", []),
                    "file_path": model_info.get("file_path", ""),
                    "similarity_score": float(score)
                })

                # Stop after getting enough results
                if len(results) >= top_k:
                    break

        return results
