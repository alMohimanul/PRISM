"""PDF processing service with PyMuPDF."""

import hashlib
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

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
        """Create text chunks from page texts with semantic boundaries.

        Args:
            page_texts: List of (page_number, text) tuples
            metadata: Document metadata

        Returns:
            List of PDFChunk objects
        """
        chunks = []
        chunk_index = 0

        # Combine all pages into one text with page markers
        full_text = ""
        page_map = []  # Track which character belongs to which page

        for page_num, page_text in page_texts:
            start_idx = len(full_text)
            full_text += page_text + "\n\n"
            end_idx = len(full_text)
            page_map.append((start_idx, end_idx, page_num))

        # Detect sections in the document
        sections = self._detect_sections(full_text)

        # Split into sentences
        sentences = self._split_into_sentences(full_text)

        current_chunk = ""
        current_chunk_start = 0
        sentence_buffer = []  # Keep track of sentences in current chunk

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue

            # Calculate potential new chunk size
            potential_chunk = current_chunk + " " + sentence if current_chunk else sentence

            # Check if adding this sentence exceeds chunk size
            if len(potential_chunk) > self.chunk_size and current_chunk:
                # Find which page this chunk starts on
                page_num = self._get_page_for_position(current_chunk_start, page_map)

                # Detect section context for this chunk
                section_info = self._get_section_context(current_chunk_start, sections)

                # Create chunk
                chunk = PDFChunk(
                    text=current_chunk.strip(),
                    page_number=page_num,
                    chunk_index=chunk_index,
                    metadata={
                        "title": metadata.get("title", ""),
                        "author": metadata.get("author", ""),
                        "section": section_info.get("section", ""),
                        "section_type": section_info.get("type", "body"),
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

                # Create overlap using complete sentences (not character-based)
                if self.chunk_overlap > 0 and sentence_buffer:
                    # Find sentences that fit within overlap size
                    overlap_sentences = self._get_overlap_sentences(
                        sentence_buffer, self.chunk_overlap
                    )
                    if overlap_sentences:
                        current_chunk = " ".join(overlap_sentences) + " " + sentence
                        current_chunk_start = full_text.find(overlap_sentences[0], current_chunk_start)
                        sentence_buffer = overlap_sentences + [sentence]
                    else:
                        current_chunk = sentence
                        current_chunk_start = full_text.find(sentence, current_chunk_start)
                        sentence_buffer = [sentence]
                else:
                    current_chunk = sentence
                    current_chunk_start = full_text.find(sentence, current_chunk_start)
                    sentence_buffer = [sentence]
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
                    current_chunk_start = full_text.find(sentence)
                sentence_buffer.append(sentence)

        # Save final chunk
        if current_chunk.strip():
            page_num = self._get_page_for_position(current_chunk_start, page_map)
            section_info = self._get_section_context(current_chunk_start, sections)

            chunk = PDFChunk(
                text=current_chunk.strip(),
                page_number=page_num,
                chunk_index=chunk_index,
                metadata={
                    "title": metadata.get("title", ""),
                    "author": metadata.get("author", ""),
                    "section": section_info.get("section", ""),
                    "section_type": section_info.get("type", "body"),
                },
            )
            chunks.append(chunk)

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences while preserving structure.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Normalize whitespace but preserve paragraph breaks
        text = re.sub(r"[ \t]+", " ", text)

        # Split on sentence boundaries
        # Improved regex to handle abbreviations and citations
        sentences = re.split(
            r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=[.!?])\s+(?=[A-Z])", text
        )

        return [s.strip() for s in sentences if s.strip()]

    def _detect_sections(self, text: str) -> List[Dict[str, Any]]:
        """Detect section headers, tables, and figures in the document.

        Args:
            text: Full document text

        Returns:
            List of dicts with section info: {position, title, type}
        """
        sections = []

        # Common section patterns in academic papers
        section_patterns = [
            (r"\n\s*ABSTRACT\s*\n", "abstract"),
            (r"\n\s*(?:1\.?\s+)?INTRODUCTION\s*\n", "introduction"),
            (r"\n\s*(?:\d+\.?\s+)?RELATED WORK\s*\n", "related_work"),
            (r"\n\s*(?:\d+\.?\s+)?BACKGROUND\s*\n", "background"),
            (r"\n\s*(?:\d+\.?\s+)?METHODOLOGY\s*\n", "methodology"),
            (r"\n\s*(?:\d+\.?\s+)?METHODS?\s*\n", "methods"),
            (r"\n\s*(?:\d+\.?\s+)?EXPERIMENTS?\s*\n", "experiments"),
            (r"\n\s*(?:\d+\.?\s+)?RESULTS?\s*\n", "results"),
            (r"\n\s*(?:\d+\.?\s+)?DISCUSSION\s*\n", "discussion"),
            (r"\n\s*(?:\d+\.?\s+)?CONCLUSION\s*\n", "conclusion"),
            (r"\n\s*(?:\d+\.?\s+)?REFERENCES\s*\n", "references"),
        ]

        for pattern, section_type in section_patterns:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                sections.append({
                    "position": match.start(),
                    "title": match.group().strip(),
                    "type": section_type,
                })

        # Detect tables
        table_patterns = [
            r"Table\s+\d+[:\.]?\s+[^\n]+",  # Table 1: Caption
            r"TABLE\s+\d+[:\.]?\s+[^\n]+",  # TABLE 1: Caption
        ]

        for pattern in table_patterns:
            for match in re.finditer(pattern, text):
                sections.append({
                    "position": match.start(),
                    "title": match.group().strip(),
                    "type": "table",
                })

        # Detect figures
        figure_patterns = [
            r"Figure\s+\d+[:\.]?\s+[^\n]+",  # Figure 1: Caption
            r"Fig\.\s+\d+[:\.]?\s+[^\n]+",   # Fig. 1: Caption
            r"FIGURE\s+\d+[:\.]?\s+[^\n]+",  # FIGURE 1: Caption
        ]

        for pattern in figure_patterns:
            for match in re.finditer(pattern, text):
                sections.append({
                    "position": match.start(),
                    "title": match.group().strip(),
                    "type": "figure",
                })

        # Sort by position
        sections.sort(key=lambda x: x["position"])

        return sections

    def _get_section_context(
        self, position: int, sections: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Get the section context for a given text position.

        Args:
            position: Character position in text
            sections: List of detected sections

        Returns:
            Dict with section and type
        """
        current_section = {"section": "", "type": "body"}

        for section in sections:
            if section["position"] <= position:
                current_section = {
                    "section": section["title"],
                    "type": section["type"],
                }
            else:
                break

        return current_section

    def _get_page_for_position(
        self, position: int, page_map: List[Tuple[int, int, int]]
    ) -> int:
        """Get page number for a character position.

        Args:
            position: Character position in text
            page_map: List of (start, end, page_num) tuples

        Returns:
            Page number (1-indexed)
        """
        for start, end, page_num in page_map:
            if start <= position < end:
                return page_num

        # Default to first page if not found
        return page_map[0][2] if page_map else 1

    def _get_overlap_sentences(
        self, sentence_buffer: List[str], overlap_size: int
    ) -> List[str]:
        """Get sentences that fit within the overlap size.

        Args:
            sentence_buffer: List of recent sentences
            overlap_size: Target overlap size in characters

        Returns:
            List of sentences for overlap
        """
        overlap_sentences = []
        current_size = 0

        # Work backwards from the end of the buffer
        for sentence in reversed(sentence_buffer):
            sentence_len = len(sentence)
            if current_size + sentence_len <= overlap_size:
                overlap_sentences.insert(0, sentence)
                current_size += sentence_len
            else:
                break

        return overlap_sentences

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
