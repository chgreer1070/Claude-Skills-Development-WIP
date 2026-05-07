#!/usr/bin/env python3
"""
Compare actual extraction manifest against per-fixture expectation sidecars.

Each sidecar YAML may include any subset of these checks:
  - document_type: <expected>
  - hierarchy_role: <expected>
  - effective_date: <expected or null>
  - title_must_contain: <substring>
  - parties_include: [<name>, ...]        # all must appear (case-sensitive)
  - parties_include_any: [<name>, ...]    # at least one must appear (substring, case-ins.)
  - parties_min_count: <int>
  - dba_aliases_min_count: <int>
  - parent_ref_must_be_nonnull: true
  - language_warning: <bool>
  - expected_language_warning: <bool>   # alias
  - expected_extraction_method: <str>
  - expected_status: <str>              # for error fixtures
  - document_type_observed_first_match: <str>  # informational, prints observed

Informational keys (notes, expected_behavior) are ignored for pass/fail.
"""
import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
EXP_DIR = ROOT / "fixtures" / "expected"


def check(actual, exp):
    """Return (passed: bool, failure_messages: list[str])."""
    fails = []

    # Status check (for error fixtures)
    if "expected_status" in exp:
        if actual.get("status") != exp["expected_status"]:
            fails.append(f"status={actual.get('status')!r} expected={exp['expected_status']!r}")
        return (len(fails) == 0), fails

    if "document_type" in exp:
        if actual.get("document_type") != exp["document_type"]:
            fails.append(
                f"document_type={actual.get('document_type')!r} expected={exp['document_type']!r}"
            )

    if "hierarchy_role" in exp:
        if actual.get("hierarchy_role") != exp["hierarchy_role"]:
            fails.append(
                f"hierarchy_role={actual.get('hierarchy_role')!r} expected={exp['hierarchy_role']!r}"
            )

    if "effective_date" in exp:
        if actual.get("effective_date") != exp["effective_date"]:
            fails.append(
                f"effective_date={actual.get('effective_date')!r} expected={exp['effective_date']!r}"
            )

    if "title_must_contain" in exp:
        title = actual.get("title") or ""
        if exp["title_must_contain"] not in title:
            fails.append(
                f"title={title!r} missing substring {exp['title_must_contain']!r}"
            )

    parties = actual.get("parties", {}).get("all_parties", []) or []
    if "parties_include" in exp:
        for needle in exp["parties_include"]:
            if not any(needle in p for p in parties):
                fails.append(f"parties missing {needle!r}; got {parties}")

    if "parties_include_any" in exp:
        needles = [n.lower() for n in exp["parties_include_any"]]
        hay = " ".join(parties).lower()
        if not any(n in hay for n in needles):
            fails.append(
                f"parties missing any of {exp['parties_include_any']}; got {parties}"
            )

    if "parties_min_count" in exp:
        if len(parties) < exp["parties_min_count"]:
            fails.append(f"parties count {len(parties)} < {exp['parties_min_count']}; got {parties}")

    if "dba_aliases_min_count" in exp:
        n = len(actual.get("dba_aliases") or [])
        if n < exp["dba_aliases_min_count"]:
            fails.append(f"dba_aliases count {n} < {exp['dba_aliases_min_count']}")

    if "parent_ref_must_be_nonnull" in exp and exp["parent_ref_must_be_nonnull"]:
        if not actual.get("parent_reference"):
            fails.append("parent_reference is null/empty")

    for key in ("language_warning", "expected_language_warning"):
        if key in exp:
            want = exp[key]
            got = actual.get("language_warning")
            if bool(got) != bool(want):
                fails.append(f"language_warning={got!r} expected={want!r}")

    if "expected_extraction_method" in exp:
        got = actual.get("extraction_method")
        if got != exp["expected_extraction_method"]:
            fails.append(f"extraction_method={got!r} expected={exp['expected_extraction_method']!r}")

    return (len(fails) == 0), fails


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--json", action="store_true", help="Emit JSON summary as last line")
    args = ap.parse_args()

    manifest = json.loads(Path(args.manifest).read_text())
    by_name = {}
    for c in manifest.get("contracts", []):
        by_name[Path(c["filename"]).stem] = c
    # Errored files are in extraction_summary.error_details; surface them as pseudo-contracts
    for e in manifest.get("extraction_summary", {}).get("error_details", []):
        name = Path(e["filename"]).stem
        by_name.setdefault(name, {"status": "error", "filename": e["filename"]})

    summary = {"pass": 0, "fail": 0, "skipped": 0, "missing_fixture_output": 0}
    rows = []
    for yml in sorted(EXP_DIR.glob("*.yaml")):
        stem = yml.stem
        exp = yaml.safe_load(yml.read_text()) or {}
        # Skip pure informational expectations (no checkable keys)
        checkable_keys = {
            "document_type", "hierarchy_role", "effective_date", "title_must_contain",
            "parties_include", "parties_include_any", "parties_min_count",
            "dba_aliases_min_count", "parent_ref_must_be_nonnull",
            "language_warning", "expected_language_warning",
            "expected_extraction_method", "expected_status",
        }
        if not (set(exp) & checkable_keys):
            summary["skipped"] += 1
            rows.append((stem, "INFO", []))
            continue

        actual = by_name.get(stem)
        if actual is None:
            summary["missing_fixture_output"] += 1
            rows.append((stem, "MISS", ["no manifest entry"]))
            continue

        ok, fails = check(actual, exp)
        if ok:
            summary["pass"] += 1
            rows.append((stem, "PASS", []))
        else:
            summary["fail"] += 1
            rows.append((stem, "FAIL", fails))

    # Print table
    print(f"{'FIXTURE':<45} {'RESULT':<6} DETAILS")
    print("-" * 90)
    for name, status, fails in rows:
        detail = "" if not fails else "; ".join(fails)
        print(f"{name:<45} {status:<6} {detail}")
    print("-" * 90)
    print(f"PASS={summary['pass']} FAIL={summary['fail']} INFO={summary['skipped']} MISS={summary['missing_fixture_output']}")

    if args.json:
        print("JSON_SUMMARY=" + json.dumps(summary))

    # Non-zero exit if any fail or miss
    sys.exit(0 if summary["fail"] == 0 and summary["missing_fixture_output"] == 0 else 1)


if __name__ == "__main__":
    main()
