# Contributing to T9 OS

T9 OS is a solo philosophical project, but thoughtful contributions are welcome.

## How to Contribute

1. **Open an Issue first** — describe what you want to change and why
2. **Fork and branch** — work on your own copy
3. **Submit a PR** — reference the issue

## What matters here

This is not a typical software project. The philosophy (Simondon's individuation theory) is as important as the code. If you are proposing a change to the constitution (`constitution/`) or the state machine, explain how it relates to the underlying philosophy.

## Development Setup

```bash
git clone https://github.com/HanbeenMoon/t9os.git
cd t9os
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
t9 --help       # verify CLI works
pytest           # run tests
ruff check .     # lint
```

## Code Style

- Python 3.10+
- Keep it simple — this was built by a non-CS-major
- `except Exception` not bare `except`
- No hardcoded secrets — use `t9os.lib.config`
- All code and comments in English
- Package imports: `from t9os.lib.config import ...` (not `from lib.config`)

## Questions?

Open a Discussion or Issue. There are no stupid questions here.
