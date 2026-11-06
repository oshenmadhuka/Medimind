"""
MediMind — Application Configuration
Loads and validates environment variables using Pydantic Settings.
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # ── LLM ──────────────────────────────────────────────────────────────────
    GROQ_API_KEY: str = Field(..., description="Groq API key")
    GROQ_MODEL: str = Field(
        default="qwen/qwen3.8-27b",
        description="Groq model to use"
    )

    # ── LangSmith ─────────────────────────────────────────────────────────────
    LANGCHAIN_API_KEY: str = Field(default="", description="LangSmith API key")
    LANGCHAIN_TRACING_V2: bool = Field(default=False, description="Enable LangSmith tracing")
    LANGCHAIN_PROJECT: str = Field(default="medimind-clinical-ai")

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = Field(
        default="postgresql://medimind:medimind123@localhost:5432/medimind_db"
    )

    # ── App ───────────────────────────────────────────────────────────────────
    APP_ENV: str = Field(default="development")
    APP_PORT: int = Field(default=8000)
    FRONTEND_URL: str = Field(default="http://localhost:5173")

    # ── ChromaDB ──────────────────────────────────────────────────────────────
    CHROMA_HOST: str = Field(default="localhost")
    CHROMA_PORT: int = Field(default=8001)
    CHROMA_COLLECTION: str = Field(default="medical_literature")

    # ── External APIs ─────────────────────────────────────────────────────────
    OPENFDA_API_KEY: str = Field(default="", description="OpenFDA API key (optional)")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Global settings instance
settings = get_settings()
