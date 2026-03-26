# T9 OS Deploy Checklist
# ADR-058: Don't just implement — deploy and verify.

> "Writing code = 30%. Testing + deploying + verifying = the other 70%."

---

## 1. Any Code Change

- [ ] `safe_change.sh snapshot` executed (auto: post-tool-use hook)
- [ ] Smoke test 37/37 PASS
- [ ] verify_claims 10/10 VERIFIED (on CONSTITUTION_CHANGE)

## 2. New Pipeline Addition

- [ ] SRBB confirmed (Orient layer auto-triggers)
- [ ] Registered in `lib/registry.py`
- [ ] `CLAUDE.md` pipeline registry table updated
- [ ] If cron-based: added to `cron_runner.sh` + crontab
- [ ] Smoke test updated with file existence check

## 3. Constitution / Core Document Change

- [ ] Orient layer confirmed (L1/L2 = block, retry required)
- [ ] Three-location simultaneous update: L1/L2 + CLAUDE.md + memory
- [ ] Quantitative claims verified (`verify_claims.py`)

## 4. Deployment (Vercel / systemd / cron)

- [ ] Local execution verified (1 run + exit code 0)
- [ ] Deployment executed
- [ ] Post-deploy service response confirmed
- [ ] Healthcheck passing
- [ ] Telegram notification confirmed (if applicable)

## 5. Session End

- [ ] `safe_change.sh verify` (auto: session-end hook)
- [ ] Key work registered via `t9_seed.py capture`
- [ ] ADR written if needed (or `adr_auto.py` auto-generates)

---

## Automation Status

| Item | Automated | Manual |
|------|-----------|--------|
| Snapshot | post-tool-use (on first edit) | `safe_change.sh snapshot` |
| Smoke test | session-start (warns on FAIL) | `python3 tests/smoke_test.py` |
| Verify | session-end | `safe_change.sh verify` |
| Claims | manual | `python3 tests/verify_claims.py` |
| Orient layer | PreToolUse hook | — |
| Registry update | manual | `lib/registry.py` edit |
| ADR | session-end (`adr_auto.py`) | direct authoring |
