"""
test_api.py - Unit and Integration Tests for Tulya REST API.

Tests:
  - /samples catalog listing
  - /analyze job creation and stage progression
  - /jobs/{id} polling and status validation
  - /jobs/{id}/report schema validation and mandatory disclaimer presence
  - /jobs/{id}/export for json, csv, and md formats
  - Graceful failure paths (empty file, invalid sample, missing job)
  - Deterministic-only fallback execution
"""

import time
import pytest
from fastapi.testclient import TestClient

from backend.app.api.main import app
from backend.app.api.models import LEGAL_DISCLAIMER

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_get_samples_catalog():
    response = client.get("/samples")
    assert response.status_code == 200
    data = response.json()
    assert "samples" in data
    assert data["total"] >= 3

    slugs = [s["slug"] for s in data["samples"]]
    assert "domestic_violence_2005" in slugs
    assert "right_to_information_2005" in slugs
    assert "environment_protection_1986" in slugs


def test_job_not_found():
    response = client.get("/jobs/non_existent_job_12345")
    assert response.status_code == 404


def test_empty_file_upload_rejected():
    files = {
        "en_file": ("test_en.pdf", b"", "application/pdf"),
        "hi_file": ("test_hi.pdf", b"dummy content", "application/pdf")
    }
    response = client.post("/analyze", files=files)
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


def test_missing_files_and_sample_rejected():
    response = client.post("/analyze", data={})
    assert response.status_code == 400


def test_analyze_bundled_sample_end_to_end():
    # Submit job for a short act with deterministic fallback
    response = client.post("/samples/environment_protection_1986/analyze?force_deterministic=true")
    assert response.status_code == 202
    job_data = response.json()
    job_id = job_data["job_id"]
    assert job_id.startswith("job_")
    assert job_data["status"] in ["PENDING", "PROCESSING"]

    # Poll until completed
    max_wait = 20
    start_time = time.time()
    completed = False
    last_prog = None

    while time.time() - start_time < max_wait:
        prog_res = client.get(f"/jobs/{job_id}")
        assert prog_res.status_code == 200
        last_prog = prog_res.json()
        if last_prog["status"] == "COMPLETED":
            completed = True
            break
        elif last_prog["status"] == "FAILED":
            pytest.fail(f"Job failed unexpectedly: {last_prog.get('error')}")
        time.sleep(0.5)

    assert completed, f"Job did not complete within {max_wait}s. Last state: {last_prog}"
    assert last_prog["stage"] == "COMPLETE"
    assert last_prog["progress_percent"] == 100.0

    # 1. Fetch full report
    report_res = client.get(f"/jobs/{job_id}/report")
    assert report_res.status_code == 200
    report = report_res.json()

    # Schema checks
    assert report["job_id"] == job_id
    assert report["act_slug"] == "environment_protection_1986"
    assert "summary" in report
    assert "findings" in report
    assert report["fallback_used"] is True

    # Critical Guardrail Check: Mandatory disclaimer presence
    assert "disclaimer" in report
    assert report["disclaimer"] == LEGAL_DISCLAIMER

    # 2. Test JSON export
    export_json = client.get(f"/jobs/{job_id}/export?format=json")
    assert export_json.status_code == 200
    assert export_json.headers["content-type"] == "application/json"
    exported_data = export_json.json()
    assert exported_data["disclaimer"] == LEGAL_DISCLAIMER

    # 3. Test CSV export
    export_csv = client.get(f"/jobs/{job_id}/export?format=csv")
    assert export_csv.status_code == 200
    assert "text/csv" in export_csv.headers["content-type"]
    csv_text = export_csv.text
    assert "finding_id,category,source,severity" in csv_text

    # 4. Test Markdown export
    export_md = client.get(f"/jobs/{job_id}/export?format=md")
    assert export_md.status_code == 200
    assert "text/markdown" in export_md.headers["content-type"]
    md_text = export_md.text
    assert "# Tulya Audit Report" in md_text
    assert LEGAL_DISCLAIMER in md_text

