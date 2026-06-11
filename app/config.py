from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # Application
    APP_TITLE: str = "AI Document Assistant"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # LLM provider: "openai" or "ollama"
    LLM_PROVIDER: str = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"

    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    # Qdrant
    QDRANT_URL: str = "http://qdrant:6333"
    QDRANT_COLLECTION: str = "doc_chunks"
    QDRANT_VECTOR_SIZE: int = 1536  # matches text-embedding-3-small; set 768 for nomic

    # PostgreSQL
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@postgres:5432/docassistant"
    DATABASE_URL_SYNC: str = "postgresql+psycopg2://postgres:password@postgres:5432/docassistant"

    # Ingestion
    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K: int = 4

    # Upload
    UPLOAD_DIR: str = "/tmp/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "case_sensitive": True}


settings = Settings()
