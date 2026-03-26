#!/usr/bin/env python3
"""
T9 OS script
CLAUDE.md pipeline vs T9OS/pipes/ compare
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # T9OS/
ROOT = os.path.dirname(BASE)  # HANBEEN/
CLAUDE_MD = os.path.join(ROOT, "CLAUDE.md")
PIPES_DIR = os.path.join(BASE, "pipes")
LIB_DIR = os.path.join(BASE, "lib")


def get_registered_files():
    """CLAUDE.md pipeline tableregisterfile extract"""
    registered = {}
    with open(CLAUDE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    # pipeline tablefileextract
    # pattern: `T9OS/pipes/xxx.py` `T9OS/lib/xxx.py` `T9OS/t9_seed.py`
    pattern = r"`T9OS/((?:pipes|lib)/[\w.]+|t9_seed\.py)`"
    for m in re.finditer(pattern, content):
        path = m.group(1)
        registered[path] = True

    return registered


def get_actual_files():
    """T9OS/pipes/ T9OS/lib/ .py file list"""
    actual = {}

    for dirname, prefix in [(PIPES_DIR, "pipes"), (LIB_DIR, "lib")]:
        if not os.path.isdir(dirname):
            continue
        for f in os.listdir(dirname):
            if (f.endswith(".py") or f.endswith(".sh")) and f != "__init__.py":
                actual[f"{prefix}/{f}"] = True

    # t9_seed.py
    if os.path.isfile(os.path.join(BASE, "t9_seed.py")):
        actual["t9_seed.py"] = True

    return actual


def main():
    if not os.path.isfile(CLAUDE_MD):
        print(f"ERROR: CLAUDE.md not found at {CLAUDE_MD}")
        sys.exit(1)

    registered = get_registered_files()
    actual = get_actual_files()

    all_keys = sorted(set(list(registered.keys()) + list(actual.keys())))

    errors = []
    warnings = []
    ok = []

    for key in all_keys:
        in_reg = key in registered
        in_actual = key in actual

        if in_reg and in_actual:
            ok.append(key)
        elif in_reg and not in_actual:
            errors.append(key)
        elif not in_reg and in_actual:
            warnings.append(key)

    # output
    print("=" * 60)
    print("T9 OS result")
    print("=" * 60)

    total = len(all_keys)
    matched = len(ok)
    score = int(matched / total * 100) if total > 0 else 0

    print(f"\nscore: {score}% ({matched}/{total})")
    print()

    if ok:
        print(f"OK ({len(ok)}items) — CLAUDE.md register + file :")
        for f in ok:
            print(f"  [OK] {f}")

    if errors:
        print(f"\nERROR ({len(errors)}items) — CLAUDE.mdregisterfile not found:")
        for f in errors:
            print(f"  [ERROR] {f}")

    if warnings:
        print(f"\nWARNING ({len(warnings)}items) — file CLAUDE.md register:")
        for f in warnings:
            print(f"  [WARNING] {f}")

    print()
    print("=" * 60)

    # exit 1
    if errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
