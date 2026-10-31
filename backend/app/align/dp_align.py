"""
dp_align.py - Monotonic Dynamic Programming Sequence Alignment for Legal Clauses.

Implements monotonic DP sequence alignment supporting:
  - 1-to-1 alignments
  - 1-to-2 merges (one English clause mapped to two Hindi clauses)
  - 2-to-1 merges (two English clauses mapped to one Hindi clause)
  - Gaps / omissions in either language stream
  - Unaligned weak units (avoids forced matches)
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from backend.app.segment.models import ClauseNode
from backend.app.align.models import AlignedPair
from backend.app.align.encoder import LaBSEEncoder


def monotonic_dp_align(
    en_clauses: List[ClauseNode],
    hi_clauses: List[ClauseNode],
    encoder: LaBSEEncoder,
    match_threshold: float = 0.50,
    merge_penalty: float = 0.12,
    skip_score: float = 0.0,
    low_sim_threshold: float = 0.65
) -> List[AlignedPair]:
    """
    Aligns two ordered sequences of clauses within a section or unanchored block.
    Uses dynamic programming with backtracking to recover optimal monotonic alignment.
    """
    m = len(en_clauses)
    n = len(hi_clauses)

    if m == 0 and n == 0:
        return []

    # Handle single-sided cases
    if m == 0:
        return [
            AlignedPair(
                en_paths=[],
                hi_paths=[h.path],
                en_text="",
                hi_text=h.text,
                match_type="OMISSION",
                similarity=0.0,
                low_similarity=True
            )
            for h in hi_clauses
        ]

    if n == 0:
        return [
            AlignedPair(
                en_paths=[e.path],
                hi_paths=[],
                en_text=e.text,
                hi_text="",
                match_type="OMISSION",
                similarity=0.0,
                low_similarity=True
            )
            for e in en_clauses
        ]

    # Pre-extract texts
    en_texts = [e.text.strip() for e in en_clauses]
    hi_texts = [h.text.strip() for h in hi_clauses]

    # Compute 1-to-1 similarity matrix
    sim_1_1 = encoder.compute_similarity_matrix(en_texts, hi_texts)

    # Initialize DP table and backpointers
    # dp[i][j]: best alignment score for en_clauses[:i] and hi_clauses[:j]
    dp = np.full((m + 1, n + 1), -1e9, dtype=np.float32)
    dp[0][0] = 0.0

    # backpointer[i][j] = (prev_i, prev_j, op, sim)
    backpointer: Dict[Tuple[int, int], Tuple[int, int, str, float]] = {}

    for i in range(1, m + 1):
        dp[i][0] = dp[i - 1][0] + skip_score
        backpointer[(i, 0)] = (i - 1, 0, "SKIP_EN", 0.0)

    for j in range(1, n + 1):
        dp[0][j] = dp[0][j - 1] + skip_score
        backpointer[(0, j)] = (0, j - 1, "SKIP_HI", 0.0)

    # Fill DP table
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            best_score = -1e9
            best_trans = (i - 1, j, "SKIP_EN", 0.0)

            # Option 1: Skip English (Omission in Hindi)
            score_skip_en = dp[i - 1][j] + skip_score
            if score_skip_en > best_score:
                best_score = score_skip_en
                best_trans = (i - 1, j, "SKIP_EN", 0.0)

            # Option 2: Skip Hindi (Omission in English)
            score_skip_hi = dp[i][j - 1] + skip_score
            if score_skip_hi > best_score:
                best_score = score_skip_hi
                best_trans = (i, j - 1, "SKIP_HI", 0.0)

            # Option 3: 1-to-1 Match
            s11 = float(sim_1_1[i - 1][j - 1])
            if s11 >= match_threshold:
                score_11 = dp[i - 1][j - 1] + s11
                if score_11 > best_score:
                    best_score = score_11
                    best_trans = (i - 1, j - 1, "MATCH_1_1", s11)

            # Option 4: 1-to-2 Merge (1 EN to 2 HI)
            if j >= 2:
                merged_hi = f"{hi_texts[j - 2]} {hi_texts[j - 1]}"
                s12 = encoder.compute_similarity(en_texts[i - 1], merged_hi)
                if s12 >= match_threshold:
                    score_12 = dp[i - 1][j - 2] + s12 - merge_penalty
                    if score_12 > best_score:
                        best_score = score_12
                        best_trans = (i - 1, j - 2, "MERGE_1_2", s12)

            # Option 5: 2-to-1 Merge (2 EN to 1 HI)
            if i >= 2:
                merged_en = f"{en_texts[i - 2]} {en_texts[i - 1]}"
                s21 = encoder.compute_similarity(merged_en, hi_texts[j - 1])
                if s21 >= match_threshold:
                    score_21 = dp[i - 2][j - 1] + s21 - merge_penalty
                    if score_21 > best_score:
                        best_score = score_21
                        best_trans = (i - 2, j - 1, "MERGE_2_1", s21)

            dp[i][j] = best_score
            backpointer[(i, j)] = best_trans

    # Backtrack from (m, n)
    curr_i, curr_j = m, n
    rev_aligned: List[AlignedPair] = []

    while curr_i > 0 or curr_j > 0:
        prev_i, prev_j, op, sim = backpointer.get((curr_i, curr_j), (curr_i - 1, curr_j, "SKIP_EN", 0.0))

        if op == "MATCH_1_1":
            e_node = en_clauses[curr_i - 1]
            h_node = hi_clauses[curr_j - 1]
            rev_aligned.append(
                AlignedPair(
                    en_paths=[e_node.path],
                    hi_paths=[h_node.path],
                    en_text=e_node.text,
                    hi_text=h_node.text,
                    match_type="SEMANTIC_1_1",
                    similarity=round(sim, 4),
                    low_similarity=(sim < low_sim_threshold)
                )
            )
        elif op == "MERGE_1_2":
            e_node = en_clauses[curr_i - 1]
            h_node1 = hi_clauses[curr_j - 2]
            h_node2 = hi_clauses[curr_j - 1]
            rev_aligned.append(
                AlignedPair(
                    en_paths=[e_node.path],
                    hi_paths=[h_node1.path, h_node2.path],
                    en_text=e_node.text,
                    hi_text=f"{h_node1.text} {h_node2.text}",
                    match_type="MERGE_1_2",
                    similarity=round(sim, 4),
                    low_similarity=(sim < low_sim_threshold)
                )
            )
        elif op == "MERGE_2_1":
            e_node1 = en_clauses[curr_i - 2]
            e_node2 = en_clauses[curr_i - 1]
            h_node = hi_clauses[curr_j - 1]
            rev_aligned.append(
                AlignedPair(
                    en_paths=[e_node1.path, e_node2.path],
                    hi_paths=[h_node.path],
                    en_text=f"{e_node1.text} {e_node2.text}",
                    hi_text=h_node.text,
                    match_type="MERGE_2_1",
                    similarity=round(sim, 4),
                    low_similarity=(sim < low_sim_threshold)
                )
            )
        elif op == "SKIP_EN":
            e_node = en_clauses[curr_i - 1]
            rev_aligned.append(
                AlignedPair(
                    en_paths=[e_node.path],
                    hi_paths=[],
                    en_text=e_node.text,
                    hi_text="",
                    match_type="OMISSION",
                    similarity=0.0,
                    low_similarity=True
                )
            )
        elif op == "SKIP_HI":
            h_node = hi_clauses[curr_j - 1]
            rev_aligned.append(
                AlignedPair(
                    en_paths=[],
                    hi_paths=[h_node.path],
                    en_text="",
                    hi_text=h_node.text,
                    match_type="OMISSION",
                    similarity=0.0,
                    low_similarity=True
                )
            )

        curr_i, curr_j = prev_i, prev_j

    aligned = list(reversed(rev_aligned))

    # Optional Reorder Pass:
    # If any English omission and Hindi omission have high similarity (>= 0.78), link them as REORDERED
    omitted_en = [p for p in aligned if len(p.hi_paths) == 0]
    omitted_hi = [p for p in aligned if len(p.en_paths) == 0]

    if omitted_en and omitted_hi:
        reordered_en_paths = set()
        reordered_hi_paths = set()
        new_reordered_pairs = []

        for p_e in omitted_en:
            ep = p_e.en_paths[0]
            best_sim = 0.0
            best_p_h = None

            for p_h in omitted_hi:
                hp = p_h.hi_paths[0]
                if hp in reordered_hi_paths:
                    continue
                sim = encoder.compute_similarity(p_e.en_text, p_h.hi_text)
                if sim >= 0.78 and sim > best_sim:
                    best_sim = sim
                    best_p_h = p_h

            if best_p_h and best_sim >= 0.78:
                reordered_en_paths.add(ep)
                reordered_hi_paths.add(best_p_h.hi_paths[0])
                new_reordered_pairs.append(
                    AlignedPair(
                        en_paths=[ep],
                        hi_paths=[best_p_h.hi_paths[0]],
                        en_text=p_e.en_text,
                        hi_text=best_p_h.hi_text,
                        match_type="REORDERED",
                        similarity=round(best_sim, 4),
                        low_similarity=False
                    )
                )

        if new_reordered_pairs:
            # Rebuild aligned list replacing the reordered omissions
            filtered = [
                p for p in aligned
                if not (len(p.hi_paths) == 0 and p.en_paths[0] in reordered_en_paths)
                and not (len(p.en_paths) == 0 and p.hi_paths[0] in reordered_hi_paths)
            ]
            aligned = filtered + new_reordered_pairs

    return aligned
