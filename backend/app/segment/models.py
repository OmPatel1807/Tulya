"""
models.py - Data models for Clause Trees and Nodes.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClauseNode(BaseModel):
    """
    Represents a structural legal unit (Section, Sub-section, Clause, Proviso, Explanation).
    """
    path: str = Field(..., description="Canonical dot-delimited path (e.g. '1', '1.1', '2.a', '3.proviso.1')")
    label: str = Field(..., description="Surface label from the text (e.g. 'Section 1', '(1)', '(a)', 'धारा 1', '(क)')")
    title: Optional[str] = Field(None, description="Clause title or heading caption if present")
    text: str = Field(..., description="Cleaned body text of this specific clause")
    page_no: int = Field(1, description="Source page number")
    children: List["ClauseNode"] = Field(default_factory=list, description="Nested sub-clauses")

    def flatten(self) -> List["ClauseNode"]:
        """Returns flat list containing this node and all recursive children."""
        res = [self]
        for c in self.children:
            res.extend(c.flatten())
        return res


class ClauseTree(BaseModel):
    """
    Hierarchical clause tree for an entire Act stream.
    """
    act_slug: str
    language: str
    sections: List[ClauseNode] = Field(default_factory=list)

    def flatten(self) -> List[ClauseNode]:
        """Flattens all sections and their nested children."""
        res = []
        for s in self.sections:
            res.extend(s.flatten())
        return res

    def find_by_path(self, path: str) -> Optional[ClauseNode]:
        """Finds a clause node by its canonical path."""
        for n in self.flatten():
            if n.path == path:
                return n
        return None
