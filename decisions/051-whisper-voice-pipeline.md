# ADR-051: Voice Transcription Pipeline (faster-whisper)

- Date: 2026-03-16
- Status: Accepted
- Decision: Auto-transcribe Telegram voice messages via faster-whisper and register as preindividual entities in the seed engine.
- Rationale: Voice is the lowest-friction input modality. Transcription → entity capture closes the loop from voice to searchable knowledge.
- Outcome: `pipes/whisper_pipeline.py`

## Simondon Mapping
Expanding the preindividual field to include auditory input — more modalities mean richer potential.
