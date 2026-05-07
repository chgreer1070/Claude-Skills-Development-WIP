# Contract Portfolio Organizer v4 — Stress-Test Report

**Branch:** `claude/team-review-v2R9b`
**Skill audited:** `contract-portfolio-organizer-v4/`
**Date:** 2026-05-07
**Methodology:** static review + runtime stress with 25 synthetic PDFs + scale benchmark at N ∈ {100, 500, 1000}

---

## Executive Summary

The skill is functional and well-structured for its happy path, but the runtime
fixture pass surfaced four issues that materially change extraction output for
**realistic, non-adversarial** contracts — three of those were not in the
initial static review. Two are security issues in the bundled visualization
templates. All Critical findings have been fixed in this commit; two High
findings (language false-positive on short text, multi-party regex truncation
at internal periods) are documented but deferred per scope.

**Top findings (severity-ordered):**

| # | Tag | Headline |
|---|---|---|
| F6 | `[C2-Critical-Always-Workflow-Isolated]` | `dated …` regex hijacks the **child/amendment** document's effective_date by matching the **parent** reference. SOWs, amendments, and A&R MSAs all inherited the wrong date. **Fixed.** |
| F7 | `[C1-Critical-Always-Workflow-Isolated]` | `Change Order` is documented in SKILL.md taxonomy but missing from `TYPE_MAP` — could never classify. **Fixed.** |
| F4 | `[C5-Critical-Always-Blocker-Isolated]` | Two `innerHTML = \`...${value}\`` injection sinks in `references/visualization-templates.md` (detail panel + timeline tooltip). Trivially exploitable from a contract whose title contains HTML. **Fixed.** |
| F3 | `[C5-Critical-Always-Workflow-Isolated]` | SKILL.md instructs `pip install pymupdf --break-system-packages`, overriding PEP 668 protections on the user's base Python. **Fixed.** |
| F1+F2 | `[C2-High-Always-Annoying-Isolated]` | `extract_title` returned a 4-tuple where item 4 duplicated item 1; `short_header` detection block was dead code (outer loop already broke on `"This "`). **Fixed.** |
| F5 | `[C5-High-Often-Workflow-Isolated]` | Phase 5 had no guidance for sanitizing customer names used as folder paths (unicode, `..`, collisions). **Fixed (doc).** |
| H-LANG | `[C3-High-Always-Annoying-Isolated]` | 22 / 24 baseline English contracts flagged `language_warning=True` — short legalese has too few stop-word hits to clear the 40 % English-ratio threshold. **Documented, deferred.** |
| H-MULTI | `[C2-High-Always-Workflow-Isolated]` | "by and among A, B Inc., C Ltd., and D Inc." → only 2 of 4 parties, because `[^.;:]+?` truncates at the first `.` inside `Inc.`. **Documented, deferred.** |
| H-DUP | `[C4-High-Often-Annoying-CrossCutting]` | At N=500 → 496 near-duplicates flagged; at N=1000 → 2480. Same-type/same-effective_date is far too permissive for a synthetic corpus and will misfire on real portfolios with seasonal contract bursts. **Documented, deferred.** |
| H-IMPLICIT | `[C1-High-Often-Annoying-Isolated]` | Phase 4 scoring rubric in SKILL.md mentions `parent_reference match OR implicit link → 0.60` but never defines "implicit link". **Documented, deferred.** |
| M-VER | `[C1-Medium-Always-Invisible-Isolated]` | Folder is `contract-portfolio-organizer-v4` and SKILL.md heading is "v4", but body says "v5 incorporated 22 improvements" and patch-log refers to "v5 release". Documented. |

**Ship recommendation:** ship with the four Critical fixes applied. The two
deferred Highs (language false-positive, multi-party split) and the over-permissive
near-duplicate heuristic should be the next batch.

---

## Methodology

### Test taxonomy

| ID | Category | What it tests |
|---|---|---|
| C1 | Specification consistency | Doc ↔ code drift, version labels, dead code, undefined rubric terms |
| C2 | Correctness | Classification, entity resolution, date/party extraction, parent linking |
| C3 | Robustness | Malformed inputs, edge cases, i18n, OCR/empty PDFs |
| C4 | Scale | Wall-time, memory, false-positive rates at N=100/500/1000 |
| C5 | Security | Install directives, XSS in HTML templates, path traversal |

### Scoring rubric

Each finding is tagged `[Cx-Severity-Reproducibility-Impact-FixLocality]`:

- **Severity:** Critical / High / Medium / Low
- **Reproducibility:** Always / Often (>50%) / Sometimes / Rare
- **User impact:** Blocker / Workflow-breaking / Annoying / Invisible
- **Fix locality:** Isolated / Cross-cutting / Architectural

### Fixture corpus (25 PDFs)

Built deterministically with `reportlab` via `tests/fixtures/build_fixtures.py`.
Each PDF has a `tests/fixtures/expected/<stem>.yaml` sidecar that
`tests/diff_expected.py` checks at a key-by-key level (subset semantics — only
listed keys are enforced; absence is not failure).

| Group | Count | Example fixtures |
|---|---|---|
| Baseline | 5 | `B01_clean_msa`, `B02_nda`, `B03_sow`, `B04_amendment_1`, `B05_addendum` |
| Correctness edges | 8 | conflict-title, entity collision (Inc/LLC), Spanish legalese, body-text "amendment", `amendment and waiver`, 2nd A&R MSA, implicit-parent date-only, no-header MSA-in-body |
| Robustness | 7 | unicode party, RTL transliteration, empty text layer, corrupt PDF header, 4-party "among", DBA chain, missing effective_date |
| Security | 5 | `<script>` title, `../../etc/passwd` party, badge-class payload, SVG-breaking title, 10 KB title |

For scale, the same generator produced 100 / 500 / 1000 PDFs in `/tmp/scale{N}/pdfs/`.

---

## Results

### Pre-fix vs post-fix

| Pass | Pre-fix | Post-fix |
|---|---|---|
| PASS | 11 | **15** |
| FAIL | 6 | 2 |
| INFO (advisory; no checkable assertions) | 8 | 8 |
| MISS (no manifest entry — should never happen for non-error fixtures) | 0 | 0 |

The 4 newly-passing fixtures (B03 SOW, B04 Amendment, C06 A&R MSA, C07 Change Order) all flipped because of fixes F6 + F7.

### Scale benchmark

| N | Wall-time | Manifest size | `entity_groups` | `near_duplicates` |
|---|---|---|---|---|
| 100 | 0.34 s | 100.6 KiB | 2 | 0 |
| 500 | 1.23 s | 578.7 KiB | 2 | **496** |
| 1000 | 2.63 s | 1.39 MiB | 2 | **2 480** |

Wall-time scales roughly linearly because the `O(n²)` pair loop short-circuits
on type/date mismatch before running `SequenceMatcher`. The duplicate-pair
*count*, however, grows super-linearly: same-type + same-effective-date is too
loose a gate to be a reliable duplicate signal on real portfolios where
end-of-quarter signing bursts produce many distinct same-day same-type contracts.

### Per-fixture matrix (post-fix)

```
B01_clean_msa                  FAIL  parties strip trailing '.'; language_warning false-positive
B02_nda                        PASS
B03_sow                        PASS  (was FAIL: parent's date leaked in)
B04_amendment_1                PASS  (was FAIL: parent's date leaked in)
B05_addendum                   PASS
C01_conflict_amendment_nda     INFO  observed: NDA wins after F6/F7 reordering; no conflict flag (gap)
C02_entity_collision_inc_llc   PASS  but fuzzy-merge collapses Inc vs LLC (post-norm collision; documented)
C03_spanish_legalese           PASS  language_warning=True triggered
C04_nda_body_amendment_word    PASS
C05_amendment_and_waiver       PASS
C06_ar_msa_second              PASS  (was FAIL: parent's date leaked in)
C07_implicit_parent_date_only  PASS  (was FAIL: Change Order missing from TYPE_MAP)
C08_no_header_msa_body         PASS  (parent types correctly skipped in body pass per v4-7)
R01_unicode_party              INFO  party preserved; folder sanitization deferred to skill consumer
R02_rtl_transliteration        INFO
R03_empty_text_layer           PASS  extraction_method=ocr_needed, no crash
R04_corrupt_header             PASS  status=error, batch continued
R05_multi_party_four           FAIL  2 of 4 parties due to '.' inside party name
R06_dba_alias                  PASS  d/b/a captured
R07_missing_effective_date     PASS  effective_date=None; no crash
S01_xss_title                  INFO  raw text in manifest; rendering now safe (F4)
S02_path_traversal_party       INFO  raw text in manifest; folder layer now documented (F5)
S03_badge_class_payload        INFO
S04_svg_title_payload          INFO  raw text in manifest; SVG renderer truncates at 40 chars (still no escape — Low)
S05_long_title                 INFO
```

---

## Findings — detail

### F1+F2 — `extract_title` 4-tuple duplicate + dead `short_header` block

**Tag:** `[C2-High-Always-Annoying-Isolated]`
**Evidence:** `scripts/extract_and_classify.py:144-227` (pre-fix).
The signature returned `(full_header, confidence, short_header, full_header)`. The
4th element duplicated the 1st. The `for part in title_parts: if part.startswith("This "):`
block was dead because the outer loop already broke on `"This "` *before* appending
to `title_parts` (line ~212), so the inner condition was never true → `short_header`
was always equal to `full_header`.

**Fix:** signature is now 3-tuple; `short_header` is computed by re-scanning raw
`lines` for the preamble boundary. Caller in `process_pdf` updated to unpack 3.

### F3 — `--break-system-packages` install directive

**Tag:** `[C5-Critical-Always-Workflow-Isolated]`
**Evidence:** `SKILL.md:36` (Phase 1) and `SKILL.md:385` (Typical Workflow).
Bypasses PEP 668 and writes into the user's base Python. Real risk of breaking
unrelated tooling on the operator's machine.

**Fix:** both call-sites now instruct `python3 -m venv .venv && source .venv/bin/activate && pip install pymupdf`. The script's docstring install hint
also no longer claims `pip install difflib` (stdlib).

### F4 — XSS in `references/visualization-templates.md`

**Tag:** `[C5-Critical-Always-Blocker-Isolated]`
**Evidence:**
- `references/visualization-templates.md:183` — detail panel did `row.innerHTML = `<div class="detail-label">${label}</div><div class="${valueClass}">${value}</div>`` where `value` is contract metadata (`title`, `parties`, `governing_law`, etc.).
- `references/visualization-templates.md:863-891` — timeline tooltip did `tooltip.innerHTML = \`<div class="tooltip-title">${event.title}</div>...\``.

A contract whose `title` contains `<script>...</script>` (or `<img onerror=...>`,
or any markup) executes verbatim when a user hovers / clicks on the rendered HTML.

**Fix:** both sinks rebuilt with `document.createElement` + `textContent`. No
behavioral change for benign data; HTML/script payloads now render as text.

### F5 — Phase 5 customer-folder sanitization

**Tag:** `[C5-High-Often-Workflow-Isolated]`
**Evidence:** `SKILL.md:162` (pre-fix) — example tree showed `customer_1/` etc.
but no guidance on how to derive that name from the extracted `customer_candidates`,
which can contain unicode (`株式会社トヨタ`), path-traversal segments
(`../../etc/passwd Inc.` — see fixture S02), or collide.

**Fix:** added 4-step normalization recipe to Phase 5: NFKD-fold + ASCII-restrict
+ collapse-`-` + collision suffix + reject `.`/`..` after `Path.resolve()`.
Canonical name kept inside `_INDEX.json["customer"]` so display layers still see
the original.

### F6 — child/amendment effective_date hijacked by parent reference

**Tag:** `[C2-Critical-Always-Workflow-Isolated]`
**Evidence:** `scripts/extract_and_classify.py:278-283` (pre-fix). Pattern order was:

```python
r'effective\s+(?:as\s+of\s+)?…',
r'dated\s+…',
r'entered\s+into\s+(?:on\s+)?…',
```

For the standard SOW preamble *"This SOW is entered into on April 4, 2021, …, pursuant to … MSA dated January 15, 2020"*, the second pattern won and the script reported `effective_date = 2020-01-15` (the parent MSA's date) — silently, with no warning. Confirmed on B03, B04, C06.

**Fix:** reorder so `entered into` precedes `dated`, and extend `entered into`
to also accept `as of` (the literal phrasing in B01 was *"is entered into as of January 15, 2020"* — neither anchor matched pre-fix because `effective` wasn't
the preceding word). After fix B03/B04/C06 + B01 all extract the correct
own-document date.

### F7 — `Change Order` listed in taxonomy but absent from `TYPE_MAP`

**Tag:** `[C1-Critical-Always-Workflow-Isolated]`
**Evidence:** `SKILL.md:91` Phase 2 taxonomy lists `Change Order | modifier | "Change Order", "Modification", "Addendum"`. `scripts/extract_and_classify.py:54-81` `TYPE_MAP` had no regex for it. Result: any document titled "Change Order" went out as `document_type=None, hierarchy_role="unknown"`.

**Fix:** added `(r'change\s+order|(?<!\w)modification\s+agreement(?!\w)', 'Change Order', 'modifier')` immediately after the assignment/novation entry.
Note `Addendum` is intentionally still mapped to its own role (`child`) per existing pattern; a `Change Order` titled "Addendum" remains an `Addendum`.

---

## Deferred — High & Medium

### H-LANG — language false-positive on short English contracts

**Tag:** `[C3-High-Always-Annoying-Isolated]`
**Evidence:** post-fix manifest shows `language_warning=True` on 22 / 24 fixtures,
including every clean baseline. The detector counts hits against a 22-word stop
list (`the`, `of`, `and`, …) and flags non-English when the ratio is below 0.40.
Short legalese ("MASTER SERVICES AGREEMENT … This MSA is entered into between A
and B …") has very low stop-word density.

**Recommendation:** require absolute count ≥ 5 stop-word hits *and* either ratio
≥ 0.30 *or* a minimum word count (e.g. only run the detector on texts ≥ 200
words). Or swap to a proper detector (`langdetect`, `lingua`).

### H-MULTI — multi-party "among" regex truncates at internal periods

**Tag:** `[C2-High-Always-Workflow-Isolated]`
**Evidence:** R05 fixture, `scripts/extract_and_classify.py:372`:

```python
r'(?:by\s+and\s+)?among\s+([^.;:]+?)(?:\.|;|:)'
```

`[^.;:]+?` stops at `.` — so `"among A Corp, B Inc., C Ltd., and D LLC."`
captures only `"A Corp, B Inc"` and the subsequent split sees 2 parties.

**Recommendation:** consume up to a sentence terminator that is followed by a
newline or capital sentence start, not any `.`. Or use a positive list of
known closers (`\.\s+(?:[A-Z]|\n)`). Real-world multi-party contracts always
hit this.

### H-DUP — over-permissive near-duplicate detection

**Tag:** `[C4-High-Often-Annoying-CrossCutting]`
**Evidence:** scale benchmark — N=500 → 496 pairs, N=1000 → 2480 pairs. Same
type + same effective_date is the only structural gate before the 0.90 text
threshold. End-of-quarter / fiscal-year-end signing bursts will trip this on
every real portfolio.

**Recommendation:** add same-customer (post entity-resolution) gate, or drop
to "same effective_date *and* fingerprint of the first 200 chars matches".

### H-IMPLICIT — undefined "implicit link" in Phase 4 rubric

**Tag:** `[C1-High-Often-Annoying-Isolated]`
**Evidence:** SKILL.md Phase 4 lists `Fallback (parent_reference match or implicit link) → 0.60` but never defines what an "implicit link" is, so a 0.60 confidence value is non-reproducible across operators.

**Recommendation:** either define it explicitly (e.g. "child has a parent
keyword in its title and an effective_date within 30 days of an existing parent
without an explicit textual reference") or remove the term from the rubric.

### M-VER — version label drift v4 ↔ v5

**Tag:** `[C1-Medium-Always-Invisible-Isolated]`
**Evidence:** folder name `contract-portfolio-organizer-v4`, SKILL.md heading
"Contract Portfolio Organizer v4", but SKILL.md and `references/patch-log.md`
both refer to "v5 release" / "v5 improvements". Either rename the folder /
heading to v5 or move the v5 language back into the v4 patch list.

### M-OCR — short-but-valid PDFs flagged `ocr_needed`

**Tag:** `[C3-Medium-Often-Annoying-Isolated]`
**Evidence:** `extract_text_from_pdf` flags `ocr_needed` whenever extracted text
< 100 chars (line 109). B05_addendum (a one-screen valid Addendum, 95 chars)
got the flag. Operators who follow the Phase 1 guidance will install Tesseract
unnecessarily.

**Recommendation:** raise threshold *and* require `len(doc) >= 1` page that
returned zero chars; or use PyMuPDF's image-vs-text page heuristic.

---

## Fixes — diff summary

| ID | File | Lines (post-fix) | Change |
|---|---|---|---|
| F1+F2 | `scripts/extract_and_classify.py` | ~144, ~215, ~668 | `extract_title` 3-tuple; `short_header` re-scan; caller updated |
| F6 | `scripts/extract_and_classify.py` | ~280-290 | reorder `entered into` before `dated`; accept `as of`; accept `dated as of` |
| F7 | `scripts/extract_and_classify.py` | ~60 | new TYPE_MAP entry for `Change Order` |
| F3 | `SKILL.md` | ~33-44, ~385-388 | venv flow replaces `--break-system-packages` |
| F5 | `SKILL.md` | Phase 5 (~162-186) | folder-naming sanitization recipe |
| F3 doc | `scripts/extract_and_classify.py` | ~9-15 | install hint cleaned (`difflib` is stdlib) |
| F4 | `references/visualization-templates.md` | detail panel + timeline tooltip | `innerHTML` → `createElement` + `textContent` |

---

## Reproducing this report

From the repo root:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install pymupdf reportlab pyyaml

# Build fixtures
python contract-portfolio-organizer-v4/tests/fixtures/build_fixtures.py

# Run extractor on fixtures
python contract-portfolio-organizer-v4/scripts/extract_and_classify.py \
  --input-dir contract-portfolio-organizer-v4/tests/fixtures/pdfs \
  --output   contract-portfolio-organizer-v4/tests/actual/manifest.json \
  --verbose

# Pass/fail matrix
python contract-portfolio-organizer-v4/tests/diff_expected.py \
  --manifest contract-portfolio-organizer-v4/tests/actual/manifest.json
```

Expected output: `PASS=15 FAIL=2 INFO=8 MISS=0`. The 2 FAILs (`B01_clean_msa`,
`R05_multi_party_four`) are the **deferred** Highs documented above.

For scale numbers, the same generator accepts `--scale N` to drop *N* additional
synthetic PDFs into `tests/fixtures/pdfs/` (or pass `--scale-only` and a custom
`PDF_DIR` to keep them out of the small-corpus matrix).

---

## Files added by this audit

```
contract-portfolio-organizer-v4/
├── STRESS_TEST_REPORT.md                          (this file)
└── tests/
    ├── diff_expected.py
    ├── fixtures/
    │   ├── build_fixtures.py
    │   ├── pdfs/                                  (25 PDFs, ~250 KiB total)
    │   └── expected/                              (25 YAML sidecars)
    └── actual/                                    (gitignored — generated)
```
