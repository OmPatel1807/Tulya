"""
cache.py - Persistent Disk Cache for LLM Semantic Responses.

Keyed by SHA-256 hash of:
  provider:model:prompt_version:hash(en_text + "|||" + hi_text)
"""

import os
import sqlite3
import hashlib
import json
from typing import Optional, Dict, Any


DEFAULT_CACHE_DIR = "data/processed/llm_cache"
DEFAULT_DB_PATH = os.path.join(DEFAULT_CACHE_DIR, "semantic_responses.sqlite")


class SemanticCache:
    """SQLite-backed persistent cache for LLM responses."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_cache (
                    cache_key TEXT PRIMARY KEY,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_version TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    tokens_prompt INTEGER,
                    tokens_completion INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    @staticmethod
    def compute_key(provider: str, model: str, prompt_version: str, en_text: str, hi_text: str) -> str:
        content_hash = hashlib.sha256(f"{en_text.strip()}|||{hi_text.strip()}".encode("utf-8")).hexdigest()
        full_str = f"{provider}:{model}:{prompt_version}:{content_hash}"
        return hashlib.sha256(full_str.encode("utf-8")).hexdigest()

    def get(self, cache_key: str) -> Optional[Dict[str, Any]]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT response_json, tokens_prompt, tokens_completion FROM semantic_cache WHERE cache_key = ?",
                (cache_key,)
            )
            row = cursor.fetchone()
            if row:
                return {
                    "response": json.loads(row[0]),
                    "tokens_prompt": row[1] or 0,
                    "tokens_completion": row[2] or 0
                }
        return None

    def put(
        self,
        cache_key: str,
        provider: str,
        model: str,
        prompt_version: str,
        response_dict: Dict[str, Any],
        tokens_prompt: int = 0,
        tokens_completion: int = 0
    ):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO semantic_cache 
                (cache_key, provider, model, prompt_version, response_json, tokens_prompt, tokens_completion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                cache_key,
                provider,
                model,
                prompt_version,
                json.dumps(response_dict, ensure_ascii=False),
                tokens_prompt,
                tokens_completion
            ))
            conn.commit()
