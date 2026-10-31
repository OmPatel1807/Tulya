"""
models.py - Data models for Clause Alignment in Tulya.
Represents aligned clause pairs, merge types, similarity metrics, and alignment results.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AlignedPair(BaseModel):
    """
    Represents an alignment between one or more English clauses and one or more Hindi clauses.
    Supports 1-to-1, 1-to-2, 2-to-1, and omissions (empty path on one side).
    """
    en_paths: List[str] = Field(default_factory=list, description="Canonical English clause paths (empty if Hindi insertion / English omitted)")
    hi_paths: List[str] = Field(default_factory=list, description="Canonical Hindi clause paths (empty if English insertion / Hindi omitted)")
    en_text: str = Field("", description="Concatenated English clause text")
    hi_text: str = Field("", description="Concatenated Hindi clause text")
    match_type: str = Field(..., description="Match category: 'STRUCTURAL', 'SEMANTIC_1_1', 'MERGE_1_2', 'MERGE_2_1', 'REORDERED', 'OMISSION'")
    similarity: float = Field(0.0, description="LaBSE cosine similarity score [0.0, 1.0]")
    low_similarity: bool = Field(False, description="Flag indicating semantic divergence below threshold")

    @property
    def is_omission(self) -> bool:
        """Returns True if this pair represents an unaligned clause (omission in one stream)."""
        return len(self.en_paths) == 0 or len(self.hi_paths) == 0


class AlignmentResult(BaseModel):
    """
    Complete alignment result for an Act.
    """
    act_slug: str
    pairs: List[AlignedPair] = Field(default_factory=list)
    unaligned_en: List[str] = Field(default_factory=list, description="List of English clause paths left unaligned")
    unaligned_hi: List[str] = Field(default_factory=list, description="List of Hindi clause paths left unaligned")
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def find_by_en_path(self, path: str) -> Optional[AlignedPair]:
        for p in self.pairs:
            if path in p.en_paths:
                return p
        return None

    def find_by_hi_path(self, path: str) -> Optional[AlignedPair]:
        for p in self.pairs:
            if path in p.hi_paths:
                return p
        return None
