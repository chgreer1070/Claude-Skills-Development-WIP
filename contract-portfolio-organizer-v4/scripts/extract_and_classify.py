#!/usr/bin/env python3
"""
Contract Portfolio Organizer - PDF Extraction & Classification Engine

A deterministic pipeline for extracting structured data from contract PDFs
and classifying them into hierarchical roles. Handles text extraction,
entity recognition, party extraction, date parsing, and relationship mapping.

Installation (inside a virtualenv):
    python3 -m venv .venv && source .venv/bin/activate
    pip install pymupdf              # required
    pip install pytesseract          # optional: needed only for OCR fallback
    # NOTE: `difflib` is part of the Python stdlib; do NOT `pip install` it.

Usage:
    python extract_and_classify.py --input-dir ./pdfs --output manifest.json [--verbose]
"""

import argparse
import json
import logging
import os
import re
import sys
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import fitz
except ImportError:
    print("ERROR: pymupdf not installed. Install with: pip install pymupdf")
    sys.exit(1)

try:
    import pytesseract  # noqa: F401  (optional OCR dependency; presence probe only)
    HAS_PYTESSERACT = True
except ImportError:
    HAS_PYTESSERACT = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# English language keywords for language detection
ENGLISH_KEYWORDS = {
    "the", "of", "and", "to", "in", "for", "is", "that",
    "this", "with", "by", "or", "an", "be", "as", "at",
    "from", "which", "shall", "agreement", "party", "parties"
}

# Document type classification patterns (priority order - DO NOT REORDER)
TYPE_MAP = [
    (r'equipment\s+bailment', 'Equipment Bailment', 'child_l2'),
    # Amendment patterns (extensive)
    (r'(?:amendment\s+no\.?\s*\d+|(?:first|second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|thirteenth|fourteenth|fifteenth|sixteenth|seventeenth|eighteenth|nineteenth|twentieth|twenty[- ]?first|twenty[- ]?second|twenty[- ]?third|twenty[- ]?fourth|twenty[- ]?fifth|twenty[- ]?sixth|twenty[- ]?seventh|twenty[- ]?eighth|twenty[- ]?ninth|thirtieth|\d+(?:st|nd|rd|th))\s+amendment|amendment\s+and\s+(?:waiver|restatement|release)|amendment\s+letter|amendment\s+no\.?\s*[a-z])', 'Amendment', 'modifier'),
    (r'amended\s+and\s+restated', 'A&R MSA', 'parent_superseding'),
    (r'(?:novation|assignment)\s+agreement|assignment\s+and\s+assumption', 'Assignment / Novation', 'modifier'),
    (r'change\s+order|(?<!\w)modification\s+agreement(?!\w)', 'Change Order', 'modifier'),
    (r'settlement|mutual\s+release', 'Settlement / Release', 'ancillary'),
    (r'quality\s+agreement', 'Quality Agreement', 'child'),
    (r'termination\s+agreement|contract\s+termination', 'Termination Agreement', 'ancillary_terminal'),
    (r'letter\s+of\s+authorization', 'LOA', 'ancillary'),
    (r'letter\s+of\s+intent', 'LOI', 'ancillary'),
    (r'asset\s+purchase\s+agreement', 'APA', 'ancillary'),
    (r'non-disclosure\s+agreement|confidentiality\s+agreement(?!\s+per)|confidential\s+disclosure\s+agreement|(?<!\w)(?:nda|cda)(?!\w)', 'NDA', 'standalone'),
    (r'consignment\s+addendum', 'Addendum', 'child'),
    (r'(?<!\w)addendum(?!\w)', 'Addendum', 'child'),
    (r'sub-statement\s+of\s+work|sub-sow', 'Sub-SOW', 'child_l2'),
    (r'statement\s+of\s+work|(?<!\w)sow(?!\w)', 'SOW', 'child'),
    (r'purchase\s+order\s+terms|purchase\s+order\s+agreement', 'PO Terms', 'child'),
    (r'letter\s+agreement', 'Letter Agreement', 'ancillary'),
    (r'interim\s+agreement', 'Interim Agreement', 'parent'),
    (r'(?:manufacturing|master)\s+services\s+agreement', 'MSA', 'parent'),
    (r'professional\s+services\s+agreement', 'PSA', 'parent'),
    (r'(?:master\s+)?supply\s+agreement', 'Supply Agreement', 'parent'),
    (r'framework\s+agreement', 'Framework Agreement', 'parent'),
    (r'general\s+terms\s+and\s+conditions', 'GTC', 'parent'),
    (r'sourcing\s+agreement', 'Sourcing Agreement', 'parent'),
    (r'cooperation\s+agreement', 'Cooperation Agreement', 'parent'),
]

# Flex entities to identify
FLEX_ENTITIES = {"flex", "flextronics", "multek", "nextracker"}

# Legal entity suffixes to normalize
LEGAL_SUFFIXES = {"inc.", "ltd.", "llc", "corp.", "co.", "s.p.a.", "gmbh", "b.v.", "plc"}


def extract_text_from_pdf(pdf_path: str, max_pages: int = 3) -> Tuple[str, str]:
    """
    Extract text from the first N pages of a PDF.

    Args:
        pdf_path: Path to PDF file
        max_pages: Maximum number of pages to extract

    Returns:
        Tuple of (full_text, extraction_method) where method is "native" or "ocr_needed"
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(min(max_pages, len(doc))):
            page = doc[page_num]
            text += page.get_text()
        doc.close()

        if len(text.strip()) < 100:
            logger.warning(f"Low text extraction ({len(text)} chars) from {pdf_path}")
            return text, "ocr_needed"

        return text, "native"
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}")
        return "", "error"


def detect_language(text: str) -> bool:
    """
    Detect if text is primarily English.

    Args:
        text: Text to analyze

    Returns:
        True if non-English, False if English detected
    """
    if not text:
        return False

    text_lower = text.lower()
    words = re.findall(r'\b\w+\b', text_lower)

    if not words:
        return False

    english_count = sum(1 for word in words if word in ENGLISH_KEYWORDS)
    english_ratio = english_count / len(words)

    return english_ratio < 0.40


def extract_title(text: str) -> Tuple[Optional[str], float, Optional[str]]:
    """
    Extract document title from first 12 raw lines.
    Handles both ALL-CAPS and Title-Case formats.

    Args:
        text: Full document text

    Returns:
        Tuple of (title, confidence, short_header). `short_header` is the
        header text up to (but not including) the preamble line that starts
        with "This " (e.g. "This Agreement is entered into..."); if no such
        line is seen, `short_header == title`.
    """
    lines = text.split('\n')[:12]
    empty_count = 0

    # Reject patterns
    reject_starts = {"this ", "confidential", "page "}
    reject_patterns = [r'^[_\s]+$', r'^by:', r'^___+']

    title_parts = []

    for line in lines:
        stripped = line.strip()

        if not stripped:
            empty_count += 1
            if empty_count >= 8:
                break
            continue

        empty_count = 0

        # Check reject patterns
        if any(stripped.lower().startswith(r) for r in reject_starts):
            break
        if any(re.match(p, stripped) for p in reject_patterns):
            continue

        # Check if all-caps or title-case
        alpha_count = sum(1 for c in stripped if c.isalpha())
        if alpha_count == 0:
            continue

        upper_count = sum(1 for c in stripped if c.isupper())
        upper_ratio = upper_count / alpha_count

        # ALL-CAPS detection: >60% uppercase
        if upper_ratio > 0.60:
            title_parts.append(stripped)
            if len(title_parts) == 1:
                confidence = 0.95
        else:
            # Title-Case detection: >50% of 3+ char words capitalized (and not ALL-CAPS)
            words = re.findall(r'\b\w{3,}\b', stripped)
            if words:
                cap_words = sum(1 for w in words if w[0].isupper())
                cap_ratio = cap_words / len(words)

                if cap_ratio > 0.50 and upper_ratio < 0.60:
                    title_parts.append(stripped)
                    if len(title_parts) == 1:
                        confidence = 0.70
                else:
                    break
            else:
                break

        # Stop at "This " line (preamble start)
        if stripped.startswith("This "):
            break

    if not title_parts:
        return None, 0.0, None

    full_header = " ".join(title_parts)

    # short_header: header text preceding the first "This ..." preamble line
    # in the raw scan window. The outer loop already breaks on "This " before
    # adding to title_parts, so we must scan the raw lines again to find the
    # true preamble boundary. If no preamble line is found within the scan
    # window, short_header equals full_header.
    short_header = full_header
    collected: List[str] = []
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.lower().startswith("this "):
            if collected:
                short_header = " ".join(collected)
            break
        if stripped in title_parts:
            collected.append(stripped)

    return full_header, confidence, short_header


def extract_dba_aliases(text: str) -> List[Dict[str, str]]:
    """
    Extract d/b/a, f/k/a, and other alias patterns.

    Args:
        text: Document text

    Returns:
        List of {original, alias, type} dicts
    """
    aliases = []

    # Pattern: "Company Name d/b/a Trade Name"
    dba_pattern = r'([A-Z][A-Za-z0-9\s,&.()]*?)\s+(?:d/b/a|doing\s+business\s+as)\s+([A-Z][A-Za-z0-9\s,&.()]*?)(?:\s|,|$)'
    for match in re.finditer(dba_pattern, text, re.IGNORECASE):
        aliases.append({
            "original": match.group(1).strip(),
            "alias": match.group(2).strip(),
            "type": "dba"
        })

    # Pattern: "Company Name f/k/a Former Name"
    fka_pattern = r'([A-Z][A-Za-z0-9\s,&.()]*?)\s+(?:f/k/a|formerly\s+known\s+as)\s+([A-Z][A-Za-z0-9\s,&.()]*?)(?:\s|,|$)'
    for match in re.finditer(fka_pattern, text, re.IGNORECASE):
        aliases.append({
            "original": match.group(1).strip(),
            "alias": match.group(2).strip(),
            "type": "fka"
        })

    return aliases


def extract_dates(text: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Extract effective date, expiration date, term info, and amendment date.

    Args:
        text: Document text

    Returns:
        Tuple of (effective_date, expiration_date, term_info, amendment_date)
    """
    effective_date = None
    expiration_date = None
    term_info = None
    amendment_date = None

    # Effective date patterns. Order matters: the current document's own
    # "entered into on ..." / "effective as of ..." must beat the bare
    # "dated ..." anchor, because "dated" frequently appears inside a
    # parent-agreement reference (e.g. "pursuant to that certain MSA dated
    # January 15, 2020") and would otherwise hijack the effective_date of
    # child / amendment / A&R documents.
    effective_patterns = [
        r'effective\s+(?:as\s+of\s+)?([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        # `entered into` may be followed by `on`, `as of`, or nothing. The
        # baseline "is entered into as of January 15, 2020" pattern is very
        # common in practice and previously fell through.
        r'entered\s+into\s+(?:(?:on|as\s+of)\s+)?([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'dated\s+(?:as\s+of\s+)?([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]

    for pattern in effective_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            effective_date = normalize_date(match.group(1))
            break

    # Expiration/term patterns
    term_patterns = [
        r'initial\s+term\s+of\s+([^,.\n]+)',
        r'term\s+of\s+([^,.\n]+)',
        r'shall\s+expire\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'termination\s+date\s+of\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
        r'valid\s+until\s+([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})',
    ]

    for pattern in term_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            term_text = match.group(1).strip()
            term_info = term_text[:100]  # Cap at 100 chars

            # Try to extract expiration date from term text
            date_match = re.search(r'([A-Za-z]+ \d{1,2},? \d{4}|\d{1,2}[/-]\d{1,2}[/-]\d{4})', term_text)
            if date_match:
                expiration_date = normalize_date(date_match.group(1))
            break

    # Amendment date from filename pattern (_MM-YYYY)
    # This is placeholder; would need filename context

    return effective_date, expiration_date, term_info, amendment_date


def normalize_date(date_str: str) -> str:
    """
    Normalize date string to YYYY-MM-DD format.

    Args:
        date_str: Date string in various formats

    Returns:
        Normalized date string or original if unparseable
    """
    date_str = date_str.strip()

    # Try common formats
    formats = [
        '%B %d, %Y',  # January 1, 2020
        '%B %d %Y',   # January 1 2020
        '%m/%d/%Y',   # 01/01/2020
        '%m-%d-%Y',   # 01-01-2020
        '%d/%m/%Y',   # 01/01/2020 (EU)
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue

    return date_str


def extract_parties(text: str) -> Tuple[List[str], List[str], List[str]]:
    """
    Extract parties from preamble.

    Args:
        text: Document text

    Returns:
        Tuple of (all_parties, customer_candidates, flex_entities)
    """
    all_parties = []
    customer_candidates = []
    flex_entities = []

    # Simple pattern: "between X and Y" or "by and among X, Y, and Z"
    preamble = text[:2000]  # Check first 2000 chars

    # Pattern: "between X and Y"
    between_match = re.search(r'between\s+([A-Z][^,]*?)\s+and\s+([A-Z][^,]*?)(?:\s+and|,|\.|;)', preamble, re.IGNORECASE)
    if between_match:
        all_parties.extend([between_match.group(1).strip(), between_match.group(2).strip()])

    # Pattern: "by and among X, Y, and Z"
    among_match = re.search(r'(?:by\s+and\s+)?among\s+([^.;:]+?)(?:\.|;|:)', preamble, re.IGNORECASE)
    if among_match:
        parties_text = among_match.group(1)
        parties = re.split(r',\s+and\s+|,\s+|;\s+', parties_text)
        all_parties.extend([p.strip() for p in parties if p.strip()])

    # Deduplicate
    all_parties = list(dict.fromkeys(all_parties))

    # Separate into flex and customer candidates
    for party in all_parties:
        party_lower = party.lower()
        if any(flex in party_lower for flex in FLEX_ENTITIES):
            flex_entities.append(party)
        else:
            customer_candidates.append(party)

    return all_parties, customer_candidates, flex_entities


def extract_financial_terms(text: str) -> Dict[str, Optional[str]]:
    """
    Extract financial terms and payment conditions.

    Args:
        text: Document text

    Returns:
        Dict with contract_value, liability_cap, payment_terms
    """
    contract_value = None
    liability_cap = None
    payment_terms = None

    # Search for dollar amounts near keywords
    search_context = text[:5000]  # Search first 5000 chars

    # Contract value patterns
    value_pattern = r'(?:contract\s+value|total\s+value|aggregate)\s+(?:of\s+)?(?:USD|US\$|\$)[\s]*([0-9,]+(?:\.\d{2})?)'
    match = re.search(value_pattern, search_context, re.IGNORECASE)
    if match:
        contract_value = match.group(1)

    # Liability cap patterns
    cap_pattern = r'(?:liability\s+cap|limitation\s+of\s+liability|not\s+to\s+exceed)\s+(?:USD|US\$|\$)[\s]*([0-9,]+(?:\.\d{2})?)'
    match = re.search(cap_pattern, search_context, re.IGNORECASE)
    if match:
        liability_cap = match.group(1)

    # Payment terms patterns
    payment_pattern = r'(?:net\s+\d+|payment\s+terms)[:\s]+([^.\n]{1,50})'
    match = re.search(payment_pattern, search_context, re.IGNORECASE)
    if match:
        payment_terms = match.group(1).strip()

    return {
        "contract_value": contract_value,
        "liability_cap": liability_cap,
        "payment_terms": payment_terms
    }


def extract_parent_reference(text: str) -> Tuple[Optional[str], float]:
    """
    Extract parent document reference with confidence scoring.

    Args:
        text: Document text

    Returns:
        Tuple of (parent_reference, confidence)
    """
    preamble = text[:3000]  # Search first 3000 chars

    # Date capture patterns
    D = r'.{5,100}?dated\s+[^()]*?\d{4}'
    E = r'.{5,100}?(?:effective\s+(?:as\s+of\s+)?|entered\s+into\s+(?:on\s+)?)[^()]*?\d{4}'

    patterns = [
        (r'amends\s+that\s+certain\s+(?:' + D + '|' + E + r')', 0.95),
        (r'amends\s+the\s+(?:' + D + '|' + E + r')', 0.95),
        (r'entered\s+into\s+that\s+certain\s+(?:' + D + '|' + E + r')', 0.90),
        (r'under\s+(?:and\s+governed\s+by|that\s+certain)\s+(?:' + D + '|' + E + r')', 0.85),
        (r'pursuant\s+to\s+(?:Section\s+\w+\s+of\s+)?that\s+certain\s+(?:' + D + '|' + E + r')', 0.90),
        (r'pursuant\s+to\s+the\s+(?:' + D + '|' + E + r')', 0.80),
        (r'subject\s+to\s+(?:that\s+certain\s+)?(?:' + D + '|' + E + r')', 0.75),
        (r'governed\s+by\s+that\s+certain\s+(?:' + D + '|' + E + r')', 0.70),
        (r'supplement\s+to\s+that\s+certain\s+(?:' + D + '|' + E + r')', 0.85),
        (r'in\s+connection\s+with\s+(?:the|that\s+certain)?\s+(?:' + D + '|' + E + r')', 0.70),
        (r'related\s+to\s+the\s+(?:' + D + '|' + E + r')', 0.70),
        (r'supersedes\s+and\s+replaces\s+the\s+(?:' + D + '|' + E + r')', 0.85),
        (r'parties\s+to\s+that\s+certain\s+(?:' + D + '|' + E + r')', 0.80),
    ]

    for pattern, confidence in patterns:
        match = re.search(pattern, preamble, re.IGNORECASE)
        if match:
            ref = match.group(0).strip()
            if len(ref) <= 120:
                return ref, confidence

    # Fallback: capture up to parenthesis
    fallback_match = re.search(r'[Aa]mends?|[Pp]ursuant\s+to|[Rr]elated\s+to\s+([^()]+)', preamble)
    if fallback_match:
        ref = fallback_match.group(0).strip()
        if len(ref) <= 120:
            return ref, 0.60

    return None, 0.0


def classify_document(short_header: Optional[str], text: str) -> Tuple[Optional[str], str]:
    """
    Classify document type using two-pass approach.

    Args:
        short_header: Short header text
        text: Full document text

    Returns:
        Tuple of (document_type, hierarchy_role)
    """
    search_text = short_header.lower() if short_header else ""

    # Pass 1: match against short_header
    for pattern, doc_type, role in TYPE_MAP:
        if re.search(pattern, search_text, re.IGNORECASE):
            return doc_type, role

    # Pass 2: fall back to first 2000 chars body text
    body_text = text[:2000].lower()
    for pattern, doc_type, role in TYPE_MAP:
        if re.search(pattern, body_text, re.IGNORECASE):
            # Skip parent types if no header found
            if not short_header and role.startswith('parent'):
                continue
            return doc_type, role

    return None, "unknown"


def normalize_entity_name(name: str) -> str:
    """
    Normalize entity name by removing legal suffixes and extra whitespace.

    Args:
        name: Entity name

    Returns:
        Normalized name
    """
    normalized = name.strip()

    # Remove legal suffixes
    for suffix in LEGAL_SUFFIXES:
        pattern = r'\b' + re.escape(suffix) + r'\b'
        normalized = re.sub(pattern, '', normalized, flags=re.IGNORECASE)

    # Remove trailing punctuation
    normalized = normalized.rstrip('.,;:')

    # Normalize whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()

    return normalized


def fuzzy_entity_resolution(all_contracts: List[Dict]) -> List[Dict]:
    """
    Perform fuzzy entity resolution across all contracts.

    Args:
        all_contracts: List of contract dictionaries

    Returns:
        List of entity group dictionaries
    """
    # Collect all unique entities
    all_entities = set()
    for contract in all_contracts:
        for entity in contract.get('parties', {}).get('all_parties', []):
            all_entities.add(entity)

    # Normalize entities
    entity_map = {}
    for entity in all_entities:
        normalized = normalize_entity_name(entity)
        entity_map[entity] = normalized

    # Group entities with fuzzy matching
    groups = {}
    used = set()

    for entity in all_entities:
        if entity in used:
            continue

        normalized = entity_map[entity]
        group = {
            'canonical_name': entity,
            'members': [entity],
            'match_type': 'exact',
            'confidence': 1.0
        }

        # Find fuzzy matches
        for other_entity in all_entities:
            if other_entity in used or other_entity == entity:
                continue

            other_norm = entity_map[other_entity]
            ratio = SequenceMatcher(None, normalized, other_norm).ratio()

            if ratio > 0.85:
                group['members'].append(other_entity)
                used.add(other_entity)
                group['match_type'] = 'fuzzy'
                group['confidence'] = min(group['confidence'], ratio)

        groups[entity] = group
        used.add(entity)

    return list(groups.values())


def detect_near_duplicates(all_contracts: List[Dict]) -> List[Dict]:
    """
    Detect near-duplicate contracts based on content similarity.

    Args:
        all_contracts: List of contract dictionaries

    Returns:
        List of near-duplicate pairs
    """
    duplicates = []

    for i, contract_a in enumerate(all_contracts):
        for contract_b in all_contracts[i+1:]:
            # Check if same type, date, and customer
            if (contract_a.get('document_type') != contract_b.get('document_type')):
                continue
            if (contract_a.get('effective_date') != contract_b.get('effective_date')):
                continue

            # Compare first 2000 chars
            text_a = contract_a.get('_extracted_text', '')[:2000]
            text_b = contract_b.get('_extracted_text', '')[:2000]

            similarity = SequenceMatcher(None, text_a, text_b).ratio()

            if similarity > 0.90:
                duplicates.append({
                    'file_a': contract_a['filename'],
                    'file_b': contract_b['filename'],
                    'similarity': round(similarity, 3),
                    'reason': 'Text similarity > 90%'
                })

    return duplicates


def process_pdf(pdf_path: str, input_dir: str) -> Dict[str, Any]:
    """
    Process a single PDF through the complete extraction pipeline.

    Args:
        pdf_path: Full path to PDF file
        input_dir: Input directory for relative path calculation

    Returns:
        Dictionary of extracted contract data
    """
    filename = os.path.basename(pdf_path)

    try:
        # Step 1: Extract text
        text, extraction_method = extract_text_from_pdf(pdf_path)

        if extraction_method == "error":
            return {
                'filename': filename,
                'filepath': pdf_path,
                'status': 'error',
                'warnings': [f"Failed to extract text from {filename}"]
            }

        # Step 2: Detect language
        language_warning = detect_language(text)

        # Step 3: Extract title
        title, title_confidence, short_header = extract_title(text)

        # Step 4: Extract DBA aliases
        dba_aliases = extract_dba_aliases(text)

        # Step 5: Extract dates
        effective_date, expiration_date, term_info, amendment_date = extract_dates(text)

        # Step 6: Extract parties
        all_parties, customer_candidates, flex_entities = extract_parties(text)

        # Step 7: Extract financial terms
        financial_terms = extract_financial_terms(text)

        # Step 8: Extract parent reference
        parent_reference, parent_ref_confidence = extract_parent_reference(text)

        # Step 9: Classify document
        document_type, hierarchy_role = classify_document(short_header, text)

        return {
            'filename': filename,
            'filepath': pdf_path,
            'title': title,
            'title_confidence': title_confidence,
            'short_header': short_header,
            'document_type': document_type,
            'hierarchy_role': hierarchy_role,
            'effective_date': effective_date,
            'expiration_date': expiration_date,
            'term_info': term_info,
            'parties': {
                'all_parties': all_parties,
                'customer_candidates': customer_candidates,
                'flex_entities': flex_entities
            },
            'dba_aliases': dba_aliases,
            'parent_reference': parent_reference,
            'parent_ref_confidence': parent_ref_confidence,
            'financial_terms': financial_terms,
            'status': 'active',
            'governing_law': None,
            'language_warning': language_warning,
            'extraction_method': extraction_method,
            'warnings': [],
            '_extracted_text': text  # For duplicate detection
        }

    except Exception as e:
        logger.error(f"Error processing {filename}: {e}")
        return {
            'filename': filename,
            'filepath': pdf_path,
            'status': 'error',
            'warnings': [str(e)]
        }


def main():
    """Main entry point for the extraction pipeline."""
    parser = argparse.ArgumentParser(
        description='Extract and classify contract PDFs into hierarchical structures.'
    )
    parser.add_argument(
        '--input-dir',
        required=True,
        help='Directory containing PDF files to process'
    )
    parser.add_argument(
        '--output',
        default=None,
        help='Output JSON manifest file (default: stdout)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )

    args = parser.parse_args()

    if args.verbose:
        logger.setLevel(logging.DEBUG)

    # Validate input directory
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        logger.error(f"Input directory not found: {args.input_dir}")
        sys.exit(1)

    # Find all PDF files
    pdf_files = sorted(input_dir.glob('*.pdf'))
    if not pdf_files:
        logger.warning(f"No PDF files found in {args.input_dir}")
        pdf_files = []

    logger.info(f"Found {len(pdf_files)} PDF files to process")

    # Process each PDF
    contracts = []
    ocr_needed_count = 0
    non_english_count = 0
    error_details = []

    for idx, pdf_path in enumerate(pdf_files, 1):
        logger.info(f"[{idx}/{len(pdf_files)}] Processing {pdf_path.name}")

        result = process_pdf(str(pdf_path), str(input_dir))

        if result.get('status') == 'error':
            error_details.append({
                'filename': result['filename'],
                'error': result['warnings'][0] if result['warnings'] else 'Unknown error'
            })
        else:
            if result.get('extraction_method') == 'ocr_needed':
                ocr_needed_count += 1
            if result.get('language_warning'):
                non_english_count += 1
            contracts.append(result)

    # Step 10: Fuzzy entity resolution
    entity_groups = fuzzy_entity_resolution(contracts)

    # Step 11: Near-duplicate detection
    near_duplicates = detect_near_duplicates(contracts)

    # Clean up _extracted_text for output
    for contract in contracts:
        contract.pop('_extracted_text', None)

    # Build output manifest
    manifest = {
        'extraction_summary': {
            'total_files': len(pdf_files),
            'successful': len(contracts),
            'ocr_needed': ocr_needed_count,
            'ocr_available': HAS_PYTESSERACT,
            'non_english_warnings': non_english_count,
            'errors': len(error_details),
            'error_details': error_details,
            'warnings': []
        },
        'contracts': contracts,
        'entity_groups': entity_groups,
        'near_duplicates': near_duplicates
    }

    # Output results
    output_json = json.dumps(manifest, indent=2, default=str)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(output_json)
        logger.info(f"Manifest written to {args.output}")
    else:
        print(output_json)

    # Summary
    logger.info(f"Processing complete: {len(contracts)}/{len(pdf_files)} successful")
    if error_details:
        logger.warning(f"{len(error_details)} errors encountered")


if __name__ == '__main__':
    main()
