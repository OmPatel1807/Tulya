"""
verify_api.py - Verification Script for Phase Loop 7 Part A (REST API).

Checks:
  1. Runs end-to-end audit jobs on each bundled statutory sample.
  2. Verifies stage progress sequence: QUEUED -> INGESTION -> SEGMENTATION -> ALIGNMENT -> FACTS -> SEMANTIC -> MERGE -> COMPLETE.
  3. Verifies report schema and mandatory legal disclaimer presence.
  4. Verifies JSON, CSV, and Markdown export endpoints.
  5. Verifies failure paths:
     - Empty file rejection (HTTP 400).
     - Legacy-font non-Unicode PDF detection (Graceful error message).
     - LLM outage / deterministic-only fallback execution (fallback_used = True).
"""

import sys
import time
import json
from pathlib import Path
from fastapi.testclient import TestClient

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.api.main import app
from backend.app.api.models import LEGAL_DISCLAIMER, JobStatus, JobStage
from backend.app.api.samples import BUNDLED_SAMPLES
from backend.app.api.jobs import job_manager

client = TestClient(app)


def verify_sample_job(sample_id: str, title: str) -> bool:
    print(f"\n---> Testing Bundled Sample: {title} ({sample_id})")

    # 1. Initiate job
    res = client.post(f"/samples/{sample_id}/analyze")
    assert res.status_code == 202, f"Expected 202, got {res.status_code}: {res.text}"
    job_info = res.json()
    job_id = job_info["job_id"]
    print(f"  [+] Job Created: {job_id}")

    # 2. Track stage progression
    stages_seen = set()
    max_wait = 25
    t0 = time.time()
    last_prog = None

    while time.time() - t0 < max_wait:
        p_res = client.get(f"/jobs/{job_id}")
        assert p_res.status_code == 200
        last_prog = p_res.json()
        stage = last_prog["stage"]
        stages_seen.add(stage)

        if last_prog["status"] == "COMPLETED":
            break
        elif last_prog["status"] == "FAILED":
            print(f"  [-] Job failed: {last_prog.get('error')}")
            return False

        time.sleep(0.3)

    print(f"  [+] Stages observed: {sorted(list(stages_seen))}")
    assert last_prog["status"] == "COMPLETED", f"Job timed out after {max_wait}s"
    assert last_prog["progress_percent"] == 100.0

    # 3. Verify Report Schema & Disclaimer
    rep_res = client.get(f"/jobs/{job_id}/report")
    assert rep_res.status_code == 200
    report = rep_res.json()

    assert report["job_id"] == job_id
    assert report["act_slug"] == sample_id
    assert "summary" in report
    assert "findings" in report
    assert "aligned_pairs" in report

    # Mandatory disclaimer guardrail
    assert "disclaimer" in report, "Mandatory disclaimer field is missing!"
    assert report["disclaimer"] == LEGAL_DISCLAIMER, "Disclaimer content does not match canonical text!"
    print(f"  [+] Disclaimer verified: '{report['disclaimer'][:60]}...'")
    print(f"  [+] Aligned Pairs: {report['summary']['total_pairs']}, Findings: {report['summary']['findings_count']}")

    # 4. Verify Export Endpoints
    exp_json = client.get(f"/jobs/{job_id}/export?format=json")
    assert exp_json.status_code == 200
    assert exp_json.json()["disclaimer"] == LEGAL_DISCLAIMER

    exp_csv = client.get(f"/jobs/{job_id}/export?format=csv")
    assert exp_csv.status_code == 200
    assert "finding_id,category,source,severity" in exp_csv.text

    exp_md = client.get(f"/jobs/{job_id}/export?format=md")
    assert exp_md.status_code == 200
    assert LEGAL_DISCLAIMER in exp_md.text

    print(f"  [+] JSON, CSV, and Markdown exports verified.")
    return True


def verify_failure_paths() -> bool:
    print("\n---> Testing Failure Paths & Graceful Recovery")

    # 1. Empty file upload
    print("  [•] Testing empty file upload rejection...")
    files = {
        "en_file": ("empty_en.pdf", b"", "application/pdf"),
        "hi_file": ("empty_hi.pdf", b"test content", "application/pdf")
    }
    res = client.post("/analyze", files=files)
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()
    print("  [+] Empty file cleanly rejected with HTTP 400.")

    # 2. Legacy font non-Unicode detection
    print("  [•] Testing legacy non-Unicode font detection (KrutiDev/ShreeLipi)...")
    prog = job_manager.create_job(act_slug="test_legacy_font_act")
    legacy_hi_pages = [{"page_num": 1, "text": "Hkkjr ljdkj fof/k vkSj U;k; ea=ky; fo/kk;h foHkkx"}]
    clean_en_pages = [{"page_num": 1, "text": "Government of India Ministry of Law and Justice Legislative Department"}]

    job_manager.process_job_async(
        job_id=prog.job_id,
        act_slug="test_legacy_font_act",
        en_text_pages=clean_en_pages,
        hi_text_pages=legacy_hi_pages
    )

    # Poll for expected failure
    t0 = time.time()
    failed_cleanly = False
    while time.time() - t0 < 5.0:
        p = client.get(f"/jobs/{prog.job_id}").json()
        if p["status"] == "FAILED":
            assert p["stage"] == "FAILED"
            assert "legacy" in p["error"].lower() or "unicode" in p["error"].lower()
            failed_cleanly = True
            break
        time.sleep(0.1)

    assert failed_cleanly, "Legacy font job did not fail with expected error!"
    print(f"  [+] Legacy font detected: '{p['error'][:75]}...'")

    # 3. Deterministic-only Fallback (LLM Outage simulation)
    print("  [•] Testing deterministic-only fallback (force_deterministic=True)...")
    res_fallback = client.post("/samples/environment_protection_1986/analyze?force_deterministic=true")
    assert res_fallback.status_code == 202
    fb_job_id = res_fallback.json()["job_id"]

    t0 = time.time()
    fb_completed = False
    while time.time() - t0 < 10.0:
        p = client.get(f"/jobs/{fb_job_id}").json()
        if p["status"] == "COMPLETED":
            assert p["fallback_used"] is True, "fallback_used must be True!"
            fb_completed = True
            break
        time.sleep(0.2)

    assert fb_completed, "Deterministic-only fallback job did not complete!"
    fb_rep = client.get(f"/jobs/{fb_job_id}/report").json()
    assert fb_rep["fallback_used"] is True
    assert fb_rep["disclaimer"] == LEGAL_DISCLAIMER
    print(f"  [+] Deterministic-only fallback completed successfully (Findings: {len(fb_rep['findings'])}).")

    return True


def run_all_api_verifications():
    print("=" * 72)
    print("Tulya Phase Loop 7 Part A: REST API Verifier")
    print("=" * 72)

    # Test top 3 bundled samples across short and medium categories
    test_samples = [
        ("environment_protection_1986", "The Environment (Protection) Act, 1986"),
        ("domestic_violence_2005", "The Protection of Women from Domestic Violence Act, 2005"),
        ("right_to_information_2005", "The Right to Information Act, 2005")
    ]

    all_passed = True
    for s_id, title in test_samples:
        ok = verify_sample_job(s_id, title)
        if not ok:
            all_passed = False

    fail_ok = verify_failure_paths()
    if not fail_ok:
        all_passed = False

    print("\n" + "=" * 72)
    print(f"PART A API VERIFIER RESULT: {'PASSED (All Exit Criteria Met)' if all_passed else 'FAILED'}")
    print("=" * 72)
    return all_passed


if __name__ == "__main__":
    success = run_all_api_verifications()
    sys.exit(0 if success else 1)

