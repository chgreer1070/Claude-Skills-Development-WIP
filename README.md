# Claude-Skills-Development-WIP

Work-in-progress repository for developing Claude Agent Skills.

## Contents

- [`contract-portfolio-organizer-v4/`](contract-portfolio-organizer-v4/) — a Claude
  skill that ingests a directory of contract PDFs, extracts metadata (title, dates,
  parties, financial terms, parent references), classifies each document into a
  hierarchical taxonomy, resolves entity aliases via fuzzy matching, flags
  near-duplicates, and emits a structured `manifest.json` plus visualization
  templates. See its [`SKILL.md`](contract-portfolio-organizer-v4/SKILL.md) for the
  full specification.

## Quick start

```bash
# Use an isolated virtualenv so the system Python is untouched
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Run the extraction pipeline on a folder of PDFs
python contract-portfolio-organizer-v4/scripts/extract_and_classify.py \
  --input-dir <pdf_directory> --output manifest.json --verbose
```

`pytesseract` is an optional dependency used only as an OCR-availability probe;
the extractor flags scanned PDFs as `ocr_needed` but does not perform OCR itself.

## Tests

The skill ships with synthetic PDF fixtures and a pytest regression suite that
locks in extraction/classification behavior.

```bash
pip install pytest
pytest
```

To regenerate the fixture PDFs (only needed when changing the fixtures),
`reportlab` is also required:

```bash
pip install reportlab
python contract-portfolio-organizer-v4/tests/fixtures/build_fixtures.py
```

## Continuous integration

[`.github/workflows/python-app.yml`](.github/workflows/python-app.yml) runs flake8
(failing only on syntax/undefined-name errors `E9,F63,F7,F82`) and the pytest suite
on every push and pull request against `main` using Python 3.10.
