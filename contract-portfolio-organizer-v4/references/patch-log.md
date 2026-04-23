# Patch Log — Contract Portfolio Organizer

Historical record of patches applied during validation rounds. 20 patches across 4 rounds (v2 through v4-15), validated against 73 contracts, 16 customers, 94 test assertions → 99% pass rate.

## Patch Summary Table

| # | Patch | Category | Root Cause | Fix |
|---|---|---|---|---|
| 1 | v2-1 | Classification | Body text contaminated header matching | Two-pass: header-only first, body fallback second |
| 2 | v2-2 | Classification | Regex priority allowed false matches | Reordered: Equipment Bailment before Amendment; LOI before NDA; Interim before MSA |
| 3 | v2-3 | Linking | `[^,)]` stopped at comma in "dated Oct 23, 2015" | Changed to `[^()]*?\d{4}` — captures through comma |
| 4 | v2-4 | Linking | Missing reference patterns | Added: "entered into", "parties to", "amends the", fallback-to-parenthesis |
| 5 | v3-5 | Classification | "Amendment No. 1 to A&R MSA" classified as A&R MSA | Moved Amendment before A&R MSA (safe with header-first) |
| 6 | v3-6 | Linking | Sub-SOW linked to MSA instead of SOW | Two-pass linking + child-first preference for child_l2 |
| 7 | v3-7 | Linking | "under X pursuant to Y" extracted Y (grandparent) | "under" pattern before "pursuant to" |
| 8 | v4-8 | Entity Res | DBA/trade names not resolved | DBA extraction + alias map in entity resolution |
| 9 | v4-1 | Classification | Ordinals stopped at "tenth" | Extended through "twentieth" + all `\d+(?:st|nd|rd|th)` |
| 10 | v4-2 | Classification | "Amendment and Waiver" not matched | Added compound forms: "amendment and (waiver|restatement|release)" |
| 11 | v4-3 | Classification | Bare "ADDENDUM" missed | Relaxed to `(?<!\w)addendum(?!\w)` |
| 12 | v4-4 | Classification | "Master Services Agreement" not matched | Added "master" to MSA regex |
| 13 | v4-5 | Classification | "Confidential Disclosure Agreement" not matched | Added CDA to NDA regex |
| 14 | v4-7 | Classification | No-title docs false-classified as MSA from body text | Body pass skips parent types when no header found |
| 15 | v4-9 | Supersession | 2nd A&R didn't supersede 1st A&R | Check `parent_superseding` role + process newest-first |
| 16 | v4-10 | Supersession | Full-text date matching caused false positives | Targeted "supersedes/replaces" extraction only |
| 17 | v4-11 | Title Extraction | Sentence-case lines picked up as titles | First title line requires ALL-CAPS (>60% uppercase) |
| 18 | v4-12 | Linking | Ref capture overshot through parentheticals | `.{5,100}?dated` + `[^()]*?\d{4}` + 120-char max |
| 19 | v4-14 | Linking | "under the MSA, Flex shall..." body text matched | "under" now requires qualifier (and governed by\|that certain) |
| 20 | v4-15 | Title Extraction | Signature block matched as title | Reject `___`/`By:` lines + limit scan to 8 non-empty lines |

## v5 Improvements (Current)

The v5 release incorporated 22 additional improvements based on stress testing and edge case analysis:

- **Scanned PDF detection** with OCR fallback guidance
- **Non-English contract detection** with language warnings
- **Flexible title extraction** accepting Title-Case headers (with lower confidence scores)
- **Expanded TYPE_MAP** adding Supply Agreement, Framework Agreement, GTC, Sourcing Agreement, Cooperation Agreement, PO Terms, Assignment/Novation
- **Extended amendment ordinals** through hyphenated compounds ("twenty-first" through "twenty-ninth")
- **Removed "dated" anchor dependency** by adding "effective as of" capture patterns
- **Fuzzy entity matching** using SequenceMatcher ratio >0.85
- **Keyword stop-word list** for linking to prevent common-word false matches
- **Confidence scoring** across title extraction, parent reference matching, entity resolution, and linking
- **Multi-party contract support** (3+ parties in schema)
- **Assignment/novation tracking** as new contract type
- **Expiration date and term extraction** with renewal detection
- **Financial term extraction** (contract value, liability cap, payment terms)
- **_INDEX.json schema** fully defined
- **Per-file error recovery** — never crash the batch for one bad PDF
- **Near-duplicate detection** via text similarity scoring
- **Bundled extraction script** (`scripts/extract_and_classify.py`) for deterministic pipeline
- **Consistent visualization templates** — all four deliverables equally specified
- **Scale guidance** for portfolios >100 contracts
- **Arbitrary-depth supersession chains** (not just double)
- **Incremental update model** for adding contracts to existing portfolios

## Context Window Rationale

These 20 patches were extracted from the main SKILL.md and placed in this reference document to:

1. **Preserve historical accuracy** — Document the validation journey from v2 → v4
2. **Reduce SKILL.md size** — Main file now focuses on current (v5) implementation
3. **Enable cross-reference** — Other team members can trace root causes and understand design decisions
4. **Inform future patches** — Pattern recognition on what kinds of bugs appear (classification > linking > entity resolution by frequency)

Each patch was validated against the corresponding test contract set before release.
