"""
reorder_lookup.py - Unaligned-Clause Lookup for Cross-Section Misplacement.

Checks whether an apparently missing/unaligned clause appears elsewhere in the opposing
statutory tree. If content is found elsewhere, flags as REORDERED / MISPLACED instead of OMISSION.
"""

try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    class _FuzzFallback:
        @staticmethod
        def token_set_ratio(s1: str, s2: str) -> float:
            return difflib.SequenceMatcher(None, s1.lower(), s2.lower()).ratio() * 100.0
    fuzz = _FuzzFallback()

try:
    from backend.app.align.encoder import get_labse_encoder
except ImportError:
    get_labse_encoder = None


def find_misplaced_content(
    clause_text: str,
    target_clauses: List[Tuple[str, str]],  # List of (path, text)
    min_similarity: float = 0.72
) -> Optional[Tuple[str, float]]:
    """
    Scans a list of (path, text) pairs from the opposing statutory tree to determine
    if clause_text was relocated or reordered elsewhere.
    Returns (matched_path, similarity) if found, else None.
    """
    if not clause_text or not clause_text.strip() or not target_clauses:
        return None

    best_path = None
    best_sim = 0.0

    # 1. Quick lexical screening with RapidFuzz
    candidates = []
    for path, cand_text in target_clauses:
        if not cand_text or not cand_text.strip():
            continue
        token_ratio = fuzz.token_set_ratio(clause_text, cand_text) / 100.0
        if token_ratio >= 0.60:
            candidates.append((path, cand_text, token_ratio))

    if not candidates:
        return None

    # 2. Embedding-based cross-lingual verification if LaBSE is available
    encoder = get_labse_encoder() if get_labse_encoder else None
    if encoder:
        q_emb = encoder.encode(clause_text)
        for path, cand_text, _ in candidates:
            c_emb = encoder.encode(cand_text)
            sim = float(encoder.cosine_similarity(q_emb, c_emb))
            if sim > best_sim:
                best_sim = sim
                best_path = path
    else:
        # Fall back to best token ratio
        best_candidate = max(candidates, key=lambda x: x[2])
        best_path = best_candidate[0]
        best_sim = best_candidate[2]

    if best_sim >= min_similarity and best_path:
        return best_path, round(best_sim, 4)

    return None
