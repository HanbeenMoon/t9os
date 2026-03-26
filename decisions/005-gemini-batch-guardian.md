# ADR-005: Gemini Batch for Guardian Execution

- Date: 2026-03-16
- Status: Accepted
- Decision: Run guardian sub-reviewers via Gemini API batch (`gm_batch.py guardian`). The control tower (cc) serves as guardian chief — aggregating results and making P0 decisions only.
- Rationale: cc (Claude Code) tokens are expensive and limited. Running 21 guardian reviewers on cc tokens would starve actual work. Gemini 3 Flash / 3.1 Pro is free or near-free, optimized for bulk review.
- Outcome: `pipes/gm_batch.py` with `--mode light|default|full`

## Simondon Mapping
Division of labor between tools mirrors concretization — each tool converges on its optimal function rather than one tool doing everything abstractly.
