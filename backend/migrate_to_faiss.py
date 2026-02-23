"""Migration script to convert from zvec to FAISS vector store.

This script:
1. Backs up the existing zvec index
2. Reads all documents from the PDF storage
3. Re-processes and re-indexes them in the new FAISS index

Usage:
    python migrate_to_faiss.py
"""

import asyncio
import json
import shutil
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "apps" / "api" / "src"))

from config import settings
from services.pdf_processor import PDFProcessor
from services.vector_store import VectorStoreService


async def migrate_to_faiss():
    """Migrate existing documents from zvec to FAISS."""
    print("=" * 60)
    print("PRISM: zvec to FAISS Migration Tool")
    print("=" * 60)
    print()

    # Paths
    old_index_path = Path("./data/zvec_index")
    old_docstore_file = old_index_path / "docstore.json"
    pdf_storage_path = Path(settings.pdf_storage_path)
    backup_path = Path("./data/zvec_index_backup")

    # Check if old index exists
    if not old_docstore_file.exists():
        print("⚠️  No zvec index found at:", old_index_path)
        print("   Starting fresh with FAISS index.")
        print()
        return

    # Backup old index
    print("📦 Backing up zvec index...")
    if backup_path.exists():
        print(f"   Removing old backup at {backup_path}")
        shutil.rmtree(backup_path)
    shutil.copytree(old_index_path, backup_path)
    print(f"✓  Backed up to: {backup_path}")
    print()

    # Load old docstore
    print("📖 Loading old docstore...")
    with open(old_docstore_file, "r") as f:
        old_docstore = json.load(f)

    document_count = len(old_docstore)
    print(f"✓  Found {document_count} documents")
    print()

    if document_count == 0:
        print("   No documents to migrate. Exiting.")
        return

    # Initialize new FAISS vector store
    print("🔧 Initializing FAISS vector store...")
    vector_store = VectorStoreService(
        index_path=settings.vector_index_path,
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model if settings.enable_reranking else None,
        enable_reranking=settings.enable_reranking,
    )
    print(f"✓  FAISS index initialized at: {settings.vector_index_path}")
    print()

    # Initialize PDF processor
    print("🔧 Initializing PDF processor...")
    pdf_processor = PDFProcessor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    print("✓  PDF processor ready")
    print()

    # Process each document
    print("📄 Re-indexing documents...")
    print("-" * 60)

    success_count = 0
    failed_docs = []

    for idx, (doc_id, doc_info) in enumerate(old_docstore.items(), 1):
        doc_title = doc_info.get("metadata", {}).get("title", "Unknown")
        print(f"\n[{idx}/{document_count}] Processing: {doc_title}")
        print(f"    Document ID: {doc_id}")

        # Find PDF file
        pdf_file = pdf_storage_path / f"{doc_id}.pdf"

        if not pdf_file.exists():
            print(f"    ❌ PDF file not found: {pdf_file}")
            failed_docs.append((doc_id, doc_title, "PDF file not found"))
            continue

        try:
            # Process PDF
            print(f"    📖 Processing PDF...")
            metadata, chunks = await pdf_processor.process_pdf(pdf_file)

            # Extract text and metadata
            texts = [chunk.text for chunk in chunks]
            chunk_metadata = [
                {
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    **chunk.metadata,
                }
                for chunk in chunks
            ]

            # Add to FAISS
            print(f"    🔍 Adding {len(texts)} chunks to FAISS...")
            vector_store.add_documents(doc_id, texts, chunk_metadata)

            print(f"    ✓  Successfully indexed {len(texts)} chunks")
            success_count += 1

        except Exception as e:
            print(f"    ❌ Error processing document: {e}")
            failed_docs.append((doc_id, doc_title, str(e)))
            continue

    # Summary
    print()
    print("=" * 60)
    print("Migration Summary")
    print("=" * 60)
    print(f"Total documents: {document_count}")
    print(f"Successfully migrated: {success_count}")
    print(f"Failed: {len(failed_docs)}")
    print()

    if failed_docs:
        print("Failed documents:")
        for doc_id, title, error in failed_docs:
            print(f"  - {title} ({doc_id[:8]}...)")
            print(f"    Error: {error}")
        print()

    # Final stats
    total_chunks = vector_store.get_total_chunks()
    print(f"Total chunks in FAISS index: {total_chunks}")
    print()

    print("✓  Migration complete!")
    print()
    print("Next steps:")
    print("  1. Verify the migration by starting the backend server")
    print("  2. Test document search functionality")
    print("  3. If everything works, you can safely delete the backup:")
    print(f"     rm -rf {backup_path}")
    print()


if __name__ == "__main__":
    asyncio.run(migrate_to_faiss())
