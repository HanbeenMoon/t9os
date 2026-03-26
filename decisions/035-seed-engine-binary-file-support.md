# ADR-035: Seed Engine Binary File Parsing

- Date: 2026-03-16
- Status: Accepted
- Decision: Extend `t9_seed.py` reindex targets from markdown-only to docx, pdf, xlsx, txt, csv, log, images, and video. Parse content with python-docx/pymupdf/openpyxl and index full text in FTS5.
- Rationale: Preindividuals arrive in diverse formats. Restricting indexing to markdown loses potential from binary files.
- Outcome: `lib/parsers.py` with multi-format parsing, FTS5 full-body indexing

## Simondon Mapping
Expanding the preindividual field — more input formats mean more potential captured in the supersaturated solution.
