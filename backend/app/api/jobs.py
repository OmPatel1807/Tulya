"""
jobs.py - Background job manager for Tulya statutory audits.

Tracks stage progress, handles legacy font detection and graceful fallbacks,
and produces full AuditReportResponse objects.
"""

import os
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, Optional, List, Any
from collections import defaultdict

from backend.app.api.models import (
    JobProgress,
    JobStage,
    JobStatus,
    AuditReportResponse,
    LEGAL_DISCLAIMER
)
from backend.app.ingest.script_check import check_script, LegacyFontError
from backend.app.ingest.clean import clean_page_text
from backend.app.ingest.pdf_loader import extract_text
from backend.app.ingest.split_language import process_document_pair
from backend.app.segment.segmenter import segment_document
from backend.app.align.aligner import align_document_trees
from backend.app.pipeline.runner import PipelineRunner
from backend.app.pipeline.models import AuditFinding, AuditCategory, AuditSeverity, AuditSource
from backend.app.semantic.client import SemanticComparatorClient


class JobManager:
    """Thread-safe background job registry."""

    def __init__(self):
        self._lock = threading.Lock()
        self._progress: Dict[str, JobProgress] = {}
        self._reports: Dict[str, AuditReportResponse] = {}

    def create_job(self, act_slug: str) -> JobProgress:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        prog = JobProgress(
            job_id=job_id,
            status=JobStatus.PENDING,
            stage=JobStage.QUEUED,
            progress_percent=0.0,
            stage_message="Job queued for processing",
            created_at=now,
            updated_at=now
        )
        with self._lock:
            self._progress[job_id] = prog
        return prog

    def get_progress(self, job_id: str) -> Optional[JobProgress]:
        with self._lock:
            return self._progress.get(job_id)

    def get_report(self, job_id: str) -> Optional[AuditReportResponse]:
        with self._lock:
            return self._reports.get(job_id)

    def _update_stage(
        self,
        job_id: str,
        stage: JobStage,
        percent: float,
        message: str,
        status: JobStatus = JobStatus.PROCESSING,
        error: Optional[str] = None,
        fallback_used: bool = False
    ):
        with self._lock:
            if job_id in self._progress:
                now = datetime.now(timezone.utc).isoformat()
                self._progress[job_id] = JobProgress(
                    job_id=job_id,
                    status=status,
                    stage=stage,
                    progress_percent=percent,
                    stage_message=message,
                    error=error,
                    fallback_used=fallback_used or self._progress[job_id].fallback_used,
                    created_at=self._progress[job_id].created_at,
                    updated_at=now
                )

    def process_job_async(
        self,
        job_id: str,
        act_slug: str,
        en_path: Optional[str] = None,
        hi_path: Optional[str] = None,
        en_text_pages: Optional[List[Dict[str, Any]]] = None,
        hi_text_pages: Optional[List[Dict[str, Any]]] = None,
        force_deterministic: bool = False,
        title: Optional[str] = None
    ):
        """Starts background thread to run pipeline."""
        thread = threading.Thread(
            target=self._run_job_pipeline,
            args=(job_id, act_slug, en_path, hi_path, en_text_pages, hi_text_pages, force_deterministic, title),
            daemon=True
        )
        thread.start()

    def _run_job_pipeline(
        self,
        job_id: str,
        act_slug: str,
        en_path: Optional[str] = None,
        hi_path: Optional[str] = None,
        en_text_pages: Optional[List[Dict[str, Any]]] = None,
        hi_text_pages: Optional[List[Dict[str, Any]]] = None,
        force_deterministic: bool = False,
        title: Optional[str] = None
    ):
        t0 = time.perf_counter()
        display_title = title or act_slug.replace("_", " ").title()

        try:
            # --- Stage 1: INGESTION (10%) ---
            self._update_stage(job_id, JobStage.INGESTION, 10.0, "Extracting text streams and checking Unicode script integrity...")

            if en_text_pages is None or hi_text_pages is None:
                if not en_path or not hi_path:
                    raise ValueError("Missing file paths or text pages for analysis.")
                if not os.path.exists(en_path) or not os.path.exists(hi_path):
                    raise FileNotFoundError("Uploaded file path does not exist.")

                # Check empty files
                if os.path.getsize(en_path) == 0 or os.path.getsize(hi_path) == 0:
                    raise ValueError("Uploaded PDF file is empty (0 bytes) or corrupted.")

                doc = process_document_pair(act_slug, en_path=en_path, hi_path=hi_path)
                en_pages = doc["english"]
                hi_pages = doc["hindi"]
            else:
                en_pages = en_text_pages
                hi_pages = hi_text_pages

            # Validate extraction content
            en_total_len = sum(len(p.get("text", "")) for p in en_pages)
            hi_total_len = sum(len(p.get("text", "")) for p in hi_pages)
            if en_total_len < 10 or hi_total_len < 10:
                raise ValueError("PDF text extraction produced insufficient text. Document may be an un-OCRed scanned image.")

            # Script Check for Hindi
            for p in hi_pages:
                check_script(p.get("text", ""), expected_lang="hi", strict=True)

            # --- Stage 2: SEGMENTATION (30%) ---
            self._update_stage(job_id, JobStage.SEGMENTATION, 30.0, "Constructing hierarchical statutory clause trees...")
            en_tree = segment_document(en_pages, lang="en", act_slug=act_slug)
            hi_tree = segment_document(hi_pages, lang="hi", act_slug=act_slug)

            # --- Stage 3: ALIGNMENT (50%) ---
            self._update_stage(job_id, JobStage.ALIGNMENT, 50.0, "Aligning statutory provisions across languages with monotonic DP...")
            align_res = align_document_trees(en_tree, hi_tree, act_slug=act_slug)

            # --- Stage 4: FACTS (70%) & SEMANTIC (85%) & MERGE (95%) ---
            self._update_stage(job_id, JobStage.FACTS, 70.0, f"Comparing factual entities across {len(align_res.pairs)} aligned clauses...")

            fallback_used = force_deterministic
            if not force_deterministic:
                try:
                    semantic_client = SemanticComparatorClient()
                except Exception:
                    fallback_used = True
                    semantic_client = None
            else:
                semantic_client = None

            runner = PipelineRunner(semantic_client=semantic_client)
            all_findings: List[AuditFinding] = []
            aligned_pair_records: List[Dict[str, Any]] = []

            total_pairs = len(align_res.pairs)
            for idx, p in enumerate(align_res.pairs):
                # Update progress smoothly through facts and semantic
                if total_pairs > 0 and idx % max(1, total_pairs // 5) == 0:
                    pct = 70.0 + (idx / total_pairs) * 20.0
                    stage_curr = JobStage.FACTS if pct < 80.0 else JobStage.SEMANTIC
                    msg = "Extracting factual differences..." if stage_curr == JobStage.FACTS else "Evaluating grounded semantic consistency..."
                    self._update_stage(job_id, stage_curr, pct, msg, fallback_used=fallback_used)

                # Execute clause audit
                c_id = f"{act_slug}_{idx+1:03d}"
                audit_res = runner.audit_clause_pair(
                    case_id=c_id,
                    en_text=p.en_text,
                    hi_text=p.hi_text,
                    en_paths=p.en_paths,
                    hi_paths=p.hi_paths
                )

                all_findings.extend(audit_res.findings)
                aligned_pair_records.append({
                    "pair_index": idx,
                    "en_paths": p.en_paths,
                    "hi_paths": p.hi_paths,
                    "en_text": p.en_text,
                    "hi_text": p.hi_text,
                    "match_type": p.match_type,
                    "similarity": round(p.similarity, 4),
                    "is_omission": p.is_omission,
                    "findings_count": len(audit_res.findings),
                    "finding_ids": [f.finding_id for f in audit_res.findings]
                })

            # --- Stage 6: MERGE & REPORT GENERATION (95%) ---
            self._update_stage(job_id, JobStage.MERGE, 95.0, "Consolidating findings and compiling audit scorecard...", fallback_used=fallback_used)

            # Summaries
            by_category = defaultdict(int)
            by_severity = defaultdict(int)
            by_source = {
                "deterministic_only": 0,
                "llm_only": 0,
                "both": 0
            }

            for f in all_findings:
                cat_name = f.category.value if hasattr(f.category, "value") else str(f.category)
                sev_name = f.severity.value if hasattr(f.severity, "value") else str(f.severity)
                by_category[cat_name] += 1
                by_severity[sev_name] += 1

                if f.source == AuditSource.DETERMINISTIC:
                    by_source["deterministic_only"] += 1
                elif f.source == AuditSource.LLM:
                    by_source["llm_only"] += 1
                elif f.source == AuditSource.BOTH:
                    by_source["both"] += 1

            total_elapsed = time.perf_counter() - t0
            summary = {
                "total_pairs": len(align_res.pairs),
                "aligned_pairs": len([p for p in align_res.pairs if not p.is_omission]),
                "omission_pairs": len([p for p in align_res.pairs if p.is_omission]),
                "findings_count": len(all_findings),
                "by_category": dict(by_category),
                "by_severity": dict(by_severity),
                "by_source": by_source,
                "elapsed_seconds": round(total_elapsed, 2)
            }

            report = AuditReportResponse(
                job_id=job_id,
                act_slug=act_slug,
                title=display_title,
                status=JobStatus.COMPLETED,
                fallback_used=fallback_used,
                summary=summary,
                findings=all_findings,
                aligned_pairs=aligned_pair_records,
                disclaimer=LEGAL_DISCLAIMER,
                metrics={
                    "latency_seconds": round(total_elapsed, 3),
                    "clauses_audited": len(align_res.pairs),
                    "throughput_clauses_per_sec": round(len(align_res.pairs) / max(0.01, total_elapsed), 1)
                }
            )

            with self._lock:
                self._reports[job_id] = report

            # --- Stage 7: COMPLETE (100%) ---
            self._update_stage(
                job_id=job_id,
                stage=JobStage.COMPLETE,
                percent=100.0,
                message="Audit successfully completed.",
                status=JobStatus.COMPLETED,
                fallback_used=fallback_used
            )

        except LegacyFontError as le:
            error_msg = (
                f"Hindi PDF encoding error: Legacy 8-bit ASCII font detected ({str(le)}). "
                "Official gazette must be encoded in standard Unicode Devanagari to guarantee auditing accuracy."
            )
            self._update_stage(
                job_id=job_id,
                stage=JobStage.FAILED,
                percent=100.0,
                message="Job failed due to non-Unicode legacy font.",
                status=JobStatus.FAILED,
                error=error_msg
            )
        except Exception as e:
            error_msg = f"Audit pipeline failed: {str(e)}"
            self._update_stage(
                job_id=job_id,
                stage=JobStage.FAILED,
                percent=100.0,
                message="Job execution failed.",
                status=JobStatus.FAILED,
                error=error_msg
            )


# Global singleton
job_manager = JobManager()
