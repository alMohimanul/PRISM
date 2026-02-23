#!/usr/bin/env python3
"""Re-index existing PDFs with the new zvec + semantic chunking pipeline."""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "apps/api/src"))

from services.pdf_processor import PDFProcessor
from services.vector_store import VectorStoreService
from config import settings


async def reindex_documents():
    """Re-index all PDFs in the data/pdfs directory."""

    print("🚀 Starting document re-indexing with semantic chunking...")

    # Initialize services
    print("Initializing services...")
    pdf_processor = PDFProcessor(
        chunk_size=512,  # tokens
        chunk_overlap=128,
        use_semantic_chunking=True
    )

    vector_store = VectorStoreService(
        index_path=settings.vector_index_path,
        embedding_model=settings.embedding_model,
        enable_reranking=False  # Disable for faster indexing
    )

    # Find all PDFs - check both locations
    pdf_dir = Path(settings.pdf_storage_path)
    if not pdf_dir.exists():
        # Try parent directory's data/pdfs
        pdf_dir = Path(__file__).parent.parent / "data" / "pdfs"

    pdfs = list(pdf_dir.glob("*.pdf"))

    if not pdfs:
        print("❌ No PDFs found in", pdf_dir)
        return

    print(f"\n📚 Found {len(pdfs)} PDF(s) to process")

    # Process each PDF
    for i, pdf_path in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}] Processing: {pdf_path.name}")

        try:
            # Extract document ID from filename
            document_id = pdf_path.stem

            # Process PDF with semantic chunking
            print("  - Extracting text and metadata...")
            metadata, chunks = await pdf_processor.process_pdf(pdf_path)

            print(f"  - Created {len(chunks)} semantic chunks")
            print(f"  - Title: {metadata.get('title', 'Unknown')}")
            print(f"  - Authors: {', '.join(metadata.get('authors', [])[:3])}")

            # Prepare chunk data for vector store
            texts = [chunk.text for chunk in chunks]
            chunk_metadata = [chunk.metadata for chunk in chunks]

            # Add to vector store
            print("  - Generating embeddings and storing in zvec...")
            vector_store.add_documents(document_id, texts, chunk_metadata)

            print(f"  ✅ Successfully indexed with {len(chunks)} chunks")

        except Exception as e:
            print(f"  ❌ Error processing {pdf_path.name}: {e}")
            import traceback
            traceback.print_exc()
            continue

    # Summary
    total_chunks = vector_store.get_total_chunks()
    total_docs = len(vector_store.list_documents())

    print(f"\n{'='*60}")
    print(f"✨ Re-indexing complete!")
    print(f"📊 Total documents: {total_docs}")
    print(f"📦 Total chunks: {total_chunks}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    asyncio.run(reindex_documents())
