"""
test_align.py - Unit tests for Phase Loop 3 (Bilingual Clause Alignment).
Tests LaBSE embedding caching, structural anchoring, monotonic DP alignment,
1-to-2 and 2-to-1 merges, omission handling, reordering, and low-similarity flags.
"""

import os
import tempfile
from pathlib import Path
import numpy as np
import pytest

from backend.app.segment.models import ClauseNode, ClauseTree
from backend.app.align.models import AlignedPair, AlignmentResult
from backend.app.align.encoder import EmbeddingCache, LaBSEEncoder
from backend.app.align.dp_align import monotonic_dp_align
from backend.app.align.aligner import align_document_trees


class TestEmbeddingCache:
    """Tests for persistent SQLite embedding cache."""

    def test_cache_put_and_get(self, tmp_path):
        db_path = tmp_path / "test_cache.sqlite"
        cache = EmbeddingCache(db_path=db_path)

        text_a = "This is a test English sentence."
        text_b = "यह एक परीक्षण हिन्दी वाक्य है।"
        hash_a = EmbeddingCache.hash_text(text_a)
        hash_b = EmbeddingCache.hash_text(text_b)

        vec_a = np.random.randn(768).astype(np.float32)
        vec_b = np.random.randn(768).astype(np.float32)

        cache.put_many([(hash_a, text_a, vec_a), (hash_b, text_b, vec_b)])

        retrieved = cache.get_many([hash_a, hash_b, "non_existent_hash"])
        assert hash_a in retrieved
        assert hash_b in retrieved
        assert "non_existent_hash" not in retrieved
        np.testing.assert_allclose(retrieved[hash_a], vec_a, atol=1e-6)
        np.testing.assert_allclose(retrieved[hash_b], vec_b, atol=1e-6)


class MockEncoder:
    """Mock encoder for fast unit testing of DP logic without running LaBSE model."""

    def __init__(self, sim_dict=None):
        self.sim_dict = sim_dict or {}

    def compute_similarity(self, text_a: str, text_b: str) -> float:
        key = (text_a.strip(), text_b.strip())
        rev_key = (text_b.strip(), text_a.strip())
        return self.sim_dict.get(key, self.sim_dict.get(rev_key, 0.2))

    def compute_similarity_matrix(self, texts_a, texts_b):
        mat = np.zeros((len(texts_a), len(texts_b)), dtype=np.float32)
        for i, a in enumerate(texts_a):
            for j, b in enumerate(texts_b):
                mat[i, j] = self.compute_similarity(a, b)
        return mat


class TestMonotonicDP:
    """Tests for DP sequence alignment behaviors."""

    def test_exact_1_to_1_alignment(self):
        en_nodes = [
            ClauseNode(path="1.a", label="(a)", text="Definitions of the Act", page_no=1),
            ClauseNode(path="1.b", label="(b)", text="Extent of jurisdiction", page_no=1)
        ]
        hi_nodes = [
            ClauseNode(path="1.a", label="(क)", text="अधिनियम की परिभाषाएं", page_no=1),
            ClauseNode(path="1.b", label="(ख)", text="अधिकारिता का विस्तार", page_no=1)
        ]

        sim_map = {
            ("Definitions of the Act", "अधिनियम की परिभाषाएं"): 0.92,
            ("Extent of jurisdiction", "अधिकारिता का विस्तार"): 0.88
        }
        mock_enc = MockEncoder(sim_map)

        pairs = monotonic_dp_align(en_nodes, hi_nodes, encoder=mock_enc, match_threshold=0.5)
        assert len(pairs) == 2
        assert pairs[0].match_type == "SEMANTIC_1_1"
        assert pairs[0].en_paths == ["1.a"]
        assert pairs[0].hi_paths == ["1.a"]
        assert pairs[0].similarity == 0.92
        assert not pairs[0].low_similarity

        assert pairs[1].match_type == "SEMANTIC_1_1"
        assert pairs[1].en_paths == ["1.b"]
        assert pairs[1].hi_paths == ["1.b"]
        assert pairs[1].similarity == 0.88

    def test_merge_1_to_2_alignment(self):
        """One English sentence corresponds to two split Hindi clauses."""
        en_nodes = [
            ClauseNode(
                path="4.1",
                label="(1)",
                text="The Central Government may appoint officers and specify their powers and duties.",
                page_no=1
            )
        ]
        hi_nodes = [
            ClauseNode(path="4.1", label="(1)", text="केन्द्रीय सरकार अधिकारियों की नियुक्ति कर सकेगी।", page_no=1),
            ClauseNode(path="4.2", label="(2)", text="और उनकी शक्तियों और कर्तव्यों को विनिर्दिष्ट कर सकेगी।", page_no=1)
        ]

        # Individual similarities are moderate, combined similarity is high
        sim_map = {
            ("The Central Government may appoint officers and specify their powers and duties.",
             "केन्द्रीय सरकार अधिकारियों की नियुक्ति कर सकेगी। और उनकी शक्तियों और कर्तव्यों को विनिर्दिष्ट कर सकेगी।"): 0.91,
            ("The Central Government may appoint officers and specify their powers and duties.",
             "केन्द्रीय सरकार अधिकारियों की नियुक्ति कर सकेगी।"): 0.55
        }
        mock_enc = MockEncoder(sim_map)

        pairs = monotonic_dp_align(en_nodes, hi_nodes, encoder=mock_enc, match_threshold=0.5, merge_penalty=0.1)
        assert len(pairs) == 1
        assert pairs[0].match_type == "MERGE_1_2"
        assert pairs[0].en_paths == ["4.1"]
        assert pairs[0].hi_paths == ["4.1", "4.2"]
        assert pairs[0].similarity == 0.91

    def test_merge_2_to_1_alignment(self):
        """Two English clauses correspond to a single combined Hindi clause."""
        en_nodes = [
            ClauseNode(path="3.a", label="(a)", text="Notice shall be given in writing.", page_no=1),
            ClauseNode(path="3.b", label="(b)", text="Such notice must be signed by the applicant.", page_no=1)
        ]
        hi_nodes = [
            ClauseNode(
                path="3.a",
                label="(क)",
                text="सूचना लिखित रूप में दी जाएगी तथा आवेदक द्वारा हस्ताक्षरित होगी।",
                page_no=1
            )
        ]

        sim_map = {
            ("Notice shall be given in writing. Such notice must be signed by the applicant.",
             "सूचना लिखित रूप में दी जाएगी तथा आवेदक द्वारा हस्ताक्षरित होगी।"): 0.89
        }
        mock_enc = MockEncoder(sim_map)

        pairs = monotonic_dp_align(en_nodes, hi_nodes, encoder=mock_enc, match_threshold=0.5, merge_penalty=0.1)
        assert len(pairs) == 1
        assert pairs[0].match_type == "MERGE_2_1"
        assert pairs[0].en_paths == ["3.a", "3.b"]
        assert pairs[0].hi_paths == ["3.a"]
        assert pairs[0].similarity == 0.89

    def test_omission_leaves_unit_unaligned(self):
        """A clause genuinely present in one language but missing in the other."""
        en_nodes = [
            ClauseNode(path="10.1", label="(1)", text="Common clause in English.", page_no=1),
            ClauseNode(path="10.2", label="(2)", text="Inserted amendment in English not in Hindi.", page_no=1)
        ]
        hi_nodes = [
            ClauseNode(path="10.1", label="(1)", text="हिन्दी में सामान्य खंड।", page_no=1)
        ]

        sim_map = {
            ("Common clause in English.", "हिन्दी में सामान्य खंड।"): 0.85,
            ("Inserted amendment in English not in Hindi.", "हिन्दी में सामान्य खंड।"): 0.15
        }
        mock_enc = MockEncoder(sim_map)

        pairs = monotonic_dp_align(en_nodes, hi_nodes, encoder=mock_enc, match_threshold=0.5)
        assert len(pairs) == 2
        assert pairs[0].match_type == "SEMANTIC_1_1"
        assert pairs[0].en_paths == ["10.1"]
        assert pairs[0].hi_paths == ["10.1"]

        assert pairs[1].match_type == "OMISSION"
        assert pairs[1].en_paths == ["10.2"]
        assert pairs[1].hi_paths == []
        assert pairs[1].is_omission

    def test_low_similarity_flag(self):
        """Pairs with similarity between match_threshold and low_sim_threshold have flag set."""
        en_nodes = [ClauseNode(path="5.1", label="(1)", text="Divergent translation in English", page_no=1)]
        hi_nodes = [ClauseNode(path="5.1", label="(1)", text="भिन्न अनुवाद हिन्दी में", page_no=1)]

        sim_map = {
            ("Divergent translation in English", "भिन्न अनुवाद हिन्दी में"): 0.58
        }
        mock_enc = MockEncoder(sim_map)

        pairs = monotonic_dp_align(
            en_nodes, hi_nodes, encoder=mock_enc, match_threshold=0.50, low_sim_threshold=0.65
        )
        assert len(pairs) == 1
        assert pairs[0].similarity == 0.58
        assert pairs[0].low_similarity is True


class TestDocumentTreeAlignment:
    """Tests for full document tree alignment with structural anchoring and DP."""

    def test_structural_anchoring_and_fallback(self):
        en_tree = ClauseTree(
            act_slug="test_act",
            language="en",
            sections=[
                ClauseNode(
                    path="1",
                    label="1",
                    title="Short title",
                    text="This Act may be called the Test Act, 2025.",
                    page_no=1,
                    children=[
                        ClauseNode(path="1.1", label="(1)", text="It extends to the whole of India.", page_no=1),
                        ClauseNode(path="1.2", label="(2)", text="It shall come into force at once.", page_no=1)
                    ]
                ),
                ClauseNode(
                    path="2",
                    label="2",
                    title="Definitions",
                    text="In this Act:",
                    page_no=1,
                    children=[
                        ClauseNode(path="2.a", label="(a)", text="court means high court", page_no=1)
                    ]
                )
            ]
        )

        hi_tree = ClauseTree(
            act_slug="test_act",
            language="hi",
            sections=[
                ClauseNode(
                    path="1",
                    label="1",
                    title="संक्षिप्त नाम",
                    text="यह अधिनियम परीक्षण अधिनियम, 2025 कहा जा सकेगा।",
                    page_no=1,
                    children=[
                        ClauseNode(path="1.1", label="(1)", text="इसका विस्तार सम्पूर्ण भारत पर है।", page_no=1),
                        ClauseNode(path="1.2", label="(2)", text="यह तुरन्त प्रवृत्त होगा।", page_no=1)
                    ]
                )
                # Section 2 omitted in Hindi
            ]
        )

        sim_map = {
            ("Short title This Act may be called the Test Act, 2025.", "संक्षिप्त नाम यह अधिनियम परीक्षण अधिनियम, 2025 कहा जा सकेगा।"): 0.94,
            ("It extends to the whole of India.", "इसका विस्तार सम्पूर्ण भारत पर है।"): 0.92,
            ("It shall come into force at once.", "यह तुरन्त प्रवृत्त होगा।"): 0.91,
        }
        mock_enc = MockEncoder(sim_map)

        res = align_document_trees(en_tree, hi_tree, act_slug="test_act", encoder=mock_enc)

        # Section 1 and its children must be structurally anchored
        sec1_pair = res.find_by_en_path("1")
        assert sec1_pair is not None
        assert sec1_pair.match_type == "STRUCTURAL"
        assert sec1_pair.hi_paths == ["1"]

        sub1_pair = res.find_by_en_path("1.1")
        assert sub1_pair is not None
        assert sub1_pair.match_type == "STRUCTURAL"
        assert sub1_pair.hi_paths == ["1.1"]

        # Section 2 should be in omissions
        sec2_pair = res.find_by_en_path("2")
        assert sec2_pair is not None
        assert sec2_pair.match_type == "OMISSION"
        assert sec2_pair.hi_paths == []
        assert "2" in res.unaligned_en
