from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.1:latest")
    embedding_model: str = Field(default="nomic-embed-text")
    use_sentence_transformers: bool = Field(default=False)
    use_llm_subtopics: bool = Field(default=True)
    force_local_generation: bool = Field(default=False)
    full_headings_list: bool = Field(default=False)

    chunk_size: int = Field(default=800)
    chunk_overlap: int = Field(default=120)
    retrieval_top_k: int = Field(default=4)
    retrieval_candidate_k: int = Field(default=24)
    temperature: float = Field(default=0.2)
    embedding_batch_size: int = Field(default=64)
    subtopic_max_chars: int = Field(default=12000)
    chapter_max_chars: int = Field(default=12000)

    pdf_cache_dir: Path = Field(default=Path("cache/pdfs"))
    index_dir: Path = Field(default=Path("cache/index"))
    ncert_catalog_path: Path = Field(default=Path("database/ncert_catalog.json"))

    log_level: str = Field(default="INFO")
    cors_allow_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:4173",
            "http://127.0.0.1:4173",
        ]
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
