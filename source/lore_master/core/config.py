import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    model: str = "anthropic/claude-haiku-4-5"   # check docs.claude.com for current names
    max_tokens: int = 1024
    temperature: float = 0.7
    retrival_k: int = 4                          # number of chunks to retrieve
    knowlede_dir: str = "data/knowledge-base"
    persist_dir: str = "data/vector_db"
    collection_name: str = "hollow_knight"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


def get_settings() -> Settings:
    if not os.environ.get("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY not found. Copy .env.example to .env.")
    return Settings()
