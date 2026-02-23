"""FAISS vector store service with embeddings."""

import json
import logging
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional

import faiss
from sentence_transformers import SentenceTransformer

from .reranker import RerankerService

logger = logging.getLogger(__name__)


class VectorStoreService:
    """Service for managing FAISS vector store and embeddings."""

    def __init__(
        self,
        index_path: str,
        embedding_model: str,
        reranker_model: Optional[str] = None,
        enable_reranking: bool = False
    ):
        """Initialize vector store service.

        Args:
            index_path: Path to store FAISS index
            embedding_model: Name of the sentence-transformers model
            reranker_model: Optional name of the cross-encoder reranker model
            enable_reranking: Whether to enable reranking
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Initialize reranker if enabled
        self.enable_reranking = enable_reranking
        self.reranker: Optional[RerankerService] = None
        if enable_reranking and reranker_model:
            self.reranker = RerankerService(reranker_model)

        # Initialize FAISS index
        self.index: Optional[faiss.IndexFlatIP] = None
        self.docstore: Dict[str, Any] = {}
        self.chunk_metadata: List[Dict[str, Any]] = []  # Metadata for each chunk

        # File paths
        self.index_file = self.index_path / "faiss.index"
        self.docstore_file = self.index_path / "docstore.json"
        self.metadata_file = self.index_path / "chunk_metadata.pkl"

        self._load_or_create_index()

    def _load_or_create_index(self) -> None:
        """Load existing index or create a new one."""
        if self.index_file.exists():
            try:
                # Load FAISS index
                self.index = faiss.read_index(str(self.index_file))

                # Load docstore
                if self.docstore_file.exists():
                    with open(self.docstore_file, "r") as f:
                        self.docstore = json.load(f)

                # Load chunk metadata
                if self.metadata_file.exists():
                    with open(self.metadata_file, "rb") as f:
                        self.chunk_metadata = pickle.load(f)

                logger.info(f"Loaded FAISS index with {self.index.ntotal} vectors")
            except Exception as e:
                logger.error(f"Error loading existing index: {e}")
                self._create_new_index()
        else:
            self._create_new_index()

    def _create_new_index(self) -> None:
        """Create a new FAISS index."""
        # Use IndexFlatIP for inner product (cosine similarity with normalized vectors)
        self.index = faiss.IndexFlatIP(self.embedding_dim)
        self.docstore = {}
        self.chunk_metadata = []
        logger.info(f"Created new FAISS index with dimension {self.embedding_dim}")

    def _save_index(self) -> None:
        """Save FAISS index and metadata to disk."""
        try:
            # Save FAISS index
            faiss.write_index(self.index, str(self.index_file))

            # Save docstore
            with open(self.docstore_file, "w") as f:
                json.dump(self.docstore, f, indent=2)

            # Save chunk metadata
            with open(self.metadata_file, "wb") as f:
                pickle.dump(self.chunk_metadata, f)

            logger.info("Saved FAISS index and metadata")
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise

    def add_documents(
        self,
        document_id: str,
        texts: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """Add document chunks to the vector store.

        Args:
            document_id: Unique identifier for the document
            texts: List of text chunks to add
            metadatas: Optional list of metadata dicts for each chunk

        Raises:
            ValueError: If texts is empty or insertion fails
            RuntimeError: If FAISS insertion fails
        """
        if not texts:
            logger.warning(f"add_documents called with empty texts for document {document_id}")
            return

        logger.info(f"Adding {len(texts)} chunks for document {document_id}")

        try:
            # Generate embeddings
            logger.debug(f"Generating embeddings for {len(texts)} chunks...")
            embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

            # Normalize embeddings for cosine similarity
            faiss.normalize_L2(embeddings)

            # Prepare metadata
            if metadatas is None:
                metadatas = [{}] * len(texts)

            # Store chunk metadata
            start_idx = len(self.chunk_metadata)
            for i, (text, metadata) in enumerate(zip(texts, metadatas)):
                chunk_meta = {
                    "document_id": document_id,
                    "text": text,
                    "chunk_index": i,
                    "page_number": metadata.get("page_number", 0),
                    "title": metadata.get("title", ""),
                    "year": metadata.get("year", 0),
                    "authors": metadata.get("authors", []),
                    "venue": metadata.get("venue", ""),
                    "section": metadata.get("section", ""),
                    "section_type": metadata.get("section_type", ""),
                    "semantic_density": metadata.get("semantic_density", 0.0),
                    "contains_citation": metadata.get("contains_citation", False),
                    "contains_equation": metadata.get("contains_equation", False),
                    "contains_table_ref": metadata.get("contains_table_ref", False),
                    "contains_figure_ref": metadata.get("contains_figure_ref", False),
                }
                self.chunk_metadata.append(chunk_meta)

            # Add to FAISS index
            self.index.add(embeddings)
            logger.info(f"Successfully added {len(texts)} chunks to FAISS index")

            # Update docstore
            if document_id not in self.docstore:
                self.docstore[document_id] = {"chunk_count": 0, "metadata": {}, "chunk_indices": []}

            # Store the indices in FAISS for this document
            chunk_indices = list(range(start_idx, start_idx + len(texts)))
            self.docstore[document_id]["chunk_indices"].extend(chunk_indices)
            self.docstore[document_id]["chunk_count"] += len(texts)

            if metadatas and metadatas[0]:
                # Store first chunk's metadata as document metadata
                self.docstore[document_id]["metadata"].update(metadatas[0])

            # Save everything
            self._save_index()
            logger.info(f"Docstore updated for document {document_id}")

        except Exception as e:
            logger.error(f"Error in add_documents for {document_id}: {e}")
            raise

    def search(
        self,
        query: str,
        top_k: int = 5,
        filter_document_id: Optional[str] = None,
        filter_document_ids: Optional[List[str]] = None,
        reranker_top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using semantic similarity with optional reranking.

        Args:
            query: Search query
            top_k: Number of final results to return
            filter_document_id: Optional single document ID to filter results (deprecated, use filter_document_ids)
            filter_document_ids: Optional list of document IDs to filter results (for multi-doc queries)
            reranker_top_k: Number of candidates to retrieve before reranking (default: top_k * 4)

        Returns:
            List of search results with text, metadata, and scores
        """
        total_docs = self.index.ntotal if self.index else 0

        if total_docs == 0:
            return []

        # Determine number of candidates to retrieve
        if self.enable_reranking and self.reranker:
            # Retrieve more candidates for reranking
            if reranker_top_k is None:
                reranker_top_k = top_k * 4
            initial_k = min(reranker_top_k, total_docs)
        else:
            # No reranking, retrieve 2x for filtering
            initial_k = min(top_k * 2, total_docs)

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)

        # Build document filter list if specified
        filter_doc_ids = None
        if filter_document_ids:
            filter_doc_ids = set(filter_document_ids)
        elif filter_document_id:
            filter_doc_ids = {filter_document_id}

        # Search in FAISS
        # If we have filters, we need to search more to account for filtering
        search_k = initial_k * 3 if filter_doc_ids else initial_k
        search_k = min(search_k, total_docs)

        distances, indices = self.index.search(query_embedding, search_k)

        # Format results with filtering
        results = []
        for idx, score in zip(indices[0], distances[0]):
            if idx < 0 or idx >= len(self.chunk_metadata):
                continue

            chunk = self.chunk_metadata[idx]
            document_id = chunk["document_id"]
            chunk_text = chunk.get("text", "")

            # Skip tombstoned/deleted chunks to avoid empty retrievals.
            if not document_id or not chunk_text:
                continue

            # Apply document filter if specified
            if filter_doc_ids and document_id not in filter_doc_ids:
                continue

            results.append({
                "text": chunk_text,
                "document_id": document_id,
                "chunk_index": chunk["chunk_index"],
                "score": float(score),
                "metadata": {
                    "page_number": chunk["page_number"],
                    "title": chunk["title"],
                    "year": chunk["year"],
                    "authors": chunk["authors"],
                    "venue": chunk["venue"],
                    "section": chunk["section"],
                    "section_type": chunk["section_type"],
                    "semantic_density": chunk["semantic_density"],
                    "contains_citation": chunk["contains_citation"],
                    "contains_equation": chunk["contains_equation"],
                    "contains_table_ref": chunk["contains_table_ref"],
                    "contains_figure_ref": chunk["contains_figure_ref"],
                },
            })

            # Stop once we have enough results
            if len(results) >= initial_k:
                break

        # Apply reranking if enabled
        if self.enable_reranking and self.reranker and results:
            results = self.reranker.rerank(query, results, top_k=top_k)
        else:
            # No reranking, just return top_k
            results = results[:top_k]

        return results

    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a specific document.

        Args:
            document_id: Document identifier

        Returns:
            Document information or None if not found
        """
        return self.docstore.get(document_id)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and all its chunks from the vector store.

        Args:
            document_id: Document identifier to delete

        Returns:
            True if document was deleted, False if not found
        """
        if document_id not in self.docstore:
            return False

        try:
            # Get chunk indices for this document
            chunk_indices = self.docstore[document_id].get("chunk_indices", [])

            # Mark chunks as deleted (set document_id to empty)
            for idx in chunk_indices:
                if idx < len(self.chunk_metadata):
                    self.chunk_metadata[idx]["document_id"] = ""
                    self.chunk_metadata[idx]["text"] = ""

            # Remove from docstore
            del self.docstore[document_id]

            # Save changes
            self._save_index()

            logger.info(f"Deleted document {document_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the vector store.

        Returns:
            List of document information
        """
        return [
            {"document_id": doc_id, **info} for doc_id, info in self.docstore.items()
        ]

    def get_total_chunks(self) -> int:
        """Get total number of chunks in the collection.

        Returns:
            Total chunk count
        """
        return self.index.ntotal if self.index else 0

    def get_contextual_chunks(
        self,
        chunk_results: List[Dict[str, Any]],
        context_window: int = 1
    ) -> List[Dict[str, Any]]:
        """Expand results with surrounding chunks for better context coherence.

        For each top chunk, fetch ±context_window surrounding chunks from the same document.
        This maintains narrative flow and provides better context to the LLM.

        Args:
            chunk_results: List of retrieved chunks
            context_window: Number of chunks to fetch before/after (default: 1)

        Returns:
            Expanded list of chunks with surrounding context
        """
        if not chunk_results:
            return []

        expanded_chunks = []
        seen_chunk_ids = set()

        for chunk in chunk_results:
            doc_id = chunk.get("document_id", "")
            chunk_idx = chunk.get("chunk_index", 0)

            # Add the original chunk
            chunk_id = f"{doc_id}_chunk_{chunk_idx}"
            if chunk_id not in seen_chunk_ids:
                expanded_chunks.append(chunk)
                seen_chunk_ids.add(chunk_id)

            # Fetch surrounding chunks
            for offset in range(-context_window, context_window + 1):
                if offset == 0:
                    continue  # Skip the original chunk

                neighbor_idx = chunk_idx + offset
                if neighbor_idx < 0:
                    continue

                neighbor_id = f"{doc_id}_chunk_{neighbor_idx}"

                # Skip if already added
                if neighbor_id in seen_chunk_ids:
                    continue

                try:
                    # Find the neighboring chunk in metadata
                    neighbor_chunk = None
                    for meta in self.chunk_metadata:
                        if (meta["document_id"] == doc_id and
                            meta["chunk_index"] == neighbor_idx):
                            neighbor_chunk = meta
                            break

                    if neighbor_chunk and neighbor_chunk["text"]:
                        # Format as search result
                        formatted_chunk = {
                            "text": neighbor_chunk["text"],
                            "document_id": neighbor_chunk["document_id"],
                            "chunk_index": neighbor_chunk["chunk_index"],
                            "score": chunk.get("score", 0.0) * 0.7,  # Lower score for context chunks
                            "is_context": True,  # Mark as context chunk
                            "metadata": {
                                "page_number": neighbor_chunk["page_number"],
                                "title": neighbor_chunk["title"],
                                "year": neighbor_chunk["year"],
                                "authors": neighbor_chunk["authors"],
                                "venue": neighbor_chunk["venue"],
                                "section": neighbor_chunk["section"],
                                "section_type": neighbor_chunk["section_type"],
                                "semantic_density": neighbor_chunk["semantic_density"],
                                "contains_citation": neighbor_chunk["contains_citation"],
                                "contains_equation": neighbor_chunk["contains_equation"],
                                "contains_table_ref": neighbor_chunk["contains_table_ref"],
                                "contains_figure_ref": neighbor_chunk["contains_figure_ref"],
                            },
                        }

                        expanded_chunks.append(formatted_chunk)
                        seen_chunk_ids.add(neighbor_id)
                except Exception:
                    # Skip if fetch fails
                    continue

        # Sort by document_id and chunk_index to maintain reading order
        expanded_chunks.sort(key=lambda x: (x.get("document_id", ""), x.get("chunk_index", 0)))

        return expanded_chunks
