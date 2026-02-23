"""Main FastAPI application for PRISM Research Assistant."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .agents.literature_reviewer import LiteratureReviewerAgent
# from .agents.debate_arena import DebateArenaAgent  # Disabled
# from .agents.literature_review_generator import LiteratureReviewGenerator  # Replaced with Paper Comparator
from .agents.paper_comparator import PaperComparator
from .config import settings
from .routes import chat, documents, sessions, cache, paper_comparison  # debate and literature_review disabled
from .services.pdf_processor import PDFProcessor
from .services.session_manager import SessionManager
from .services.vector_store import VectorStoreService
from .services.llm_provider import MultiProviderLLMClient
from .services.llm_cache import LLMCache

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
llm_cache: LLMCache = None
llm_client: MultiProviderLLMClient = None
literature_agent: LiteratureReviewerAgent = None
# debate_agent: DebateArenaAgent = None  # Disabled
# review_generator: LiteratureReviewGenerator = None  # Replaced with Paper Comparator
paper_comparator: PaperComparator = None


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
    global pdf_processor, vector_store, session_manager, llm_cache, llm_client, literature_agent, paper_comparator

    logger.info("Initializing PDF processor...")
    pdf_processor = PDFProcessor(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )

    logger.info("Initializing vector store...")
    vector_store = VectorStoreService(
        index_path=settings.vector_index_path,
        embedding_model=settings.embedding_model,
        reranker_model=settings.reranker_model if settings.enable_reranking else None,
        enable_reranking=settings.enable_reranking,
    )

    logger.info("Initializing session manager...")
    session_manager = SessionManager(
        redis_url=settings.redis_url,
        session_expire_hours=settings.session_expire_hours,
    )
    await session_manager.connect()

    logger.info("Initializing LLM cache...")
    llm_cache = LLMCache(
        redis_url=settings.redis_url,
        ttl_seconds=86400,  # 24 hours
        key_prefix="llm_cache:",
    )
    await llm_cache.connect()

    logger.info("Initializing Multi-Provider LLM Client...")
    llm_client = MultiProviderLLMClient(
        groq_api_key=settings.groq_api_key,
        groq_model=settings.groq_model,
        gemini_api_key=settings.gemini_api_key,
        gemini_model=settings.gemini_model,
        min_request_interval=settings.llm_min_request_interval,
        max_retries=settings.llm_max_retries,
        cache=llm_cache,
    )

    logger.info("Initializing Literature Reviewer agent...")
    literature_agent = LiteratureReviewerAgent(
        vector_store=vector_store,
        llm_client=llm_client,
        reranker_top_k=settings.reranker_top_k,
        final_top_k=settings.final_top_k,
    )

    # Debate Arena disabled
    # logger.info("Initializing Debate Arena agent...")
    # debate_agent = DebateArenaAgent(
    #     vector_store=vector_store,
    #     groq_api_key=settings.groq_api_key,
    #     groq_model=settings.groq_model,
    # )

    # Literature Review Generator disabled - replaced with Paper Comparator
    # logger.info("Initializing Literature Review Generator...")
    # review_generator = LiteratureReviewGenerator(
    #     vector_store=vector_store,
    #     llm_client=llm_client,
    # )

    logger.info("Initializing Paper Comparator...")
    paper_comparator = PaperComparator(
        vector_store=vector_store,
        llm_client=llm_client,
    )

    # Inject dependencies into route modules
    documents.set_dependencies(pdf_processor, vector_store)
    sessions.set_dependencies(session_manager)
    chat.set_dependencies(literature_agent, session_manager)
    # debate.set_dependencies(debate_agent)  # Disabled
    # literature_review.set_dependencies(review_generator)  # Disabled
    paper_comparison.set_dependencies(paper_comparator)
    cache.set_dependencies(llm_cache)

    logger.info("PRISM API started successfully")

    yield

    # Shutdown
    logger.info("Shutting down PRISM Research Assistant API")
    await session_manager.disconnect()
    await llm_cache.disconnect()


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
# app.include_router(debate.router)  # Disabled
# app.include_router(literature_review.router)  # Disabled - replaced with paper_comparison
app.include_router(paper_comparison.router)
app.include_router(cache.router)


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
