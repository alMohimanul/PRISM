"""Configuration management using Pydantic Settings."""

from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")

    # Database Configuration
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/prism",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    # Vector Database (FAISS)
    vector_index_path: str = Field(default="./data/faiss_index", alias="VECTOR_INDEX_PATH")

    # PDF Storage
    pdf_storage_path: str = Field(default="./data/pdfs", alias="PDF_STORAGE_PATH")

    # LLM Configuration - Groq
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="openai/gpt-oss-20b", alias="GROQ_MODEL")

    # LLM Configuration - Gemini
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    llm_min_request_interval: float = Field(default=2.0, alias="LLM_MIN_REQUEST_INTERVAL")
    llm_max_retries: int = Field(default=3, alias="LLM_MAX_RETRIES")

    # Embedding Model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

    # Reranking Configuration
    enable_reranking: bool = Field(default=True, alias="ENABLE_RERANKING")
    reranker_model: str = Field(
        default="cross-encoder/ms-marco-MiniLM-L-6-v2", alias="RERANKER_MODEL"
    )
    reranker_top_k: int = Field(default=8, alias="RERANKER_TOP_K")  # Heavily reduced for free tier
    final_top_k: int = Field(default=2, alias="FINAL_TOP_K")  # 2 highly relevant chunks

    # PDF Processing
    max_file_size_mb: int = Field(default=50, alias="MAX_FILE_SIZE_MB")
    chunk_size: int = Field(default=1000, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=200, alias="CHUNK_OVERLAP")

    # Session Configuration
    session_expire_hours: int = Field(default=24, alias="SESSION_EXPIRE_HOURS")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        alias="CORS_ORIGINS",
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string."""
        if isinstance(self.cors_origins, str):
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins

    # Logging
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


# Global settings instance
settings = Settings()
