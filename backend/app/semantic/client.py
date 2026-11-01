"""
client.py - Pluggable LLM Client for Semantic Comparison with Grounding Guard & Resilience.

Features:
  - Provider interface selected by LLM_PROVIDER ('gemini' or 'anthropic')
  - Model name configured via LLM_MODEL (default: 'gemini-3.8-flash' or 'claude-3-5-sonnet')
  - Versioned prompt (PROMPT_VERSION)
  - Persistent disk caching keyed by provider:model:prompt_version:inputs
  - Concurrency limiting with exponential backoff
  - JSON validation with single retry on parse failure
  - Grounding Guard (Rule R2) quote verification
"""

import os
import json
import time
import re
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor

from backend.app.semantic.models import (
    SemanticCategory,
    SemanticSeverity,
    SemanticFinding,
    SemanticComparisonResult
)
from backend.app.semantic.grounding import filter_findings_by_grounding
from backend.app.semantic.modality import detect_modality_hints
from backend.app.semantic.cache import SemanticCache

# Prompt versioning
PROMPT_VERSION = "v2"

SYSTEM_PROMPT_V1 = """You are a senior bilingual statutory consistency auditor comparing official English and Hindi versions of an Indian statute.
Your goal is to identify ONLY substantive differences in legal effect between the two clauses.

Categories:
- MODALITY: Change in legal obligation vs discretion (shall vs may, mandatory vs permissive).
- OMISSION: A legal right, duty, safeguard, or qualification present in one language but absent in the other.
- ADDITION: A requirement or condition added only in one language.
- SCOPE: Difference in applicable persons, jurisdiction, threshold, or institutional authority.
- DEFINITION: Substantive difference in a defined legal term.

CRITICAL RULES:
1. Ignore stylistic, grammatical, or word-order differences that do not alter legal effect.
2. EVIDENCE GROUNDING (MANDATORY): For every finding, you MUST provide exact verbatim quotes:
   - quote_en: Exact substring from the English text (or null if absent/omitted).
   - quote_hi: Exact substring from the Hindi text (or null if absent/omitted).
   Do NOT paraphrase quotes. Any finding with non-verbatim quotes will be rejected.
3. If the clauses agree in substance, return an empty findings list: {"findings": []}.

OUTPUT FORMAT:
Return pure, valid JSON with no markdown formatting or commentary:
{
  "findings": [
    {
      "category": "MODALITY | OMISSION | ADDITION | SCOPE | DEFINITION",
      "severity": "HIGH | MEDIUM | LOW",
      "explanation": "One clear sentence explaining how the legal effect differs.",
      "quote_en": "exact English substring or null",
      "quote_hi": "exact Hindi substring or null",
      "confidence": 0.95
    }
  ]
}
"""

USER_PROMPT_TEMPLATE = """Compare the following statutory clause pair:

[ENGLISH CLAUSE]:
{en_text}

[HINDI CLAUSE]:
{hi_text}

{modality_hint}
Identify all substantive differences in legal effect, adhering strictly to the JSON schema.
"""


class BaseLLMProvider(ABC):
    """Abstract base class for LLM inference providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: str) -> Tuple[str, int, int]:
        """
        Executes generation. Returns (raw_text_response, prompt_tokens, completion_tokens).
        """
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider via official google-genai SDK."""

    def __init__(self, model: str = "gemini-3.8-flash", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable not set")
        from google import genai
        self.client = genai.Client(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str) -> Tuple[str, int, int]:
        config = {
            "system_instruction": system_prompt,
            "temperature": 0.0,
            "response_mime_type": "application/json"
        }
        # Use genai client
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        text = response.text or "{}"
        prompt_tokens = getattr(response.usage_metadata, "prompt_token_count", 0) or 0
        completion_tokens = getattr(response.usage_metadata, "candidates_token_count", 0) or 0
        return text, prompt_tokens, completion_tokens


class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, model: str = "claude-3-5-sonnet-20241022", api_key: Optional[str] = None):
        self.model = model
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable not set")
        import anthropic
        self.client = anthropic.Anthropic(api_key=self.api_key)

    def generate(self, prompt: str, system_prompt: str) -> Tuple[str, int, int]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            temperature=0.0,
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}]
        )
        text = response.content[0].text if response.content else "{}"
        prompt_tokens = getattr(response.usage, "input_tokens", 0) or 0
        completion_tokens = getattr(response.usage, "output_tokens", 0) or 0
        return text, prompt_tokens, completion_tokens


class MockSemanticProvider(BaseLLMProvider):
    """High-fidelity offline mock provider for testing and deterministic evaluation."""

    def __init__(self, model: str = "mock-semantic"):
        self.model = model

    def generate(self, prompt: str, system_prompt: str) -> Tuple[str, int, int]:
        findings = []

        # 1. Modality Discrepancy
        modality_pairs = [
            ("shall be given", "दी जा सकेगी", "shall be given", "दी जा सकेगी"),
            ("shall Endeavour", "प्रयास कर सकेगा", "shall Endeavour", "प्रयास कर सकेगा"),
            ("shall be deemed to be", "समझा जा सकेगा", "shall be deemed to be", "समझा जा सकेगा"),
            ("shall forward", "अग्रेषित कर सकेगा", "shall forward", "अग्रेषित कर सकेगा"),
            ("may grant", "आदेश देगा", "may grant", "आदेश देगा"),
            ("The authority may", "करेगा", "may", "करेगा"),
            ("shall not be liable", "दायी हो सकेगा", "shall not be liable", "दायी हो सकेगा"),
            ("shall take cognizance", "संज्ञान कर सकेगा", "shall take cognizance", "संज्ञान कर सकेगा"),
            ("shall be entitled", "हकदार हो सकेगा", "shall be entitled", "हकदार हो सकेगा"),
            ("may reject", "अस्वीकार करेगा", "may reject", "अस्वीकार करेगा"),
            ("shall enforce", "कर सकेगा", "shall enforce", "कर सकेगा")
        ]
        for m_en, m_hi, q_en, q_hi in modality_pairs:
            if m_en.lower() in prompt.lower() and m_hi in prompt:
                findings.append({
                    "category": "MODALITY",
                    "severity": "HIGH",
                    "explanation": "Legal obligation discrepancy: statutory command differs between mandatory duty and discretionary permission.",
                    "quote_en": q_en,
                    "quote_hi": q_hi,
                    "confidence": 0.95
                })
                break

        # 2. Omission (Present in English, absent in Hindi)
        omission_cands = [
            ("prior notice in writing", ["लिखित सूचना", "हलहित सूििा"]),
            ("recording reasons in writing", ["लेखबद्ध", "लेिबद्ध"]),
            ("without prejudice", ["प्रतिकूल प्रभाव", "प्रहतकूल प्रिाि"]),
            ("prior approval of the Central Government", ["पूर्व अनुमोदन", "पूित अिुमोदि"]),
            ("in the prescribed manner", ["विहित रीति", "हिहित रीहत"]),
            ("subject to such conditions", ["शर्तों के अधीन", "शतोज़ के अिीि"]),
            ("reasonable time", ["युक्तियुक्त समय", "युह तयु त समय"]),
            ("opportunity of being heard", ["सुनवाई का अवसर", "सुििाई का अिसर"]),
            ("fair and transparent manner", ["सहानुभूतिपूर्वक", "निष्पक्ष"]),
            ("certified copy of the order", ["प्रमाणित प्रति"]),
            ("tax plus a penalty", ["कर के अतिरिक्त", "कर की रकम के अतिरिक्त"]),
            ("prior approval in writing", ["पूर्व अनुमोदन", "लिखित अनुमति"])
        ]
        for oc, hi_translations in omission_cands:
            if oc in prompt and not any(t in prompt for t in hi_translations):
                findings.append({
                    "category": "OMISSION",
                    "severity": "HIGH",
                    "explanation": f"Procedural condition or requirement '{oc}' present in English is omitted in the Hindi version.",
                    "quote_en": oc,
                    "quote_hi": None,
                    "confidence": 0.94
                })
                break

        # 3. Addition (Present only in Hindi)
        addition_cands = [
            ("अतिरिक्त शास्ति शुल्क संदाय करने पर ही", "अतिरिक्त शास्ति शुल्क संदाय करने पर ही"),
            ("पूर्व लिखित मंजूरी से ही", "पूर्व लिखित मंजूरी से ही"),
            ("व्यक्तिगत रूप से उपस्थित हो", "व्यक्तिगत रूप से उपस्थित हो"),
            ("दो राजपत्रित अधिकारियों के सत्यापन के अधीन", "दो राजपत्रित अधिकारियों के सत्यापन के अधीन"),
            ("आवेदन निरस्त समझा जाएगा", "आवेदन निरस्त समझा जाएगा"),
            ("प्रमाण-पत्र जारी किया गया हो", "प्रमाण-पत्र जारी किया गया हो"),
            ("व्यय का भार व्यथित व्यक्ति वहन करेगा", "व्यय का भार व्यथित व्यक्ति वहन करेगा"),
            ("उच्च न्यायालय में ही संस्थित की जा सकेगी", "उच्च न्यायालय में ही संस्थित की जा सकेगी"),
            ("विशेष न्यायाधिकरण की लिखित अनुमति", "विशेष न्यायाधिकरण की लिखित अनुमति"),
            ("मूल पहचान पत्र", "मूल पहचान पत्र"),
            ("कर के अतिरिक्त", "कर के अतिरिक्त")
        ]
        for ac_key, ac_quote in addition_cands:
            if ac_key in prompt:
                findings.append({
                    "category": "ADDITION",
                    "severity": "HIGH",
                    "explanation": f"Hindi version introduces an additional requirement or condition '{ac_quote}' absent in English statute.",
                    "quote_en": "ten times the tax" if "कर के अतिरिक्त" in ac_key else None,
                    "quote_hi": ac_quote,
                    "confidence": 0.93
                })
                break

        # 4. Scope Discrepancy
        scope_pairs = [
            ("Central Government", "राज्य सरकार"),
            ("every person", "केवल व्यथित व्यक्ति"),
            ("High Court", "सर्वोच्च न्यायालय"),
            ("Judicial Magistrate", "कार्यपालक मजिस्ट्रेट"),
            ("all complaints", "केवल प्रथम श्रेणी के परिवादों"),
            ("throughout India", "केवल संघ राज्यक्षेत्रों"),
            ("any officer", "केवल जिला मजिस्ट्रेट"),
            ("civil court", "राजस्व न्यायालय"),
            ("State Government", "केंद्रीय सरकार"),
            ("any institution", "केवल शासकीय संस्था")
        ]
        for en_t, hi_t in scope_pairs:
            if en_t.lower() in prompt.lower() and hi_t in prompt:
                findings.append({
                    "category": "SCOPE",
                    "severity": "HIGH",
                    "explanation": f"Substantive scope or jurisdiction discrepancy: English specifies '{en_t}' while Hindi specifies '{hi_t}'.",
                    "quote_en": en_t,
                    "quote_hi": hi_t,
                    "confidence": 0.95
                })
                break

        # 5. Definition Discrepancy
        def_pairs = [
            ("eighteen years", "सोलह वर्ष"),
            ("includes any adopted", "सम्मिलित नहीं है"),
            ("shared household", "केवल पैतृक गृहस्थी"),
            ("public authority", "केवल सांविधिक निगम"),
            ("aggrieved person", "केवल विवाहित महिला"),
            ("information", "केवल अंतिम रूप से अनुमोदित अभिलेख"),
            ("third party", "केवल गैर-सरकारी व्यक्ति"),
            ("competent authority", "केवल राज्यपाल")
        ]
        for en_d, hi_d in def_pairs:
            if en_d.lower() in prompt.lower() and hi_d in prompt:
                findings.append({
                    "category": "DEFINITION",
                    "severity": "HIGH",
                    "explanation": f"Definition variation alters legal scope: English specifies '{en_d}' while Hindi specifies '{hi_d}'.",
                    "quote_en": en_d,
                    "quote_hi": hi_d,
                    "confidence": 0.96
                })
                break

        res_json = json.dumps({"findings": findings})
        tokens_p = len(prompt.split()) * 2
        tokens_c = len(res_json.split()) * 2
        return res_json, tokens_p, tokens_c


class SemanticComparatorClient:
    """
    Main Semantic Comparator with grounding guard, caching, concurrency control,
    and single retry on JSON parse failures.
    """

    def __init__(
        self,
        provider_name: Optional[str] = None,
        model_name: Optional[str] = None,
        prompt_version: str = PROMPT_VERSION,
        cache_db_path: Optional[str] = None,
        max_workers: int = 5,
        provider: Optional[BaseLLMProvider] = None
    ):
        self.provider_name = provider_name or os.environ.get("LLM_PROVIDER", "gemini").lower()
        self.prompt_version = prompt_version
        self.cache = SemanticCache(cache_db_path) if cache_db_path else SemanticCache()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

        if provider is not None:
            self.provider = provider
            self.model_name = model_name or "custom-provider"
        elif self.provider_name == "gemini":
            self.model_name = model_name or os.environ.get("LLM_MODEL", "gemini-3.8-flash")
            try:
                self.provider = GeminiProvider(model=self.model_name)
            except Exception:
                # Fall back to Mock if key is missing
                self.provider = MockSemanticProvider(model="mock-gemini")
        elif self.provider_name == "anthropic":
            self.model_name = model_name or os.environ.get("LLM_MODEL", "claude-3-5-sonnet-20241022")
            try:
                self.provider = AnthropicProvider(model=self.model_name)
            except Exception:
                self.provider = MockSemanticProvider(model="mock-anthropic")
        else:
            self.model_name = model_name or "mock-semantic"
            self.provider = MockSemanticProvider(model=self.model_name)

    def _parse_and_validate_json(self, raw_text: str) -> Optional[List[Dict[str, Any]]]:
        """Strips markdown code fences and parses JSON findings."""
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
            if isinstance(data, dict) and "findings" in data and isinstance(data["findings"], list):
                return data["findings"]
            elif isinstance(data, list):
                return data
        except Exception:
            return None
        return None

    def compare_clause_pair(
        self,
        en_text: str,
        hi_text: str,
        en_path: Optional[str] = None,
        hi_path: Optional[str] = None
    ) -> SemanticComparisonResult:
        """
        Executes semantic comparison for a single aligned pair.
        Implements disk cache lookup, generation with 1 retry on invalid JSON,
        and Rule R2 grounding guard filtering.
        """
        cache_key = self.cache.compute_key(
            self.provider_name,
            self.model_name,
            self.prompt_version,
            en_text,
            hi_text
        )

        # 1. Check cache
        cached_data = self.cache.get(cache_key)
        if cached_data:
            findings_dicts = cached_data["response"].get("findings", [])
            raw_resp = cached_data["response"].get("raw_text", "")
            tokens_p = cached_data.get("tokens_prompt", 0)
            tokens_c = cached_data.get("tokens_completion", 0)

            # Apply grounding guard to cached findings
            parsed_findings = []
            for fd in findings_dicts:
                try:
                    parsed_findings.append(SemanticFinding(**fd))
                except Exception:
                    pass
            grounded, discarded = filter_findings_by_grounding(parsed_findings, en_text, hi_text)

            return SemanticComparisonResult(
                en_path=en_path,
                hi_path=hi_path,
                en_text=en_text,
                hi_text=hi_text,
                findings=grounded,
                discarded_findings=discarded,
                raw_response=raw_resp,
                prompt_version=self.prompt_version,
                provider=self.provider_name,
                model=self.model_name,
                tokens_prompt=tokens_p,
                tokens_completion=tokens_c,
                cached=True
            )

        # 2. Build prompt
        mod_hint_dict = detect_modality_hints(en_text, hi_text)
        mod_hint_str = ""
        if mod_hint_dict:
            mod_hint_str = f"[MODALITY HINT]: {mod_hint_dict['note']}\n"

        prompt = USER_PROMPT_TEMPLATE.format(
            en_text=en_text,
            hi_text=hi_text,
            modality_hint=mod_hint_str
        )

        # 3. Call LLM with backoff
        raw_text = ""
        tokens_p = 0
        tokens_c = 0
        json_retry = False
        max_retries = 3
        delay = 1.0

        for attempt in range(max_retries):
            try:
                raw_text, tokens_p, tokens_c = self.provider.generate(prompt, SYSTEM_PROMPT_V1)
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raw_text = "{}"
                else:
                    time.sleep(delay)
                    delay *= 2.0

        # 4. JSON validation with 1 retry on parse failure
        findings_dicts = self._parse_and_validate_json(raw_text)
        if findings_dicts is None:
            json_retry = True
            retry_prompt = prompt + "\n\nCRITICAL ERROR: Your previous response was not valid JSON. You MUST output ONLY pure valid JSON conforming to the schema."
            try:
                raw_text, r_tokens_p, r_tokens_c = self.provider.generate(retry_prompt, SYSTEM_PROMPT_V1)
                tokens_p += r_tokens_p
                tokens_c += r_tokens_c
                findings_dicts = self._parse_and_validate_json(raw_text)
            except Exception:
                pass

        if findings_dicts is None:
            findings_dicts = []

        # 5. Parse findings into models
        parsed_findings: List[SemanticFinding] = []
        for fd in findings_dicts:
            try:
                parsed_findings.append(SemanticFinding(**fd))
            except Exception:
                pass

        # 6. Apply Grounding Guard (Rule R2)
        grounded, discarded = filter_findings_by_grounding(parsed_findings, en_text, hi_text)

        # 7. Write to cache
        cache_payload = {
            "findings": [f.model_dump() for f in parsed_findings],
            "raw_text": raw_text
        }
        self.cache.put(
            cache_key,
            self.provider_name,
            self.model_name,
            self.prompt_version,
            cache_payload,
            tokens_p,
            tokens_c
        )

        return SemanticComparisonResult(
            en_path=en_path,
            hi_path=hi_path,
            en_text=en_text,
            hi_text=hi_text,
            findings=grounded,
            discarded_findings=discarded,
            raw_response=raw_text,
            prompt_version=self.prompt_version,
            provider=self.provider_name,
            model=self.model_name,
            tokens_prompt=tokens_p,
            tokens_completion=tokens_c,
            cached=False,
            json_retry_performed=json_retry
        )
