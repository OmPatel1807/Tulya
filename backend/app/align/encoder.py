"""
encoder.py - Cross-Lingual Embedding Engine with Persistent Caching for LaBSE.

Encodes bilingual clauses (English & Hindi) into cross-lingual semantic vector space.
Caches all embeddings in an SQLite database keyed by SHA-256 of cleaned text to guarantee:
  1. Zero redundant model inference across runs.
  2. Blazing fast lookup for repeat evaluation and DP operations.
"""

import os
import sqlite3
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Union
import numpy as np

# Cache path
CACHE_DIR = Path("data/processed/embeddings_cache")
CACHE_DB_PATH = CACHE_DIR / "labse_embeddings.sqlite"


class EmbeddingCache:
    """Persistent SQLite-backed embedding cache."""

    def __init__(self, db_path: Path = CACHE_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    text_hash TEXT PRIMARY KEY,
                    text_preview TEXT,
                    dim INTEGER,
                    vector BLOB
                )
            """)
            conn.commit()

    @staticmethod
    def hash_text(text: str) -> str:
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()

    def get_many(self, hashes: List[str]) -> Dict[str, np.ndarray]:
        if not hashes:
            return {}
        res = {}
        with sqlite3.connect(self.db_path) as conn:
            # Query in batches to avoid SQLite variable limit
            batch_size = 500
            for i in range(0, len(hashes), batch_size):
                batch = hashes[i:i+batch_size]
                placeholders = ",".join("?" for _ in batch)
                cursor = conn.execute(
                    f"SELECT text_hash, dim, vector FROM embeddings WHERE text_hash IN ({placeholders})",
                    batch
                )
                for h, dim, blob in cursor.fetchall():
                    vec = np.frombuffer(blob, dtype=np.float32)
                    res[h] = vec
        return res

    def put_many(self, items: List[Tuple[str, str, np.ndarray]]):
        if not items:
            return
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                "INSERT OR REPLACE INTO embeddings (text_hash, text_preview, dim, vector) VALUES (?, ?, ?, ?)",
                [(h, txt[:100], vec.shape[0], vec.astype(np.float32).tobytes()) for h, txt, vec in items]
            )
            conn.commit()


class LaBSEEncoder:
    """
    Singleton wrapper for sentence-transformers/LaBSE with automatic embedding caching.
    """
    _instance: Optional["LaBSEEncoder"] = None

    def __init__(self, model_name: str = "sentence-transformers/LaBSE"):
        self.model_name = model_name
        self.cache = EmbeddingCache()
        self._model = None

    @classmethod
    def get_instance(cls, model_name: str = "sentence-transformers/LaBSE") -> "LaBSEEncoder":
        if cls._instance is None:
            cls._instance = cls(model_name)
        return cls._instance

    @property
    def model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: List[str]) -> np.ndarray:
        """
        Encodes a list of texts into normalized embedding vectors.
        Retrieves cached embeddings first, only computing uncached texts with LaBSE.
        """
        if not texts:
            return np.zeros((0, 768), dtype=np.float32)

        hashes = [EmbeddingCache.hash_text(t) for t in texts]
        cached = self.cache.get_many(hashes)

        uncached_indices = [i for i, h in enumerate(hashes) if h not in cached]
        if uncached_indices:
            uncached_texts = [texts[i] for i in uncached_indices]
            new_vectors = self.model.encode(
                uncached_texts,
                batch_size=32,
                show_progress_bar=False,
                normalize_embeddings=True
            )
            # Store in cache
            new_items = []
            for idx, i in enumerate(uncached_indices):
                h = hashes[i]
                v = new_vectors[idx]
                cached[h] = v
                new_items.append((h, texts[i], v))
            self.cache.put_many(new_items)

        res = np.array([cached[h] for h in hashes], dtype=np.float32)
        return res

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        """Computes cosine similarity between two texts."""
        if not text_a.strip() or not text_b.strip():
            return 0.0
        vecs = self.encode([text_a, text_b])
        dot = float(np.dot(vecs[0], vecs[1]))
        return max(0.0, min(1.0, dot))

    def compute_similarity_matrix(self, texts_a: List[str], texts_b: List[str]) -> np.ndarray:
        """
        Computes cosine similarity matrix between two lists of texts.
        Output shape: (len(texts_a), len(texts_b)).
        """
        if not texts_a or not texts_b:
            return np.zeros((len(texts_a), len(texts_b)), dtype=np.float32)
        vecs_a = self.encode(texts_a)
        vecs_b = self.encode(texts_b)
        sim_mat = np.matmul(vecs_a, vecs_b.T)
        return np.clip(sim_mat, 0.0, 1.0)
