"""
aligner.py - Top-Level Bilingual Clause Alignment Pipeline.

Performs multi-stage alignment:
  1. Structural Anchoring: aligns corresponding sections and identical normalized paths.
  2. Within-Section Monotonic DP: semantic alignment using LaBSE embeddings,
     supporting 1-to-1, 1-to-2 merges, 2-to-1 merges, and gap/omission handling.
  3. Reordered Clause Detection: links swapped clauses with high cross-lingual similarity.
  4. Weak Unit Pruning: leaves low-confidence units unaligned instead of forcing links.
"""

import re
from typing import List, Dict, Set, Tuple, Optional
from backend.app.segment.models import ClauseTree, ClauseNode
from backend.app.align.models import AlignedPair, AlignmentResult
from backend.app.align.encoder import LaBSEEncoder
from backend.app.align.dp_align import monotonic_dp_align


def sort_sec_key(path: str) -> int:
    m = re.match(r'^\d+', path)
    return int(m.group(0)) if m else 0


def align_document_trees(
    en_tree: ClauseTree,
    hi_tree: ClauseTree,
    act_slug: str,
    encoder: Optional[LaBSEEncoder] = None,
    struct_threshold: float = 0.25,
    low_sim_threshold: float = 0.65,
    match_threshold: float = 0.50,
    merge_penalty: float = 0.12
) -> AlignmentResult:
    """
    Aligns complete English and Hindi ClauseTrees for an Act.
    """
    if encoder is None:
        encoder = LaBSEEncoder.get_instance()

    result_pairs: List[AlignedPair] = []

    en_sec_dict = {s.path: s for s in en_tree.sections}
    hi_sec_dict = {s.path: s for s in hi_tree.sections}

    all_en_sec_paths = set(en_sec_dict.keys())
    all_hi_sec_paths = set(hi_sec_dict.keys())

    common_secs = sorted(list(all_en_sec_paths & all_hi_sec_paths), key=sort_sec_key)
    en_only_secs = sorted(list(all_en_sec_paths - all_hi_sec_paths), key=sort_sec_key)
    hi_only_secs = sorted(list(all_hi_sec_paths - all_en_sec_paths), key=sort_sec_key)

    # 1. Handle common sections
    for sec_path in common_secs:
        en_sec = en_sec_dict[sec_path]
        hi_sec = hi_sec_dict[sec_path]

        # Top-level section pair
        en_sec_text = f"{en_sec.title or ''} {en_sec.text}".strip()
        hi_sec_text = f"{hi_sec.title or ''} {hi_sec.text}".strip()
        sec_sim = encoder.compute_similarity(en_sec_text, hi_sec_text)

        result_pairs.append(
            AlignedPair(
                en_paths=[sec_path],
                hi_paths=[sec_path],
                en_text=en_sec_text,
                hi_text=hi_sec_text,
                match_type="STRUCTURAL",
                similarity=round(sec_sim, 4),
                low_similarity=(sec_sim < low_sim_threshold)
            )
        )

        # Child clauses (subsections, clauses, provisos, explanations)
        # Flatten all children under this section
        en_children = [n for n in en_sec.flatten() if n.path != sec_path]
        hi_children = [n for n in hi_sec.flatten() if n.path != sec_path]

        en_child_dict = {c.path: c for c in en_children}
        hi_child_dict = {c.path: c for c in hi_children}

        common_child_paths = set(en_child_dict.keys()) & set(hi_child_dict.keys())

        anchored_en: Set[str] = set()
        anchored_hi: Set[str] = set()

        # Stage 1: Structural Anchoring for matching child paths
        for cp in sorted(list(common_child_paths)):
            en_c = en_child_dict[cp]
            hi_c = hi_child_dict[cp]
            sim = encoder.compute_similarity(en_c.text, hi_c.text)

            # Accept identical normalized paths as structural anchor and flag if low similarity
            anchored_en.add(cp)
            anchored_hi.add(cp)
            result_pairs.append(
                AlignedPair(
                    en_paths=[cp],
                    hi_paths=[cp],
                    en_text=en_c.text,
                    hi_text=hi_c.text,
                    match_type="STRUCTURAL",
                    similarity=round(sim, 4),
                    low_similarity=(sim < low_sim_threshold)
                )
            )

        # Stage 2: Monotonic DP for remaining unanchored child clauses
        unanchored_en = [c for c in en_children if c.path not in anchored_en]
        unanchored_hi = [c for c in hi_children if c.path not in anchored_hi]

        if unanchored_en or unanchored_hi:
            dp_pairs = monotonic_dp_align(
                en_clauses=unanchored_en,
                hi_clauses=unanchored_hi,
                encoder=encoder,
                match_threshold=match_threshold,
                merge_penalty=merge_penalty,
                low_sim_threshold=low_sim_threshold
            )
            result_pairs.extend(dp_pairs)

    # 2. Handle English-only sections (e.g. inserted sections omitted in Hindi)
    for sec_path in en_only_secs:
        en_sec = en_sec_dict[sec_path]
        for node in en_sec.flatten():
            result_pairs.append(
                AlignedPair(
                    en_paths=[node.path],
                    hi_paths=[],
                    en_text=f"{node.title or ''} {node.text}".strip(),
                    hi_text="",
                    match_type="OMISSION",
                    similarity=0.0,
                    low_similarity=True
                )
            )

    # 3. Handle Hindi-only sections
    for sec_path in hi_only_secs:
        hi_sec = hi_sec_dict[sec_path]
        for node in hi_sec.flatten():
            result_pairs.append(
                AlignedPair(
                    en_paths=[],
                    hi_paths=[node.path],
                    en_text="",
                    hi_text=f"{node.title or ''} {node.text}".strip(),
                    match_type="OMISSION",
                    similarity=0.0,
                    low_similarity=True
                )
            )

    # 4. Stage 3: Merge adjacent unaligned units if cross-lingual similarity significantly improves
    # Check if an EN omission can merge into an adjacent pair (2-to-1 merge)
    omission_en_indices = [idx for idx, p in enumerate(result_pairs) if len(p.hi_paths) == 0 and len(p.en_paths) == 1]
    absorbed_en_omissions: Set[int] = set()

    for om_idx in omission_en_indices:
        om_pair = result_pairs[om_idx]
        om_path = om_pair.en_paths[0]
        for cand_idx, cand_p in enumerate(result_pairs):
            if cand_idx in absorbed_en_omissions or cand_idx == om_idx or cand_p.is_omission:
                continue
            is_adjacent = any(
                om_path.startswith(f"{cp}.") or cp.startswith(f"{om_path}.")
                for cp in cand_p.en_paths
            )
            if not is_adjacent:
                continue

            merged_text = f"{cand_p.en_text} {om_pair.en_text}".strip()
            s_merged = encoder.compute_similarity(merged_text, cand_p.hi_text)
            if s_merged >= 0.70 and s_merged > cand_p.similarity + 0.08:
                cand_p.en_paths.append(om_path)
                cand_p.en_text = merged_text
                cand_p.similarity = round(s_merged, 4)
                cand_p.match_type = "MERGE_2_1"
                cand_p.low_similarity = (s_merged < low_sim_threshold)
                absorbed_en_omissions.add(om_idx)
                break

    # Check if an HI omission can merge into an adjacent pair (1-to-2 merge)
    omission_hi_indices = [idx for idx, p in enumerate(result_pairs) if len(p.en_paths) == 0 and len(p.hi_paths) == 1]
    absorbed_hi_omissions: Set[int] = set()

    for om_idx in omission_hi_indices:
        om_pair = result_pairs[om_idx]
        om_path = om_pair.hi_paths[0]
        for cand_idx, cand_p in enumerate(result_pairs):
            if cand_idx in absorbed_hi_omissions or cand_idx == om_idx or cand_p.is_omission:
                continue
            is_adjacent = any(
                om_path.startswith(f"{hp}.") or hp.startswith(f"{om_path}.")
                for hp in cand_p.hi_paths
            )
            if not is_adjacent:
                continue

            merged_text = f"{cand_p.hi_text} {om_pair.hi_text}".strip()
            s_merged = encoder.compute_similarity(cand_p.en_text, merged_text)
            if s_merged >= 0.70 and s_merged > cand_p.similarity + 0.08:
                cand_p.hi_paths.append(om_path)
                cand_p.hi_text = merged_text
                cand_p.similarity = round(s_merged, 4)
                cand_p.match_type = "MERGE_1_2"
                cand_p.low_similarity = (s_merged < low_sim_threshold)
                absorbed_hi_omissions.add(om_idx)
                break

    all_absorbed = absorbed_en_omissions | absorbed_hi_omissions
    if all_absorbed:
        result_pairs = [p for i, p in enumerate(result_pairs) if i not in all_absorbed]

    unaligned_en = [p.en_paths[0] for p in result_pairs if len(p.hi_paths) == 0 and len(p.en_paths) > 0]
    unaligned_hi = [p.hi_paths[0] for p in result_pairs if len(p.en_paths) == 0 and len(p.hi_paths) > 0]

    return AlignmentResult(
        act_slug=act_slug,
        pairs=result_pairs,
        unaligned_en=unaligned_en,
        unaligned_hi=unaligned_hi,
        metadata={
            "total_pairs": len(result_pairs),
            "common_sections": len(common_secs),
            "en_only_sections": len(en_only_secs),
            "hi_only_sections": len(hi_only_secs)
        }
    )
