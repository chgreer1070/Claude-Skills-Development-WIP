"""
Pytest regression tests for the contract-portfolio-organizer extraction pipeline.

These tests run the bundled extractor against the synthetic PDF fixtures
committed under tests/fixtures/pdfs/ and lock in the critical fixes (F1, F6, F7)
applied during the v4 stress test. See ../STRESS_TEST_REPORT.md for the full
audit.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRIPT = SKILL_DIR / "scripts" / "extract_and_classify.py"
FIXTURE_PDFS = SKILL_DIR / "tests" / "fixtures" / "pdfs"


@pytest.fixture(scope="module")
def manifest(tmp_path_factory):
    pytest.importorskip("fitz", reason="pymupdf not installed")
    out = tmp_path_factory.mktemp("manifest") / "manifest.json"
    res = subprocess.run(
        [sys.executable, str(SCRIPT), "--input-dir", str(FIXTURE_PDFS), "--output", str(out)],
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"extractor failed: {res.stderr}"
    return json.loads(out.read_text())


def by_name(manifest, filename):
    return next((c for c in manifest["contracts"] if c["filename"] == filename), None)


def test_extract_title_returns_three_tuple():
    """F1+F2: extract_title returns 3 elements (was a 4-tuple with a duplicate)."""
    pytest.importorskip("fitz", reason="pymupdf not installed")
    sys.path.insert(0, str(SKILL_DIR / "scripts"))
    import extract_and_classify

    text = "MASTER SERVICES AGREEMENT\n\nThis Agreement is entered into..."
    result = extract_and_classify.extract_title(text)
    assert len(result) == 3
    title, conf, short = result
    assert title and "MASTER" in title


def test_b01_clean_msa_extracts_own_date(manifest):
    """F6: 'is entered into as of <date>' must match (regression on baseline MSA)."""
    msa = by_name(manifest, "B01_clean_msa.pdf")
    assert msa is not None
    assert msa["effective_date"] == "2020-01-15"
    assert msa["document_type"] == "MSA"


def test_b03_sow_uses_own_date_not_parent_date(manifest):
    """F6: SOW must use its own 'entered into' date, not the parent MSA's 'dated' anchor."""
    sow = by_name(manifest, "B03_sow.pdf")
    assert sow is not None
    assert sow["effective_date"] == "2021-04-04"
    assert sow["document_type"] == "SOW"


def test_b04_amendment_uses_own_date(manifest):
    """F6: Amendment uses its own date, not the amended MSA's date."""
    amd = by_name(manifest, "B04_amendment_1.pdf")
    assert amd is not None
    assert amd["effective_date"] == "2022-06-01"
    assert amd["document_type"] == "Amendment"


def test_c06_ar_msa_uses_own_date(manifest):
    """F6: 2nd A&R MSA uses its own date, not the original MSA's."""
    ar = by_name(manifest, "C06_ar_msa_second.pdf")
    assert ar is not None
    assert ar["effective_date"] == "2023-02-02"
    assert ar["document_type"] == "A&R MSA"


def test_c07_change_order_classified(manifest):
    """F7: 'Change Order' is now in TYPE_MAP."""
    co = by_name(manifest, "C07_implicit_parent_date_only.pdf")
    assert co is not None
    assert co["document_type"] == "Change Order"
    assert co["hierarchy_role"] == "modifier"


def test_corrupt_pdf_does_not_crash_batch(manifest):
    """R04: corrupt PDF is logged and skipped; batch continues."""
    err_files = [e["filename"] for e in manifest["extraction_summary"]["error_details"]]
    assert "R04_corrupt_header.pdf" in err_files
    assert manifest["extraction_summary"]["successful"] >= 20


def test_baseline_classification_smoke(manifest):
    """Sanity: baseline fixtures classify correctly post-fix."""
    expectations = {
        "B01_clean_msa.pdf": "MSA",
        "B02_nda.pdf": "NDA",
        "B03_sow.pdf": "SOW",
        "B04_amendment_1.pdf": "Amendment",
        "B05_addendum.pdf": "Addendum",
    }
    for fname, expected_type in expectations.items():
        c = by_name(manifest, fname)
        assert c is not None, f"{fname} missing from manifest"
        assert c["document_type"] == expected_type, (
            f"{fname}: got document_type={c['document_type']!r}, expected {expected_type!r}"
        )
