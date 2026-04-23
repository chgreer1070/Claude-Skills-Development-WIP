---
name: Contract Portfolio Organizer
description: >
  Rapidly ingest, classify, and organize customer contracts into a queryable portfolio
  with relationship mapping and financial summaries. Handles PDFs from <50 to 200+ contracts,
  detects amendments/riders, surfaces parent agreements, flags near-duplicates, extracts
  expiration/financial terms, and generates four visualization formats. **Triggers on:**
  "organize my contracts", "analyze our contract portfolio", "build a contract database",
  "extract and classify my PDFs", or "catalog our agreements".
---

# Contract Portfolio Organizer v4

Transform raw PDF contract folders into a richly annotated, relationship-mapped contract
portfolio with confidence scores, financial summaries, and multi-format visualizations.

## Overview

This skill ingests a directory of contract PDFs, extracts metadata (title, effective/expiration
dates, financial terms, parties, parent references), classifies contracts into a hierarchical
taxonomy, resolves entity ambiguities using fuzzy matching, builds a relationship graph with
confidence scoring, and outputs a structured portfolio with four visualization types. Handles
non-English detection, scanned PDFs with OCR fallback, near-duplicate flagging, and supersession
chains of arbitrary depth.

## Six-Phase Process

### Phase 1: Extract & Detect

The skill runs a deterministic extraction pipeline via bundled Python script. This separates
concerns—the script handles predictable, mechanical work; you focus on judgment calls.

**Run the extraction script:**

```bash
pip install pymupdf --break-system-packages
python scripts/extract_and_classify.py --input-dir <pdf_directory> --output manifest.json --verbose
```

The script processes each PDF in isolation (try/except wrapped) and outputs `manifest.json`
with all extracted metadata. It handles:

- **PDF text extraction** with native PyMuPDF; detects empty text layers (scanned PDFs)
- **Title extraction** from ALL-CAPS headers *and* Title-Case headers (lower confidence)
- **DBA/alias detection** (legal vs. trade names)
- **Contract classification** (expanded TYPE_MAP including Supply Agreements, Framework Agreements, GTC, Sourcing Agreements, Cooperation Agreements, PO Terms, Assignment/Novation)
- **Parent reference extraction** via "pursuant to", "supersedes", "amends", "enters into" anchors; also "effective as of" / "entered into on" patterns
- **Effective & expiration date extraction** (term_info captures "5 years with auto-renewal")
- **Financial term extraction** (contract_value, liability_cap, payment_terms)
- **Entity resolution** with fuzzy name matching (difflib.SequenceMatcher ratio >0.85)
- **Near-duplicate detection** (same type/date, >90% text similarity → flagged, not auto-merged)
- **Non-English detection** (warnings for contracts not in English)
- **OCR detection** (marks extraction_method as "native", "ocr_needed", or "ocr_completed")

**Review the manifest:**

Open `manifest.json`. Spot-check contracts with low confidence scores, warnings, or
unknowns. The script provides confidence_scores for title extraction, parent_ref_confidence,
and metadata_confidence. Pay special attention to:

- Contracts marked `extraction_method: "ocr_needed"` (offer OCR via pytesseract, or skip with warning)
- Contracts with `language_warning: true` (may be non-English)
- Low-confidence title_confidence or parent_ref_confidence (<0.70)
- Unknown/unclassified contracts (document_type is null)
- near_duplicates list (same-type/same-date contracts; decide which to keep)

### Phase 2: Classify & Resolve Unknowns

Review the script's document_type assignments. For any contracts classified as `null`:

1. Open the PDF and read the header / recitals
2. Match against the **Expanded Taxonomy** (see below)
3. Decide: is this a parent, child, modifier, or ancillary?
4. Update the manifest entry with the correct document_type and hierarchy_role
5. For multi-party contracts (3+ parties), note in the parties.all_parties list

**Expanded Taxonomy:**

| Type | Hierarchy Role | Trigger Phrases |
|------|---|---|
| Master Service Agreement (MSA) | parent | "Master Service Agreement", "MSA", "Terms and Conditions" |
| Supply Agreement | parent | "Supply Agreement", "Master Supply Agreement" |
| Framework Agreement | parent | "Framework Agreement"; establishes governing terms structure |
| General Terms & Conditions (GTC) | parent | "General Terms and Conditions", "Standard Terms" |
| Sourcing Agreement | parent | "Sourcing Agreement"; specifies supplier terms |
| Cooperation Agreement | parent | "Cooperation Agreement"; joint/mutual governance |
| Amendment / Revision (A&R) | parent_superseding | "Amendment No. 1", "First Amendment", "Revision Agreement"; newest supersedes oldest active parent |
| Purchase Order / SOW | child | References parent MSA; "Statement of Work", "SOW", "Purchase Order", "PO" |
| Purchase Order Terms | child | "Purchase Order Terms"; references a parent Supply Agreement |
| Service Schedule | child | "Schedule A", "Schedule of Services"; modifies parent scope |
| Change Order | modifier | "Change Order", "Modification", "Addendum"; adjusts terms of existing agreement |
| Amendment Letter | modifier | "Amendment Letter", "Letter Agreement"; concise amendment (not numbered revision) |
| Assignment / Novation | modifier | "Assignment Agreement", "Novation"; transfers party rights to third party |
| Termination Agreement | modifier | "Termination Agreement"; formally ends prior agreement |
| Service Level Addendum | child | "Service Level Agreement", "SLA"; performance metrics supplement |
| Reseller / Partner Agreement | child/parent | Depends on scope; mark hierarchy_role appropriately |
| NDA / Confidentiality | ancillary | "Non-Disclosure Agreement", "Confidentiality Agreement" |
| Insurance Certificate | ancillary_terminal | "Certificate of Insurance"; proof of compliance |
| Compliance / Regulatory | ancillary_terminal | "Compliance Matrix", "Regulatory Attestation"; terminal reference |

### Phase 3: Resolve Entity Ambiguities

The script performs fuzzy entity matching (difflib.SequenceMatcher ratio >0.85 on normalized names).
Review `parties.customer_candidates` and `parties.flex_entities` in the manifest:

1. **Customer candidates** = parties that could be your organization (review for true customer)
2. **Flex entities** = ambiguous parties (subsidiaries, DBAs, regional offices)

For each contract:

- Mark the true customer (your organization) in `parties.customer_candidates`
- Group aliases and DBAs (legal name, trade name, regional offices) in `dba_aliases`
  ```json
  "dba_aliases": [
    ["Acme Corporation", "Acme Corp"],
    ["Acme Manufacturing LLC", "Acme Mfg"]
  ]
  ```
- Resolve `flex_entities` by researching corporate relationships; consolidate under canonical names

Update the manifest to reflect your final entity resolution. This step ensures downstream
linking and hierarchy building use consistent entity names.

### Phase 4: Link & Build Relationship Graph

With clean metadata, build the relationship graph:

1. **Load parent candidates:** Contracts with `hierarchy_role in ('parent', 'parent_superseding')`
2. **For each child/modifier:**
   - Extract keywords from title (lowercased, minus stop words)
   - Scan parent titles for keyword overlap
   - Check effective_date proximity (within 90 days = stronger signal)
   - Score confidence:
     - 3+ keywords AND date match → 0.95
     - 2+ keywords AND date match → 0.90
     - 3+ keywords, no date match → 0.80
     - 1 keyword AND date match → 0.75
     - Fallback (parent_reference match or implicit link) → 0.60
   - Flag links <0.75 confidence for human review

**Stop words (exclude from keyword overlap):**
"agreement", "services", "the", "and", "of", "dated", "between", "this", "that", "certain",
"pursuant", "under", "made", "entered", "into", "effective", "party", "parties"

3. **Handle Amendment chains:**
   - Process A&R (Amendment & Revision) MSAs newest-first
   - New A&R supersedes whichever parent is currently active
   - Naturally generalizes to 3+ level chains (MSA → 1st A&R → 2nd A&R → ...)
   - Each tier records its supersedes/superseded_by references

4. **Merge results into manifest** with relationship_graph entries:
   ```json
   "parent_agreement": "Master Service Agreement (2015-10-23)",
   "parent_confidence": 0.95,
   "children": [
    { "title": "SOW: Design Services", "date": "2016-03-15", "confidence": 0.90 }
   ],
   "superseded_by": "Amendment No. 1 (2019-06-01)" or null,
   "supersedes": "Prior Agreement Title (2012-01-01)" or null
   ```

### Phase 5: Organize & Index

Create the portfolio folder structure by customer:

```
portfolio/
├── customer_1/
│   ├── contracts/
│   │   ├── parent-msa-master-service-agreement-2015-10-23.pdf
│   │   ├── child-sow-design-services-2016-03-15.pdf
│   │   ├── modifier-amendment-1-2019-06-01.pdf
│   │   └── ancillary-nda-2014-05-10.pdf
│   ├── _INDEX.json
│   └── visualizations/
│       ├── portfolio-map.json
│       ├── timeline.json
│       ├── entity-groups.json
│       └── financial-summary.json
├── customer_2/
│   └── [same structure]
└── _PORTFOLIO_SUMMARY.json
```

Generate `_INDEX.json` for each customer with this schema:

```json
{
  "customer": "Canonical Customer Name",
  "generated_date": "YYYY-MM-DD",
  "contract_count": 12,
  "date_range": {
    "earliest": "2014-01-15",
    "latest": "2026-03-10"
  },
  "parent_agreements": [
    {
      "title": "Master Service Agreement",
      "date": "2015-10-23",
      "status": "active",
      "children_count": 7,
      "financial_terms": {
        "contract_value": "$5M",
        "liability_cap": "2x annual fees",
        "payment_terms": "Net 60"
      }
    }
  ],
  "orphans": [
    {
      "title": "Service Schedule",
      "date": "2018-02-20",
      "reason": "No parent MSA found"
    }
  ],
  "missing_parents": [
    {
      "child_title": "SOW",
      "references": "Prior Agreement (date unknown)"
    }
  ],
  "near_duplicates": [
    {
      "titles": ["Amendment Letter", "Amendment No. 1"],
      "dates": ["2020-03-01", "2020-03-01"],
      "similarity": 0.92,
      "note": "Likely same amendment; consolidate"
    }
  ],
  "warnings": [
    "5 contracts with low title confidence (< 0.70)",
    "2 PDFs marked OCR_NEEDED; recommend pytesseract installation",
    "1 contract in non-English; manual review recommended"
  ],
  "financial_summary": {
    "total_identified_value": "$15M",
    "contracts_with_value": 3,
    "contracts_without_value": 9
  }
}
```

### Phase 6: Visualize & Deliver

Generate four output formats per customer (stored in visualizations/ subdirectory):

1. **Portfolio Map (JSON/Graph):** hierarchical structure of parents, children, modifiers, orphans
2. **Timeline (JSON):** contract effective/expiration dates, term lengths, auto-renewal flags
3. **Entity Groups (JSON):** consolidated party names with aliases, role (customer, vendor, third-party)
4. **Financial Summary (JSON/CSV):** contract values, liability caps, payment terms, totals

See `references/visualization-templates.md` for detailed schema and example outputs for each format.

## Error Recovery & Robustness

The extraction script wraps each PDF in try/except to handle corruption, permission errors,
or unsupported formats gracefully. Failed PDFs appear in `extraction_summary.error_details`
with the exception message.

**Handling extraction failures:**

1. Present errors to the user with the file name and error message
2. Ask: "Skip this file or retry?"
3. If skip: continue processing remaining PDFs; note in warnings
4. If retry: check file permissions, try alternative PDF library, or ask user to re-export

**OCR fallback:**

If a PDF is marked `extraction_method: "ocr_needed"`:

- Offer to install `pytesseract` (requires Tesseract binary on system)
- If user consents, run OCR and update extraction_method to "ocr_completed"
- If declined, mark extraction_method as "ocr_skipped" and warn user that title/date extraction may be incomplete

**Non-English contracts:**

If `language_warning: true`:

- Inform the user of the file and detected language
- Ask: "Translate and retry, or mark for manual review?"
- If translate: use translation API (Google Translate, Claude, etc.) on extracted text
- If manual: document filename in warnings for human follow-up

## Scale & Performance

**<50 contracts:**
Run normally. The script processes one PDF at a time and is memory-efficient.

**50–200 contracts:**
Consider batching by pre-known customer if entity names are available upfront. This accelerates
entity resolution.

**200+ contracts:**
1. Run extraction script via `nohup python scripts/extract_and_classify.py ... &` (background process)
2. Process script output in batches (e.g., 50 customers at a time)
3. Process customer-by-customer to avoid entity resolution bottlenecks
4. For very large batches, consider distributed processing (not covered here)

**Memory management:**
The extraction script does not load entire PDF text into memory. It streams extraction and
appends to manifest.json incrementally. For timeout issues on very slow systems, increase
the subprocess timeout or run via background process.

## Incremental Updates

To add new contracts to an existing portfolio:

1. **Extract new PDFs only:**
   ```bash
   python scripts/extract_and_classify.py --input-dir <new_pdfs_dir> --output new_manifest.json
   ```

2. **Load existing indexes:**
   For each customer folder, load the existing `_INDEX.json` and contract manifest

3. **Merge new contracts:**
   - Add new contracts to the customer's contracts/ folder
   - Update the manifest with new contract metadata
   - Preserve existing folder structure; never delete old contracts

4. **Re-run linking:**
   For each new contract, run Phase 4 (link & build relationship graph) against the full
   existing parent set. This ensures new children/modifiers link to correct parents.

5. **Regenerate visualizations:**
   Regenerate Phase 6 outputs for affected customers only (those with new contracts)

6. **Update _INDEX.json:**
   Recalculate contract_count, date_range, and financial_summary for each updated customer

## Metadata Schema

Each contract's metadata includes:

```json
{
  "filename": "original_filename.pdf",
  "title": "Formal title extracted from PDF",
  "title_confidence": 0.95,
  "document_type": "Master Service Agreement (or null if unknown)",
  "hierarchy_role": "parent|parent_superseding|modifier|child|child_l2|ancillary|ancillary_terminal|standalone",
  "effective_date": "YYYY-MM-DD",
  "expiration_date": "YYYY-MM-DD or null",
  "term_info": "5 years with auto-renewal, or null",
  "parties": {
    "all_parties": ["Party A Inc.", "Party B LLC", "Party C Corp."],
    "customer_candidates": ["Party A Inc."],
    "flex_entities": ["Party B Regional Office"]
  },
  "dba_aliases": [
    ["Legal Name", "Trade Name"],
    ["Acme Corporation", "Acme Corp"]
  ],
  "parent_reference": "Referenced parent agreement title, or null",
  "parent_ref_confidence": 0.90,
  "financial_terms": {
    "contract_value": "$10M or null",
    "liability_cap": "2x annual fees or null",
    "payment_terms": "Net 60 or null"
  },
  "status": "active|terminated|superseded|completed|expired",
  "governing_law": "jurisdiction",
  "language_warning": false,
  "extraction_method": "native|ocr_needed|ocr_completed|ocr_skipped",
  "relationship_graph": {
    "parent_agreement": "MSA title or null",
    "parent_confidence": 0.95,
    "children": [{ "title": "...", "date": "...", "confidence": 0.90 }],
    "superseded_by": "Newer agreement title or null",
    "supersedes": "Older agreement title or null"
  }
}
```

## References

- **Visualization templates:** See `references/visualization-templates.md` for four output formats
- **Extraction script:** The skill bundles `scripts/extract_and_classify.py`, the deterministic extraction engine
- **Patch history:** See `references/patch-log.md` for v1–v4 improvements
- **Known limitations:** OCR quality depends on Tesseract version; very large PDFs (>500 pages) may timeout

## Typical Workflow

1. Collect all contract PDFs in a single directory
2. Run `pip install pymupdf --break-system-packages && python scripts/extract_and_classify.py --input-dir <dir> --output manifest.json --verbose`
3. Review manifest for warnings, unknowns, near-duplicates (15–30 min for 50 contracts)
4. Update document_type, hierarchy_role, and entity resolution in manifest (30 min–2 hours depending on complexity)
5. Run Phase 4 linking script to build relationship graph
6. Organize into portfolio folder structure (automated)
7. Generate four visualizations per customer (automated)
8. Deliver to stakeholder with _INDEX.json summary and visualizations

## Tips for Best Results

- **Pre-clean filenames** if possible (remove extra spaces, special characters)
- **Separate by customer** if processing >100 contracts (easier entity resolution)
- **Spot-check parents** after Phase 3 (make sure customer, vendor, and subsidiary names are correctly identified)
- **Review near-duplicates** in _INDEX.json before final delivery (decide which amendment version to keep)
- **Test OCR** on one scanned PDF before committing to full batch (Tesseract performance varies)
- **Use effective_date for linking**, not signature date, when parent/child relationships are ambiguous
