"""PDF processing service with PyMuPDF."""

import hashlib
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF


class PDFChunk:
    """Represents a chunk of text from a PDF document."""

    def __init__(
        self,
        text: str,
        page_number: int,
        chunk_index: int,
        metadata: Optional[Dict[str, str]] = None,
    ):
        self.text = text
        self.page_number = page_number
        self.chunk_index = chunk_index
        self.metadata = metadata or {}


class PDFProcessor:
    """Service for processing PDF documents."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize PDF processor.

        Args:
            chunk_size: Maximum size of text chunks
            chunk_overlap: Overlap between consecutive chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    async def process_pdf(self, file_path: Path) -> Tuple[Dict[str, str], List[PDFChunk]]:
        """Process a PDF file and extract metadata and chunks.

        Args:
            file_path: Path to the PDF file

        Returns:
            Tuple of (metadata dict, list of PDFChunk objects)
        """
        doc = fitz.open(file_path)

        # Extract metadata
        metadata = self._extract_metadata(doc)

        # Extract text from all pages
        full_text = ""
        page_texts = []

        for page_num in range(len(doc)):
            page = doc[page_num]
            page_text = page.get_text()
            page_texts.append((page_num + 1, page_text))
            full_text += page_text + "\n"

        # Extract abstract and title if not in metadata
        if not metadata.get("title"):
            metadata["title"] = self._extract_title(full_text)

        if not metadata.get("abstract"):
            metadata["abstract"] = self._extract_abstract(full_text)

        # Create chunks
        chunks = self._create_chunks(page_texts, metadata)

        doc.close()

        return metadata, chunks

    def _extract_metadata(self, doc: fitz.Document) -> Dict[str, str]:
        """Extract metadata from PDF document.

        Args:
            doc: PyMuPDF document object

        Returns:
            Dictionary with metadata fields
        """
        metadata = {}

        # Extract from PDF metadata
        pdf_metadata = doc.metadata or {}

        metadata["title"] = pdf_metadata.get("title", "")
        metadata["author"] = pdf_metadata.get("author", "")
        metadata["subject"] = pdf_metadata.get("subject", "")
        metadata["creator"] = pdf_metadata.get("creator", "")
        metadata["producer"] = pdf_metadata.get("producer", "")
        metadata["creation_date"] = pdf_metadata.get("creationDate", "")
        metadata["page_count"] = str(len(doc))

        return metadata

    def _extract_title(self, text: str) -> str:
        """Attempt to extract title from document text.

        Args:
            text: Full document text

        Returns:
            Extracted title or empty string
        """
        # Get first few lines
        lines = text.split("\n")[:10]

        # Find the longest non-empty line (likely the title)
        title = ""
        max_length = 0

        for line in lines:
            line = line.strip()
            if len(line) > max_length and len(line) < 200:
                title = line
                max_length = len(line)

        return title

    def _extract_abstract(self, text: str) -> str:
        """Attempt to extract abstract from document text.

        Args:
            text: Full document text

        Returns:
            Extracted abstract or empty string
        """
        # Look for abstract section
        abstract_pattern = r"abstract\s*[:\-]?\s*(.*?)(?:\n\n|\n[A-Z]|introduction)"
        match = re.search(abstract_pattern, text[:3000], re.IGNORECASE | re.DOTALL)

        if match:
            abstract = match.group(1).strip()
            # Clean up the abstract
            abstract = re.sub(r"\s+", " ", abstract)
            return abstract[:500]  # Limit length

        return ""

    def _create_chunks(
        self, page_texts: List[Tuple[int, str]], metadata: Dict[str, str]
    ) -> List[PDFChunk]:
        """Create text chunks from page texts.

        Args:
            page_texts: List of (page_number, text) tuples
            metadata: Document metadata

        Returns:
            List of PDFChunk objects
        """
        chunks = []
        chunk_index = 0

        for page_num, page_text in page_texts:
            # Split page text into sentences (simple approach)
            sentences = self._split_into_sentences(page_text)

            current_chunk = ""
            for sentence in sentences:
                # Check if adding this sentence would exceed chunk size
                if len(current_chunk) + len(sentence) > self.chunk_size and current_chunk:
                    # Save current chunk
                    chunk = PDFChunk(
                        text=current_chunk.strip(),
                        page_number=page_num,
                        chunk_index=chunk_index,
                        metadata={
                            "title": metadata.get("title", ""),
                            "author": metadata.get("author", ""),
                        },
                    )
                    chunks.append(chunk)
                    chunk_index += 1

                    # Start new chunk with overlap
                    if self.chunk_overlap > 0:
                        # Keep last N characters for overlap
                        overlap_text = current_chunk[-self.chunk_overlap :]
                        current_chunk = overlap_text + " " + sentence
                    else:
                        current_chunk = sentence
                else:
                    current_chunk += " " + sentence

            # Save remaining text as chunk
            if current_chunk.strip():
                chunk = PDFChunk(
                    text=current_chunk.strip(),
                    page_number=page_num,
                    chunk_index=chunk_index,
                    metadata={
                        "title": metadata.get("title", ""),
                        "author": metadata.get("author", ""),
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with nltk)
        text = text.replace("\n", " ")
        sentences = re.split(r"(?<=[.!?])\s+", text)
        return [s.strip() for s in sentences if s.strip()]

    @staticmethod
    def generate_document_id(file_path: Path) -> str:
        """Generate a unique document ID based on file content.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash of file content
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()[:16]
