"""Document upload and management endpoints."""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import List

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse

from ..config import settings
from ..models.request import UploadDocumentResponse
from ..models.response import DocumentMetadata
from ..services.pdf_processor import PDFProcessor
from ..services.vector_store import VectorStoreService

router = APIRouter(prefix="/api/documents", tags=["documents"])

# Global instances (will be injected via dependency injection in main.py)
pdf_processor: PDFProcessor = None
vector_store: VectorStoreService = None


def set_dependencies(pdf_proc: PDFProcessor, vec_store: VectorStoreService) -> None:
    """Set service dependencies.

    Args:
        pdf_proc: PDF processor instance
        vec_store: Vector store instance
    """
    global pdf_processor, vector_store
    pdf_processor = pdf_proc
    vector_store = vec_store


@router.post("/upload", response_model=UploadDocumentResponse)
async def upload_document(file: UploadFile = File(...)) -> UploadDocumentResponse:
    """Upload a PDF document for processing.

    Args:
        file: PDF file to upload

    Returns:
        Upload response with document metadata
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are supported",
        )

    # Save file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_path = Path(temp_file.name)

        # Write uploaded file
        async with aiofiles.open(temp_path, "wb") as f:
            content = await file.read()
            await f.write(content)

    try:
        # Generate document ID
        document_id = PDFProcessor.generate_document_id(temp_path)

        # Create PDF storage directory if it doesn't exist
        pdf_storage = Path(settings.pdf_storage_path)
        pdf_storage.mkdir(parents=True, exist_ok=True)

        # Store PDF permanently
        stored_pdf_path = pdf_storage / f"{document_id}.pdf"
        shutil.copy(temp_path, stored_pdf_path)

        # Process PDF
        try:
            metadata, chunks = await pdf_processor.process_pdf(temp_path)
        except Exception as e:
            print(f"Error processing PDF: {e}")
            import traceback
            traceback.print_exc()
            raise

        # Add to vector store
        texts = [chunk.text for chunk in chunks]
        chunk_metadata = [
            {
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                **chunk.metadata,
            }
            for chunk in chunks
        ]

        vector_store.add_documents(document_id, texts, chunk_metadata)

        # Get file size
        file_size = os.path.getsize(temp_path)

        return UploadDocumentResponse(
            document_id=document_id,
            filename=file.filename,
            page_count=int(metadata.get("page_count", 0)),
            size_bytes=file_size,
            status="processed",
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing PDF: {str(e)}",
        )

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("", response_model=List[DocumentMetadata])
async def list_documents() -> List[DocumentMetadata]:
    """List all uploaded documents.

    Returns:
        List of document metadata
    """
    documents = vector_store.list_documents()

    return [
        DocumentMetadata(
            document_id=doc["document_id"],
            filename=doc.get("metadata", {}).get("title", "Unknown"),
            title=doc.get("metadata", {}).get("title"),
            authors=None,  # TODO: Extract authors
            abstract=None,  # TODO: Extract abstract
            page_count=0,  # TODO: Store page count
            size_bytes=0,  # TODO: Store file size
            upload_date=datetime.utcnow(),  # TODO: Store actual upload date
            processing_status="completed",
        )
        for doc in documents
    ]


@router.get("/{document_id}", response_model=DocumentMetadata)
async def get_document(document_id: str) -> DocumentMetadata:
    """Get metadata for a specific document.

    Args:
        document_id: Document identifier

    Returns:
        Document metadata
    """
    doc_info = vector_store.get_document_info(document_id)

    if not doc_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return DocumentMetadata(
        document_id=document_id,
        filename=doc_info.get("metadata", {}).get("title", "Unknown"),
        title=doc_info.get("metadata", {}).get("title"),
        authors=None,
        abstract=None,
        page_count=0,
        size_bytes=0,
        upload_date=datetime.utcnow(),
        processing_status="completed",
    )


@router.get("/{document_id}/pdf")
async def serve_pdf(document_id: str) -> FileResponse:
    """Serve the PDF file for a document.

    Args:
        document_id: Document identifier

    Returns:
        PDF file response
    """
    pdf_storage = Path(settings.pdf_storage_path)
    pdf_path = pdf_storage / f"{document_id}.pdf"

    if not pdf_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="PDF file not found",
        )

    return FileResponse(
        path=pdf_path,
        media_type="application/pdf",
        filename=f"{document_id}.pdf",
    )


@router.delete("/{document_id}")
async def delete_document(document_id: str) -> dict:
    """Delete a document from the system.

    Args:
        document_id: Document identifier

    Returns:
        Success message
    """
    success = vector_store.delete_document(document_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    # Also delete the stored PDF file
    pdf_storage = Path(settings.pdf_storage_path)
    pdf_path = pdf_storage / f"{document_id}.pdf"
    if pdf_path.exists():
        pdf_path.unlink()

    return {"message": "Document deleted successfully", "document_id": document_id}
