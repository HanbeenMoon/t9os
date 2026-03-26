# ADR-070: Google Drive DriveFS Upload

- Date: 2026-03-23
- Status: Accepted
- Decision: Use Google Drive File Stream mount for file upload without OAuth re-authentication. `gdrive_upload.py` pipeline.
- Rationale: DriveFS provides zero-config file access. OAuth setup is a persistent friction point.
- Outcome: `pipes/gdrive_upload.py`

## Simondon Mapping
Concretization — eliminating authentication friction tightens tool integration.
