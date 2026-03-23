# T9 OS Policy Hooks

T9 OS uses Claude Code's **PreToolUse hooks** to enforce governance rules automatically. Every tool call Claude Code makes — file edits, bash commands, writes — passes through a policy layer before execution.

## How It Works

```
User request
    ↓
Claude Code decides to use a tool (Bash, Edit, Write, etc.)
    ↓
PreToolUse hook intercepts the call
    ↓
┌─────────────────────────────────────┐
│  Hard Gate (pre-tool-hard-gate.sh)  │
│  Static rules. No exceptions.       │
│  exit 0 → allow                     │
│  exit 2 → block                     │
└──────────────┬──────────────────────┘
               ↓ (if allowed)
┌─────────────────────────────────────┐
│  Soft Gate (LLM-based judgment)     │
│  Dynamic rules. Context-dependent.  │
│  Philosophy alignment, build/buy,   │
│  quality checks.                    │
└──────────────┬──────────────────────┘
               ↓ (if allowed)
Tool executes normally
```

## Two Types of Gates

### Hard Gates (Static — "Physics")

Hard gates are bash scripts that block dangerous operations unconditionally. They don't consider context or intent. If the pattern matches, the action is blocked.

**What they block:**
- `rm -rf /` and similar destructive deletions
- `git push --force` to main/master
- `git reset --hard`
- Access to sensitive files (credentials, API keys, `.env` files)
- Direct modification of the database (must go through the seed engine)
- Editing files claimed by another session

### Soft Gates (Dynamic — "Law")

Soft gates use LLM judgment to evaluate actions against project principles:
- **Build vs Buy decisions** — should we write this or use an existing tool?
- **Philosophy alignment** — does this change respect the project's Simondonian foundations?
- **Quality checks** — is this ready for commit/deploy?

## Example: Hard Gate Script

Here is a sanitized version of the hard gate hook. Place this at `.claude/hooks/pre-tool-hard-gate.sh` and configure it in `.claude/settings.json`.

```bash
#!/usr/bin/env bash
# PreToolUse hook: hard gate
# exit 0 = allow, exit 2 = block

set -euo pipefail

# Read hook input (JSON on stdin)
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | python3 -c \
  "import sys,json; print(json.load(sys.stdin).get('tool_name',''))" \
  2>/dev/null || echo "")
TOOL_INPUT=$(echo "$INPUT" | python3 -c \
  "import sys,json; print(json.dumps(json.load(sys.stdin).get('tool_input',{})))" \
  2>/dev/null || echo "{}")

# ── Rule 1: Block dangerous bash commands ──
if [ "$TOOL_NAME" = "Bash" ]; then
    COMMAND=$(echo "$TOOL_INPUT" | python3 -c \
      "import sys,json; print(json.load(sys.stdin).get('command',''))" \
      2>/dev/null || echo "")

    # Block recursive force-delete
    if echo "$COMMAND" | grep -qE 'rm\s+(-[a-zA-Z]*r[a-zA-Z]*f|--recursive)\s+/[^/]'; then
        echo '{"decision":"block","reason":"Hard gate: destructive rm blocked"}'
        exit 2
    fi

    # Block force push to main
    if echo "$COMMAND" | grep -qE 'git\s+push\s+.*--force|git\s+push\s+-f'; then
        if echo "$COMMAND" | grep -qE 'main|master'; then
            echo '{"decision":"block","reason":"Hard gate: force push to main blocked"}'
            exit 2
        fi
    fi

    # Block git reset --hard
    if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
        echo '{"decision":"block","reason":"Hard gate: git reset --hard blocked"}'
        exit 2
    fi

    # Block access to sensitive files
    if echo "$COMMAND" | grep -qE 'credentials|\.env|api[._]key'; then
        echo '{"decision":"block","reason":"Hard gate: sensitive file access blocked"}'
        exit 2
    fi
fi

# ── Rule 2: Block edits to sensitive files ──
if [ "$TOOL_NAME" = "Edit" ] || [ "$TOOL_NAME" = "Write" ]; then
    FILE_PATH=$(echo "$TOOL_INPUT" | python3 -c \
      "import sys,json; print(json.load(sys.stdin).get('file_path',''))" \
      2>/dev/null || echo "")

    # Block credential directories
    if echo "$FILE_PATH" | grep -qE 'secrets/|credentials/|\.env$'; then
        echo '{"decision":"block","reason":"Hard gate: sensitive file edit blocked"}'
        exit 2
    fi

    # Block direct DB modification
    if echo "$FILE_PATH" | grep -qE '\.db$'; then
        echo '{"decision":"block","reason":"Hard gate: direct DB edit blocked. Use the API."}'
        exit 2
    fi
fi

# ── All checks passed ──
exit 0
```

## Configuring Hooks

Register hooks in `.claude/settings.json`:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": ".claude/hooks/pre-tool-hard-gate.sh"
          }
        ]
      }
    ]
  }
}
```

The empty `matcher` string means this hook runs on **every** tool call. You can also target specific tools:

```json
{
  "matcher": "Bash",
  "hooks": [{ "type": "command", "command": ".claude/hooks/bash-gate.sh" }]
}
```

## Design Principles

1. **Hard gates are physics, not policy.** They never change based on context. If `rm -rf /` is blocked, it is always blocked, no matter how good the reason sounds.

2. **Soft gates are living law.** They adapt based on project context, current goals, and accumulated decisions (ADRs). The LLM evaluates intent, not just pattern.

3. **Fail closed.** If the hook script errors out (`set -euo pipefail`), the tool call is blocked by default. Safety over convenience.

4. **The human sets direction, the system enforces it.** Hooks encode the designer's values so the AI operates within them autonomously, without asking for permission on every action.
