"""FAISS vector store service with embeddings."""

import json
import os
import pickle
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class VectorStoreService:
    """Service for managing FAISS vector store and embeddings."""

    def __init__(self, index_path: str, embedding_model: str):
        """Initialize vector store service.

        Args:
            index_path: Path to store FAISS index and metadata
            embedding_model: Name of the sentence-transformers model
        """
        self.index_path = Path(index_path)
        self.index_path.mkdir(parents=True, exist_ok=True)

        self.index_file = self.index_path / "faiss.index"
        self.metadata_file = self.index_path / "metadata.pkl"
        self.docstore_file = self.index_path / "docstore.json"

        # Initialize embedding model
        self.embedding_model = SentenceTransformer(embedding_model)
        self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()

        # Initialize or load FAISS index
        self.index: Optional[faiss.IndexFlatL2] = None
        self.metadata: List[Dict[str, Any]] = []
        self.docstore: Dict[str, Any] = {}

        self._load_or_create_index()

    def _load_or_create_index(self) -> None:
        """Load existing index or create a new one."""
        if self.index_file.exists():
            # Load existing index
            self.index = faiss.read_index(str(self.index_file))

            # Load metadata
            if self.metadata_file.exists():
                with open(self.metadata_file, "rb") as f:
                    self.metadata = pickle.load(f)

            # Load docstore
            if self.docstore_file.exists():
                with open(self.docstore_file, "r") as f:
                    self.docstore = json.load(f)
        else:
            # Create new index
            self.index = faiss.IndexFlatL2(self.embedding_dim)
            self.metadata = []
            self.docstore = {}

    def _save_index(self) -> None:
        """Save index and metadata to disk."""
        faiss.write_index(self.index, str(self.index_file))

        with open(self.metadata_file, "wb") as f:
            pickle.dump(self.metadata, f)

        with open(self.docstore_file, "w") as f:
            json.dump(self.docstore, f, indent=2)

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
        """
        if not texts:
            return

        # Generate embeddings
        embeddings = self.embedding_model.encode(texts, convert_to_numpy=True)

        # Add to FAISS index
        self.index.add(embeddings)

        # Store metadata
        if metadatas is None:
            metadatas = [{}] * len(texts)

        for i, (text, metadata) in enumerate(zip(texts, metadatas)):
            self.metadata.append(
                {
                    "document_id": document_id,
                    "text": text,
                    "chunk_index": i,
                    **metadata,
                }
            )

        # Update docstore
        if document_id not in self.docstore:
            self.docstore[document_id] = {"chunk_count": 0, "metadata": {}}

        self.docstore[document_id]["chunk_count"] += len(texts)
        if metadatas and metadatas[0]:
            self.docstore[document_id]["metadata"].update(metadatas[0])

        # Save to disk
        self._save_index()

    def search(
        self, query: str, top_k: int = 5, filter_document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using semantic similarity.

        Args:
            query: Search query
            top_k: Number of results to return
            filter_document_id: Optional document ID to filter results

        Returns:
            List of search results with text, metadata, and scores
        """
        if self.index.ntotal == 0:
            return []

        # Generate query embedding
        query_embedding = self.embedding_model.encode([query], convert_to_numpy=True)

        # Search FAISS index
        distances, indices = self.index.search(query_embedding, min(top_k * 2, self.index.ntotal))

        # Format results
        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:
                continue

            metadata = self.metadata[idx]

            # Apply filter if specified
            if filter_document_id and metadata.get("document_id") != filter_document_id:
                continue

            results.append(
                {
                    "text": metadata["text"],
                    "document_id": metadata["document_id"],
                    "chunk_index": metadata.get("chunk_index", 0),
                    "score": float(dist),
                    "metadata": {
                        k: v
                        for k, v in metadata.items()
                        if k not in ["text", "document_id", "chunk_index"]
                    },
                }
            )

            if len(results) >= top_k:
                break

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

        Note: FAISS doesn't support efficient deletion, so we need to rebuild the index.

        Args:
            document_id: Document identifier to delete

        Returns:
            True if document was deleted, False if not found
        """
        if document_id not in self.docstore:
            return False

        # Filter out chunks from this document
        new_metadata = [m for m in self.metadata if m.get("document_id") != document_id]

        if len(new_metadata) == len(self.metadata):
            return False

        # Rebuild index with remaining chunks
        self.metadata = []
        self.index = faiss.IndexFlatL2(self.embedding_dim)

        # Re-add all chunks except from deleted document
        texts_by_doc: Dict[str, List[Tuple[str, Dict]]] = {}
        for meta in new_metadata:
            doc_id = meta["document_id"]
            if doc_id not in texts_by_doc:
                texts_by_doc[doc_id] = []
            texts_by_doc[doc_id].append((meta["text"], meta))

        # Re-add documents
        for doc_id, chunks in texts_by_doc.items():
            texts = [c[0] for c in chunks]
            metas = [c[1] for c in chunks]
            self.add_documents(doc_id, texts, metas)

        # Remove from docstore
        del self.docstore[document_id]

        self._save_index()
        return True

    def list_documents(self) -> List[Dict[str, Any]]:
        """List all documents in the vector store.

        Returns:
            List of document information
        """
        return [
            {"document_id": doc_id, **info} for doc_id, info in self.docstore.items()
        ]

    def get_total_chunks(self) -> int:
        """Get total number of chunks in the index.

        Returns:
            Total chunk count
        """
        return self.index.ntotal if self.index else 0
