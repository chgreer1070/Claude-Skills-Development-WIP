#!/usr/bin/env python3
"""
Build synthetic contract PDF fixtures for stress-testing extract_and_classify.py.

Each fixture is paired with an `expected/<stem>.yaml` sidecar describing the
expected extraction result, so diff_expected.py can compare actual output.
"""

import argparse
import os
from pathlib import Path

import yaml
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

FIX_DIR = Path(__file__).resolve().parent
PDF_DIR = FIX_DIR / "pdfs"
EXP_DIR = FIX_DIR / "expected"


def write_pdf(name: str, lines):
    """Write a simple text-layer PDF by drawing lines on canvas."""
    path = PDF_DIR / f"{name}.pdf"
    c = canvas.Canvas(str(path), pagesize=LETTER)
    width, height = LETTER
    y = height - 72
    for ln in lines:
        if y < 72:
            c.showPage()
            y = height - 72
        c.setFont("Helvetica", 11)
        c.drawString(72, y, ln[:110])
        y -= 14
    c.save()


def write_expected(name: str, data: dict):
    (EXP_DIR / f"{name}.yaml").write_text(yaml.safe_dump(data, sort_keys=False))


def write_empty_pdf(name: str):
    """PDF with no extractable text (white page)."""
    path = PDF_DIR / f"{name}.pdf"
    c = canvas.Canvas(str(path), pagesize=LETTER)
    c.showPage()
    c.save()


def write_corrupt_pdf(name: str):
    """Write a file with a broken PDF header."""
    path = PDF_DIR / f"{name}.pdf"
    path.write_bytes(b"%PDF-garbage\nnot a real pdf at all\n%%EOF\n")


# ---- Fixture definitions ----

def make_baseline():
    # B01 clean MSA
    write_pdf("B01_clean_msa", [
        "MASTER SERVICES AGREEMENT",
        "",
        "This Master Services Agreement is entered into as of January 15, 2020,",
        "between Acme Corporation and Flex Ltd., a Delaware corporation.",
        "Contract value of $1,000,000. Liability cap $500,000. Net 30 payment terms.",
        "Initial term of 5 years with auto-renewal.",
    ])
    write_expected("B01_clean_msa", {
        "document_type": "MSA",
        "hierarchy_role": "parent",
        "title_must_contain": "MASTER SERVICES AGREEMENT",
        "effective_date": "2020-01-15",
        "parties_include": ["Acme Corporation", "Flex Ltd."],
        "language_warning": False,
        "extraction_method": "native",
    })

    # B02 NDA
    write_pdf("B02_nda", [
        "NON-DISCLOSURE AGREEMENT",
        "",
        "This Non-Disclosure Agreement is entered into on March 3, 2021,",
        "between Globex Inc. and Flex Ltd.",
    ])
    write_expected("B02_nda", {
        "document_type": "NDA",
        "hierarchy_role": "standalone",
        "effective_date": "2021-03-03",
    })

    # B03 SOW
    write_pdf("B03_sow", [
        "STATEMENT OF WORK",
        "",
        "This Statement of Work is entered into on April 4, 2021,",
        "between Acme Corporation and Flex Ltd., pursuant to that certain",
        "Master Services Agreement dated January 15, 2020.",
    ])
    write_expected("B03_sow", {
        "document_type": "SOW",
        "hierarchy_role": "child",
        "effective_date": "2021-04-04",
        "parent_ref_must_be_nonnull": True,
    })

    # B04 Amendment No. 1
    write_pdf("B04_amendment_1", [
        "AMENDMENT NO. 1 TO MASTER SERVICES AGREEMENT",
        "",
        "This Amendment No. 1 is entered into on June 1, 2022,",
        "between Acme Corporation and Flex Ltd.",
        "This Amendment amends that certain Master Services Agreement dated January 15, 2020.",
    ])
    write_expected("B04_amendment_1", {
        "document_type": "Amendment",
        "hierarchy_role": "modifier",
        "effective_date": "2022-06-01",
        "parent_ref_must_be_nonnull": True,
    })

    # B05 Addendum
    write_pdf("B05_addendum", [
        "ADDENDUM",
        "",
        "This Addendum is entered into on July 7, 2022,",
        "between Acme Corporation and Flex Ltd.",
    ])
    write_expected("B05_addendum", {
        "document_type": "Addendum",
        "hierarchy_role": "child",
        "effective_date": "2022-07-07",
    })


def make_correctness_edges():
    # C01 conflict title: Amendment + NDA headings
    write_pdf("C01_conflict_amendment_nda", [
        "AMENDMENT AND NON-DISCLOSURE AGREEMENT",
        "",
        "This Agreement is entered into on May 5, 2022,",
        "between Acme Corporation and Flex Ltd.",
    ])
    write_expected("C01_conflict_amendment_nda", {
        "notes": "Title matches both Amendment and NDA patterns. First-match-wins gives Amendment; "
                 "skill offers no conflict detection.",
        "document_type_observed_first_match": "Amendment",
        "expected_behavior": "Flag ambiguous classification",
    })

    # C02 entity collision: Inc vs LLC (same root name)
    write_pdf("C02_entity_collision_inc_llc", [
        "SUPPLY AGREEMENT",
        "",
        "This Supply Agreement is entered into on August 8, 2021,",
        "between Smith & Associates Inc. and Smith & Associates LLC.",
    ])
    write_expected("C02_entity_collision_inc_llc", {
        "notes": "normalize_entity_name strips 'inc.' and 'llc'; post-norm both = 'Smith & Associates'. "
                 "Fuzzy resolution will merge the two distinct entities.",
        "parties_include_any": ["Smith & Associates Inc", "Smith & Associates LLC"],
        "expected_behavior": "Keep distinct; likely merged incorrectly.",
    })

    # C03 Spanish legalese (many English loanwords)
    write_pdf("C03_spanish_legalese", [
        "CONTRATO DE SERVICIOS",
        "",
        "Este contrato de servicios entre Acme Corporation y Flex Ltd.",
        "se celebra en la fecha del 10 de septiembre de 2021.",
        "El party prestador se obliga a cumplir con los terms del agreement.",
        "The parties shall execute this contract in good faith.",
    ])
    write_expected("C03_spanish_legalese", {
        "notes": "Spanish with English loanwords; detect_language may return False (treats as English).",
        "expected_language_warning": True,
    })

    # C04 NDA with 'amendment' in body recital
    write_pdf("C04_nda_body_amendment_word", [
        "NON-DISCLOSURE AGREEMENT",
        "",
        "This Non-Disclosure Agreement is entered into on November 11, 2022,",
        "between Globex Inc. and Flex Ltd.",
        "The parties acknowledge that any amendment to this agreement must be in writing.",
    ])
    write_expected("C04_nda_body_amendment_word", {
        "document_type": "NDA",
        "hierarchy_role": "standalone",
        "notes": "Body text contains 'amendment'; header-first classification should still pick NDA.",
    })

    # C05 amendment and waiver compound
    write_pdf("C05_amendment_and_waiver", [
        "AMENDMENT AND WAIVER",
        "",
        "This Amendment and Waiver is entered into on December 12, 2023,",
        "between Acme Corporation and Flex Ltd.",
    ])
    write_expected("C05_amendment_and_waiver", {
        "document_type": "Amendment",
        "hierarchy_role": "modifier",
    })

    # C06 A&R chain: 2nd A&R MSA
    write_pdf("C06_ar_msa_second", [
        "SECOND AMENDED AND RESTATED MASTER SERVICES AGREEMENT",
        "",
        "This Second Amended and Restated Master Services Agreement is entered into",
        "on February 2, 2023, between Acme Corporation and Flex Ltd.",
        "This Agreement amends and restates that certain Master Services Agreement",
        "dated January 15, 2020.",
    ])
    write_expected("C06_ar_msa_second", {
        "document_type": "A&R MSA",
        "hierarchy_role": "parent_superseding",
        "effective_date": "2023-02-02",
    })

    # C07 implicit parent (date-only reference)
    write_pdf("C07_implicit_parent_date_only", [
        "CHANGE ORDER",
        "",
        "This Change Order is entered into on May 5, 2022,",
        "between Acme Corporation and Flex Ltd.",
        "Reference: agreement of January 15, 2020.",
    ])
    write_expected("C07_implicit_parent_date_only", {
        "notes": "Parent referenced only by date, no anchor phrase. Scoring rubric 'implicit link' is undefined.",
        "document_type": "Change Order",
        "hierarchy_role": "modifier",
    })

    # C08 body-only parent type (no header; parent skipped by design)
    write_pdf("C08_no_header_msa_body", [
        "by:",
        "",
        "This document is a Master Services Agreement between Acme Corporation",
        "and Flex Ltd. Effective as of June 6, 2021.",
    ])
    write_expected("C08_no_header_msa_body", {
        "notes": "No usable header (rejected 'by:' line). Body mentions MSA but parent types are skipped "
                 "in body-pass per patch v4-7.",
        "document_type": None,
    })


def make_robustness():
    # R01 unicode customer name
    write_pdf("R01_unicode_party", [
        "SUPPLY AGREEMENT",
        "",
        "This Supply Agreement is entered into on September 9, 2021,",
        "between Toyota Motor Corporation (Kabushiki-gaisha Toyota) and Flex Ltd.",
    ])
    write_expected("R01_unicode_party", {
        "notes": "Folder naming should handle unicode customer names without collision.",
    })

    # R02 RTL Arabic-style title (transliteration, since reportlab default font lacks Arabic glyphs)
    write_pdf("R02_rtl_title_latin_transliteration", [
        "ATTIFAQIYAT AL-TAWRID",
        "(Supply Agreement - translit.)",
        "",
        "This Supply Agreement is entered into on October 10, 2021,",
        "between Riyadh Holding and Flex Ltd.",
    ])
    write_expected("R02_rtl_title_latin_transliteration", {
        "notes": "Non-English title; skill should detect language_warning on full-Arabic version; "
                 "transliteration with English body will not trigger warning.",
    })

    # R03 empty text layer
    write_empty_pdf("R03_empty_text_layer")
    write_expected("R03_empty_text_layer", {
        "notes": "No text layer; script should flag extraction_method=ocr_needed.",
        "expected_extraction_method": "ocr_needed",
    })

    # R04 corrupt PDF
    write_corrupt_pdf("R04_corrupt_header")
    write_expected("R04_corrupt_header", {
        "notes": "Corrupt PDF header; must not crash batch; status=error expected.",
        "expected_status": "error",
    })

    # R05 multi-party (4 parties)
    write_pdf("R05_multi_party_four", [
        "COOPERATION AGREEMENT",
        "",
        "This Cooperation Agreement is entered into on November 11, 2021,",
        "by and among Acme Corporation, Globex Inc., Initech Ltd., and Flex Ltd.",
    ])
    write_expected("R05_multi_party_four", {
        "document_type": "Cooperation Agreement",
        "hierarchy_role": "parent",
        "parties_min_count": 3,
    })

    # R06 DBA alias chain
    write_pdf("R06_dba_alias", [
        "LETTER AGREEMENT",
        "",
        "This Letter Agreement is entered into on December 1, 2021,",
        "between Acme Corporation d/b/a Acme Trading and Flex Ltd.",
    ])
    write_expected("R06_dba_alias", {
        "document_type": "Letter Agreement",
        "hierarchy_role": "ancillary",
        "dba_aliases_min_count": 1,
    })

    # R07 missing effective_date
    write_pdf("R07_missing_effective_date", [
        "PROFESSIONAL SERVICES AGREEMENT",
        "",
        "This Professional Services Agreement is between Acme Corporation and Flex Ltd.",
        "The parties agree to the following terms and conditions.",
    ])
    write_expected("R07_missing_effective_date", {
        "document_type": "PSA",
        "hierarchy_role": "parent",
        "effective_date": None,
    })


def make_security():
    # S01 XSS-style title
    write_pdf("S01_xss_title", [
        "<SCRIPT>ALERT(1)</SCRIPT> AGREEMENT",
        "",
        "This Agreement is entered into on January 1, 2023,",
        "between Acme Corporation and Flex Ltd.",
    ])
    write_expected("S01_xss_title", {
        "notes": "Title contains HTML/script-like text. Visualization hierarchy.html uses textContent for title "
                 "(safe) but tooltip template uses innerHTML with ${event.title} (XSS).",
    })

    # S02 path traversal in party name
    write_pdf("S02_path_traversal_party", [
        "SUPPLY AGREEMENT",
        "",
        "This Supply Agreement is entered into on February 2, 2023,",
        "between ../../etc/passwd Inc. and Flex Ltd.",
    ])
    write_expected("S02_path_traversal_party", {
        "notes": "Party name contains path-traversal. Phase 5 folder naming must sanitize.",
    })

    # S03 badge_class style injection (simulated via title-like marker)
    write_pdf("S03_badge_class_payload", [
        "NON-DISCLOSURE AGREEMENT",
        "",
        "This Agreement is entered into on March 3, 2023,",
        "between Acme Corp. and Flex Ltd.",
        "Marker payload: bad badge-class injection x\"><script>",
    ])
    write_expected("S03_badge_class_payload", {
        "notes": "If downstream code populates node.badge_class from extracted fields, ensure sanitize.",
    })

    # S04 SVG-injection
    write_pdf("S04_svg_title_payload", [
        "</text><circle r=\"999\"/>AGREEMENT",
        "",
        "This Agreement is entered into on April 4, 2023,",
        "between Acme Corporation and Flex Ltd.",
    ])
    write_expected("S04_svg_title_payload", {
        "notes": "Title contains SVG-breaking markup. SVG renderer truncates titles to 40 chars; still, no escape.",
    })

    # S05 very long title (10KB)
    long_title = "SUPER " * 2000 + "AGREEMENT"
    write_pdf("S05_long_title", [
        long_title,
        "",
        "This Agreement is entered into on May 5, 2023,",
        "between Acme Corporation and Flex Ltd.",
    ])
    write_expected("S05_long_title", {
        "notes": "Extremely long title line (reportlab truncates at draw time; parser still sees via text extraction).",
    })


def make_scale(n: int):
    """Generate N contract PDFs with a controlled parent/child/amendment mix."""
    import calendar
    types = [
        ("MSA", "MASTER SERVICES AGREEMENT", "parent"),
        ("SOW", "STATEMENT OF WORK", "child"),
        ("NDA", "NON-DISCLOSURE AGREEMENT", "standalone"),
        ("Amendment", "AMENDMENT NO. 1 TO MSA", "modifier"),
    ]
    for i in range(n):
        t = types[i % len(types)]
        m = (i % 12) + 1
        d = (i % 28) + 1
        y = 2018 + (i % 8)
        write_pdf(f"SCALE_{i:05d}_{t[0]}", [
            t[1],
            "",
            f"This {t[1].title()} is entered into on {calendar.month_name[m]} {d}, {y},",
            f"between Acme Corporation and Flex Ltd. (batch {i}).",
            "Contract value $1,000,000. Net 30. Liability cap $500,000.",
        ])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scale", type=int, default=0, help="Also generate N scale fixtures (0 = skip)")
    ap.add_argument("--scale-only", action="store_true", help="Only generate scale fixtures; skip correctness set")
    args = ap.parse_args()

    PDF_DIR.mkdir(parents=True, exist_ok=True)
    EXP_DIR.mkdir(parents=True, exist_ok=True)

    if not args.scale_only:
        make_baseline()
        make_correctness_edges()
        make_robustness()
        make_security()

    if args.scale > 0:
        make_scale(args.scale)

    # Count what we produced
    n_pdfs = len(list(PDF_DIR.glob("*.pdf")))
    n_exp = len(list(EXP_DIR.glob("*.yaml")))
    print(f"Generated {n_pdfs} PDF fixtures and {n_exp} expectation sidecars.")
    print(f"  PDFs:       {PDF_DIR}")
    print(f"  Expected:   {EXP_DIR}")


if __name__ == "__main__":
    main()
