"""Main FastAPI application for PRISM Research Assistant."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents.literature_reviewer import LiteratureReviewerAgent
from .config import settings
from .routes import chat, documents, sessions
from .services.pdf_processor import PDFProcessor
from .services.session_manager import SessionManager
from .services.vector_store import VectorStoreService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Global service instances
pdf_processor: PDFProcessor = None
vector_store: VectorStoreService = None
session_manager: SessionManager = None
literature_agent: LiteratureReviewerAgent = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager for startup and shutdown.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    logger.info("Starting PRISM Research Assistant API")

    # Initialize services
    global pdf_processor, vector_store, session_manager, literature_agent

    logger.info("Initializing PDF processor...")
    pdf_processor = PDFProcessor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    logger.info("Initializing vector store...")
    vector_store = VectorStoreService(
        index_path=settings.faiss_index_path,
        embedding_model=settings.embedding_model,
    )

    logger.info("Initializing session manager...")
    session_manager = SessionManager(
        redis_url=settings.redis_url,
        session_expire_hours=settings.session_expire_hours,
    )
    await session_manager.connect()

    logger.info("Initializing Literature Reviewer agent...")
    literature_agent = LiteratureReviewerAgent(
        vector_store=vector_store,
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
    )

    # Inject dependencies into route modules
    documents.set_dependencies(pdf_processor, vector_store)
    sessions.set_dependencies(session_manager)
    chat.set_dependencies(literature_agent, session_manager)

    logger.info("PRISM API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PRISM Research Assistant API")
    await session_manager.disconnect()


# Create FastAPI application
app = FastAPI(
    title="PRISM Research Assistant API",
    description="Personal Research Intelligence and Synthesis Manager",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(documents.router)
app.include_router(sessions.router)
app.include_router(chat.router)


@app.get("/")
async def root() -> dict:
    """Root endpoint.

    Returns:
        Welcome message
    """
    return {
        "message": "PRISM Research Assistant API",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint.

    Returns:
        Health status
    """
    return {
        "status": "healthy",
        "services": {
            "vector_store": vector_store.get_total_chunks() if vector_store else 0,
            "session_manager": "connected" if session_manager else "disconnected",
        },
    }
