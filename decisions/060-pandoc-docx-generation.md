# ADR-060: Pandoc + Reference Doc for DOCX Generation

- Date: 2026-03-16
- Status: Accepted
- Decision: Standardize document generation on pandoc (Markdown → DOCX) with reference-doc for formatting. Ban python-docx code generation. Always output PDF alongside DOCX.
- Rationale: Code-generated Word tables break formatting. Template-based approaches (pandoc, reference-doc) are the Buy option per SRBB.
- Outcome: Pandoc pipeline, BibTeX + citeproc for references

## Simondon Mapping
SRBB — template-based generation is Reuse/Buy, not Build.
