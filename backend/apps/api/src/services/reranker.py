"""Reranker service for improving retrieval quality."""

from typing import Any, Dict, List

import numpy as np
from sentence_transformers import CrossEncoder


class RerankerService:
    """Service for reranking search results using cross-encoder models."""

    def __init__(self, model_name: str):
        """Initialize reranker service.

        Args:
            model_name: Name of the cross-encoder model to use
        """
        self.model = CrossEncoder(model_name)
        self.model_name = model_name

    def rerank(
        self,
        query: str,
        documents: List[Dict[str, Any]],
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Rerank documents using cross-encoder model.

        Args:
            query: The search query
            documents: List of document dictionaries with 'text' field
            top_k: Number of top results to return after reranking

        Returns:
            Reranked list of documents with updated scores
        """
        if not documents:
            return []

        # Prepare query-document pairs for cross-encoder
        pairs = [[query, doc["text"]] for doc in documents]

        # Get reranking scores
        scores = self.model.predict(pairs)

        # Normalize scores to 0-1 range using sigmoid
        # Cross-encoder scores are logits (can be negative), sigmoid maps to [0, 1]
        normalized_scores = self._sigmoid(scores)

        # Add reranking scores to documents
        reranked_docs = []
        for doc, raw_score, norm_score in zip(documents, scores, normalized_scores):
            doc_copy = doc.copy()
            doc_copy["retrieval_score"] = doc_copy.get("score", 0.0)  # Keep original FAISS score
            doc_copy["rerank_score_raw"] = float(raw_score)  # Raw cross-encoder logit
            doc_copy["rerank_score"] = float(norm_score)  # Normalized to [0, 1]
            doc_copy["score"] = float(norm_score)  # Use normalized score as primary score
            reranked_docs.append(doc_copy)

        # Sort by normalized rerank score (higher is better)
        reranked_docs.sort(key=lambda x: x["rerank_score"], reverse=True)

        # Return top_k results
        return reranked_docs[:top_k]

    def _sigmoid(self, scores: np.ndarray) -> np.ndarray:
        """Apply sigmoid function to normalize scores to [0, 1] range.

        Args:
            scores: Raw cross-encoder scores (logits)

        Returns:
            Normalized scores in [0, 1] range
        """
        return 1 / (1 + np.exp(-scores))

    def get_model_info(self) -> Dict[str, str]:
        """Get information about the reranker model.

        Returns:
            Dictionary with model information
        """
        return {
            "model_name": self.model_name,
            "type": "cross-encoder"
        }
