"""Advanced semantic chunking for academic papers."""

import asyncio
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import fitz  # PyMuPDF


@dataclass
class SemanticChunk:
    """Represents a semantically meaningful chunk from an academic paper."""

    text: str
    page_number: int
    chunk_index: int
    section: str  # e.g., "Introduction", "Methods"
    section_type: str  # e.g., "introduction", "methods", "results"
    semantic_density: float  # 0-1 score for information density
    contains_citation: bool
    contains_equation: bool
    contains_table_ref: bool
    contains_figure_ref: bool
    metadata: Dict[str, Any]


class AcademicPaperChunker:
    """Advanced chunking service for academic papers with semantic awareness."""

    # Standard academic paper sections (ordered)
    SECTION_HIERARCHY = {
        "abstract": 0,
        "introduction": 1,
        "related_work": 2,
        "background": 2,
        "literature_review": 2,
        "methodology": 3,
        "methods": 3,
        "approach": 3,
        "experiments": 4,
        "experimental_setup": 4,
        "results": 5,
        "evaluation": 5,
        "discussion": 6,
        "analysis": 6,
        "conclusion": 7,
        "future_work": 8,
        "references": 9,
        "appendix": 10,
    }

    def __init__(
        self,
        chunk_size: int = 512,  # Tokens (approx 4 chars per token = 2048 chars)
        chunk_overlap: int = 128,  # Tokens
        min_chunk_size: int = 100,  # Don't create chunks smaller than this
        respect_section_boundaries: bool = True,
    ):
        """Initialize the academic paper chunker.

        Args:
            chunk_size: Target chunk size in tokens (~4 chars per token)
            chunk_overlap: Overlap between chunks in tokens
            min_chunk_size: Minimum chunk size in tokens
            respect_section_boundaries: Don't split chunks across section boundaries
        """
        self.chunk_size = chunk_size * 4  # Convert to chars
        self.chunk_overlap = chunk_overlap * 4
        self.min_chunk_size = min_chunk_size * 4
        self.respect_section_boundaries = respect_section_boundaries

    async def process_pdf(
        self, file_path: str
    ) -> Tuple[Dict[str, Any], List[SemanticChunk]]:
        """Process a PDF and create semantic chunks.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (document metadata, list of semantic chunks)
        """
        # Run blocking PyMuPDF and parsing work in a thread to avoid
        # blocking the event loop for concurrent API requests.
        return await asyncio.to_thread(self._process_pdf_sync, file_path)

    def _process_pdf_sync(
        self, file_path: str
    ) -> Tuple[Dict[str, Any], List[SemanticChunk]]:
        """Synchronous PDF processing implementation for thread execution."""
        doc = fitz.open(file_path)
        try:
            # Extract document-level metadata
            metadata = self._extract_document_metadata(doc)

            # Extract structured text with layout information
            structured_pages = self._extract_structured_text(doc)

            # Detect document structure (sections, subsections)
            doc_structure = self._detect_document_structure(structured_pages)

            # Create semantic chunks
            chunks = self._create_semantic_chunks(
                structured_pages, doc_structure, metadata
            )

            return metadata, chunks
        finally:
            doc.close()

    def _extract_document_metadata(self, doc: fitz.Document) -> Dict[str, Any]:
        """Extract comprehensive metadata from PDF.

        Args:
            doc: PyMuPDF document

        Returns:
            Metadata dictionary
        """
        metadata = {}

        # PDF metadata
        pdf_meta = doc.metadata or {}
        metadata["title"] = pdf_meta.get("title", "")
        metadata["author"] = pdf_meta.get("author", "")
        metadata["subject"] = pdf_meta.get("subject", "")
        metadata["keywords"] = pdf_meta.get("keywords", "")
        metadata["creator"] = pdf_meta.get("creator", "")
        metadata["creation_date"] = pdf_meta.get("creationDate", "")
        metadata["page_count"] = len(doc)

        # Extract title and abstract from first pages if not in metadata
        first_pages_text = ""
        for page_num in range(min(3, len(doc))):
            first_pages_text += doc[page_num].get_text() + "\n"

        if not metadata["title"]:
            metadata["title"] = self._extract_title(first_pages_text)

        metadata["abstract"] = self._extract_abstract(first_pages_text)
        metadata["authors"] = self._extract_authors(first_pages_text)
        metadata["year"] = self._extract_publication_year(first_pages_text)
        metadata["venue"] = self._extract_venue(first_pages_text)

        return metadata

    def _extract_title(self, text: str) -> str:
        """Extract title from document text."""
        lines = text.split("\n")[:15]

        # Find the longest substantive line (likely title)
        title = ""
        max_length = 0

        for line in lines:
            line = line.strip()
            # Skip very short lines and page numbers
            if (
                len(line) > max_length
                and 20 < len(line) < 250
                and not re.match(r"^\d+$", line)
                and not line.lower().startswith(("abstract", "keywords"))
            ):
                title = line
                max_length = len(line)

        return title

    def _extract_abstract(self, text: str) -> str:
        """Extract abstract from document text."""
        # Look for abstract section with improved patterns
        patterns = [
            r"(?:^|\n)\s*Abstract\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:Keywords|Introduction|\d+\s+Introduction|1\.?\s+Introduction))",
            r"(?:^|\n)\s*ABSTRACT\s*[:\-]?\s*\n(.*?)(?=\n\s*(?:KEYWORDS|INTRODUCTION|\d+\s+INTRODUCTION))",
            r"—\s*Abstract\s*[:\-]?\s*(.*?)(?=\n\s*(?:Index Terms|Keywords|Introduction))",
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:5000], re.IGNORECASE | re.DOTALL)
            if match:
                abstract = match.group(1).strip()
                # Clean up
                abstract = re.sub(r"\s+", " ", abstract)
                return abstract[:1000]

        return ""

    def _extract_authors(self, text: str) -> List[str]:
        """Extract author names from document text."""
        authors = []

        # Look for common author patterns
        # Pattern 1: Names before abstract
        lines = text.split("\n")[:30]
        for i, line in enumerate(lines):
            line = line.strip()
            # Look for lines with proper names (capitalized words)
            if re.match(r"^([A-Z][a-z]+\s+)+[A-Z][a-z]+", line):
                # Check if it's likely an author (before abstract, not too long)
                if 10 < len(line) < 100 and "abstract" not in line.lower():
                    # Split by common separators
                    names = re.split(r",\s*(?:and\s+)?|\s+and\s+", line)
                    authors.extend([n.strip() for n in names if n.strip()])

        # Deduplicate while preserving order
        seen = set()
        unique_authors = []
        for author in authors:
            if author not in seen and len(author) > 3:
                seen.add(author)
                unique_authors.append(author)

        return unique_authors[:10]  # Limit to 10 authors

    def _extract_publication_year(self, text: str) -> Optional[int]:
        """Extract publication year from document text."""
        # Look for 4-digit years (1900-2099) in first page
        years = re.findall(r"\b(19\d{2}|20\d{2})\b", text[:2000])
        if years:
            # Return most recent year found (likely publication year)
            return max(int(year) for year in years)
        return None

    def _extract_venue(self, text: str) -> str:
        """Extract publication venue (conference/journal) from text."""
        # Look for common venue patterns
        patterns = [
            r"(?:Proceedings of|Published in|Appeared in)\s+([^\n]{10,100})",
            r"((?:Conference on|Journal of|Transactions on)[^\n]{10,100})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text[:3000], re.IGNORECASE)
            if match:
                venue = match.group(1).strip()
                # Clean up
                venue = re.sub(r"\s+", " ", venue)
                return venue[:200]

        return ""

    def _extract_structured_text(
        self, doc: fitz.Document
    ) -> List[Dict[str, Any]]:
        """Extract text with structural information (fonts, positions).

        Args:
            doc: PyMuPDF document

        Returns:
            List of page dictionaries with structured text
        """
        structured_pages = []

        for page_num in range(len(doc)):
            page = doc[page_num]

            # Get text with detailed formatting
            blocks = page.get_text("dict")["blocks"]

            page_data = {
                "page_number": page_num + 1,
                "blocks": [],
                "full_text": "",
            }

            for block in blocks:
                if block.get("type") == 0:  # Text block
                    for line in block.get("lines", []):
                        for span in line.get("spans", []):
                            text = span.get("text", "").strip()
                            if text:
                                page_data["blocks"].append({
                                    "text": text,
                                    "font_size": span.get("size", 0),
                                    "font_name": span.get("font", ""),
                                    "flags": span.get("flags", 0),  # Bold, italic, etc.
                                    "color": span.get("color", 0),
                                })
                                page_data["full_text"] += text + " "

            page_data["full_text"] = page_data["full_text"].strip()
            structured_pages.append(page_data)

        return structured_pages

    def _detect_document_structure(
        self, structured_pages: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Detect sections and subsections based on text formatting.

        Args:
            structured_pages: Pages with structured text

        Returns:
            List of section markers with positions
        """
        sections = []

        # Collect all blocks with font information
        all_blocks = []
        for page in structured_pages:
            for block in page["blocks"]:
                all_blocks.append({
                    **block,
                    "page_number": page["page_number"],
                })

        # Find average font size to detect headers
        font_sizes = [b["font_size"] for b in all_blocks if b["font_size"] > 0]
        avg_font_size = sum(font_sizes) / len(font_sizes) if font_sizes else 11

        # Detect section headers
        for i, block in enumerate(all_blocks):
            text = block["text"].strip()
            font_size = block["font_size"]

            # Check if this looks like a section header
            is_header = False

            # Method 1: Larger font size
            if font_size > avg_font_size * 1.2:
                is_header = True

            # Method 2: Bold text with section keywords
            is_bold = bool(block["flags"] & 16)  # Flag for bold
            if is_bold and self._is_section_keyword(text):
                is_header = True

            # Method 3: Numbered sections (1. Introduction, etc.)
            if re.match(r"^\d+\.?\s+[A-Z]", text):
                is_header = True

            if is_header and 3 < len(text) < 100:
                section_type = self._classify_section(text)
                sections.append({
                    "text": text,
                    "type": section_type,
                    "page": block["page_number"],
                    "block_index": i,
                    "font_size": font_size,
                })

        return sections

    def _is_section_keyword(self, text: str) -> bool:
        """Check if text contains section keywords."""
        text_lower = text.lower().strip()

        # Remove numbers and punctuation
        text_clean = re.sub(r"^\d+\.?\s*", "", text_lower).strip()

        return text_clean in self.SECTION_HIERARCHY

    def _classify_section(self, text: str) -> str:
        """Classify section type from header text."""
        text_lower = text.lower().strip()

        # Remove numbering
        text_clean = re.sub(r"^\d+\.?\s*", "", text_lower).strip()

        # Direct match
        if text_clean in self.SECTION_HIERARCHY:
            return text_clean

        # Partial matches
        for section_key in self.SECTION_HIERARCHY:
            if section_key in text_clean or text_clean in section_key:
                return section_key

        # Check for common variations
        if "intro" in text_clean:
            return "introduction"
        if "method" in text_clean or "approach" in text_clean:
            return "methodology"
        if "result" in text_clean or "finding" in text_clean:
            return "results"
        if "discuss" in text_clean:
            return "discussion"
        if "conclusion" in text_clean or "concluding" in text_clean:
            return "conclusion"
        if "related" in text_clean or "prior" in text_clean:
            return "related_work"
        if "experiment" in text_clean:
            return "experiments"
        if "reference" in text_clean or "bibliograph" in text_clean:
            return "references"

        return "body"

    def _create_semantic_chunks(
        self,
        structured_pages: List[Dict[str, Any]],
        sections: List[Dict[str, Any]],
        metadata: Dict[str, Any],
    ) -> List[SemanticChunk]:
        """Create semantically-aware chunks.

        Args:
            structured_pages: Structured page data
            sections: Detected sections
            metadata: Document metadata

        Returns:
            List of semantic chunks
        """
        chunks = []
        chunk_index = 0

        # Combine all text with section markers
        full_text = ""
        page_positions = []  # Track char position -> page mapping
        section_positions = []  # Track char position -> section mapping

        current_pos = 0
        for page in structured_pages:
            page_text = page["full_text"]
            page_start = current_pos
            page_end = current_pos + len(page_text)

            page_positions.append({
                "start": page_start,
                "end": page_end,
                "page": page["page_number"],
            })

            full_text += page_text + "\n\n"
            current_pos = len(full_text)

        # Map sections to character positions
        current_section = {"type": "introduction", "text": "Introduction"}
        current_section_start = 0

        for i, section in enumerate(sections):
            # Find section text position in full_text
            section_pos = full_text.find(section["text"], current_section_start)

            if section_pos != -1:
                # Save previous section range
                if current_section_start < section_pos:
                    section_positions.append({
                        "start": current_section_start,
                        "end": section_pos,
                        "type": current_section["type"],
                        "text": current_section["text"],
                    })

                current_section = section
                current_section_start = section_pos

        # Add final section
        section_positions.append({
            "start": current_section_start,
            "end": len(full_text),
            "type": current_section.get("type", "body"),
            "text": current_section.get("text", "Body"),
        })

        # Split into sentences for chunking
        sentences = self._split_into_sentences(full_text)

        # Build chunks
        current_chunk_text = ""
        current_chunk_start = 0
        sentence_positions = []

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence or len(sentence) < 10:
                continue

            # Find sentence position
            sent_pos = full_text.find(sentence, current_chunk_start)
            if sent_pos == -1:
                continue

            # Check if adding sentence exceeds chunk size
            potential_chunk = (
                current_chunk_text + " " + sentence
                if current_chunk_text
                else sentence
            )

            # Get current section
            current_section_info = self._get_position_section(
                sent_pos, section_positions
            )

            # Check if we should create a chunk
            should_chunk = False

            if len(potential_chunk) > self.chunk_size:
                should_chunk = True
            elif self.respect_section_boundaries:
                # Check if next sentence crosses section boundary
                next_sent_pos = sent_pos + len(sentence)
                next_section = self._get_position_section(
                    next_sent_pos, section_positions
                )
                if next_section["type"] != current_section_info["type"]:
                    should_chunk = True

            if should_chunk and len(current_chunk_text) >= self.min_chunk_size:
                # Create chunk
                page_num = self._get_position_page(
                    current_chunk_start, page_positions
                )

                chunk = SemanticChunk(
                    text=current_chunk_text.strip(),
                    page_number=page_num,
                    chunk_index=chunk_index,
                    section=current_section_info["text"],
                    section_type=current_section_info["type"],
                    semantic_density=self._calculate_semantic_density(
                        current_chunk_text
                    ),
                    contains_citation=self._contains_citations(current_chunk_text),
                    contains_equation=self._contains_equations(current_chunk_text),
                    contains_table_ref=self._contains_table_ref(current_chunk_text),
                    contains_figure_ref=self._contains_figure_ref(
                        current_chunk_text
                    ),
                    metadata={
                        "title": metadata.get("title", ""),
                        "authors": metadata.get("authors", []),
                        "year": metadata.get("year"),
                        "abstract": metadata.get("abstract", ""),
                    },
                )
                chunks.append(chunk)
                chunk_index += 1

                # Start new chunk with overlap
                if self.chunk_overlap > 0 and sentence_positions:
                    overlap_sentences = self._get_overlap_sentences(
                        sentence_positions, self.chunk_overlap
                    )
                    current_chunk_text = " ".join(overlap_sentences) + " " + sentence
                    sentence_positions = overlap_sentences
                else:
                    current_chunk_text = sentence
                    sentence_positions = [sentence]

                current_chunk_start = sent_pos
            else:
                # Add to current chunk
                current_chunk_text = potential_chunk
                sentence_positions.append(sentence)

        # Final chunk
        if len(current_chunk_text.strip()) >= self.min_chunk_size:
            page_num = self._get_position_page(current_chunk_start, page_positions)
            current_section_info = self._get_position_section(
                current_chunk_start, section_positions
            )

            chunk = SemanticChunk(
                text=current_chunk_text.strip(),
                page_number=page_num,
                chunk_index=chunk_index,
                section=current_section_info["text"],
                section_type=current_section_info["type"],
                semantic_density=self._calculate_semantic_density(
                    current_chunk_text
                ),
                contains_citation=self._contains_citations(current_chunk_text),
                contains_equation=self._contains_equations(current_chunk_text),
                contains_table_ref=self._contains_table_ref(current_chunk_text),
                contains_figure_ref=self._contains_figure_ref(current_chunk_text),
                metadata={
                    "title": metadata.get("title", ""),
                    "authors": metadata.get("authors", []),
                    "year": metadata.get("year"),
                    "abstract": metadata.get("abstract", ""),
                },
            )
            chunks.append(chunk)

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Normalize whitespace
        text = re.sub(r"[ \t]+", " ", text)

        # Split on sentence boundaries, handling abbreviations
        sentences = re.split(
            r"(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<![A-Z]\.)(?<=\.|\?|!)\s+(?=[A-Z\"])",
            text,
        )

        return [s.strip() for s in sentences if s.strip()]

    def _get_position_page(
        self, pos: int, page_positions: List[Dict[str, Any]]
    ) -> int:
        """Get page number for character position."""
        for page_info in page_positions:
            if page_info["start"] <= pos < page_info["end"]:
                return page_info["page"]
        return page_positions[0]["page"] if page_positions else 1

    def _get_position_section(
        self, pos: int, section_positions: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """Get section info for character position."""
        for section_info in reversed(section_positions):
            if section_info["start"] <= pos:
                return section_info

        return {"type": "body", "text": "Body"}

    def _get_overlap_sentences(
        self, sentences: List[str], target_length: int
    ) -> List[str]:
        """Get sentences for overlap."""
        overlap = []
        current_length = 0

        for sentence in reversed(sentences):
            if current_length + len(sentence) <= target_length:
                overlap.insert(0, sentence)
                current_length += len(sentence)
            else:
                break

        return overlap

    def _calculate_semantic_density(self, text: str) -> float:
        """Calculate information density score (0-1).

        High density = contains technical terms, citations, numbers
        Low density = generic text, common words
        """
        score = 0.0

        # Check for technical indicators
        if self._contains_citations(text):
            score += 0.3
        if self._contains_equations(text):
            score += 0.2
        if self._contains_numbers(text):
            score += 0.1
        if self._contains_table_ref(text):
            score += 0.15
        if self._contains_figure_ref(text):
            score += 0.15

        # Check for technical terms (words with capitals in middle)
        technical_terms = re.findall(r"\b[A-Z][a-z]*[A-Z]\w+\b", text)
        if technical_terms:
            score += min(0.1, len(technical_terms) * 0.02)

        return min(1.0, score)

    def _contains_citations(self, text: str) -> bool:
        """Check if text contains citations."""
        patterns = [
            r"\[\d+\]",  # [1], [2]
            r"\[[\d,\s]+\]",  # [1, 2, 3]
            r"\([A-Z][a-z]+\s+et\s+al\.,?\s+\d{4}\)",  # (Smith et al., 2020)
            r"\([A-Z][a-z]+\s+and\s+[A-Z][a-z]+,?\s+\d{4}\)",  # (Smith and Jones, 2020)
        ]
        return any(re.search(p, text) for p in patterns)

    def _contains_equations(self, text: str) -> bool:
        """Check if text contains equations or mathematical notation."""
        patterns = [
            r"[∑∏∫∂∇α-ωΑ-Ω]",  # Mathematical symbols
            r"\$.*?\$",  # LaTeX inline
            r"\\[a-zA-Z]+\{",  # LaTeX commands
        ]
        return any(re.search(p, text) for p in patterns)

    def _contains_numbers(self, text: str) -> bool:
        """Check if text contains numerical data."""
        return bool(re.search(r"\b\d+\.?\d*%?\b", text))

    def _contains_table_ref(self, text: str) -> bool:
        """Check if text references tables."""
        return bool(re.search(r"Table\s+\d+|TABLE\s+\d+", text, re.IGNORECASE))

    def _contains_figure_ref(self, text: str) -> bool:
        """Check if text references figures."""
        return bool(
            re.search(r"Fig(?:ure)?\.?\s+\d+|FIGURE\s+\d+", text, re.IGNORECASE)
        )
