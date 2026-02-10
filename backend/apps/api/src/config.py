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
    faiss_index_path: str = Field(default="./data/faiss_index", alias="FAISS_INDEX_PATH")

    # LLM Configuration
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-70b-versatile", alias="GROQ_MODEL")

    # Embedding Model
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", alias="EMBEDDING_MODEL"
    )

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
