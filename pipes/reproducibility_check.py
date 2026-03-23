#!/usr/bin/env python3
"""
T9 OS 재현성 체크 스크립트
CLAUDE.md 파이프라인 레지스트리 vs 실제 T9OS/pipes/ 디렉토리 비교
"""
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # T9OS/
ROOT = os.path.dirname(BASE)  # WORKSPACE/
CLAUDE_MD = os.path.join(ROOT, "CLAUDE.md")
PIPES_DIR = os.path.join(BASE, "pipes")
LIB_DIR = os.path.join(BASE, "lib")


def get_registered_files():
    """CLAUDE.md 파이프라인 레지스트리 테이블에서 등록된 파일 추출"""
    registered = {}
    with open(CLAUDE_MD, "r", encoding="utf-8") as f:
        content = f.read()

    # 파이프라인 레지스트리 테이블에서 파일명 추출
    # 패턴: `T9OS/pipes/xxx.py` 또는 `T9OS/lib/xxx.py` 또는 `T9OS/t9_seed.py`
    pattern = r"`T9OS/((?:pipes|lib)/[\w.]+|t9_seed\.py)`"
    for m in re.finditer(pattern, content):
        path = m.group(1)
        registered[path] = True

    return registered


def get_actual_files():
    """T9OS/pipes/ 와 T9OS/lib/ 에서 실제 .py 파일 목록"""
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

    # 출력
    print("=" * 60)
    print("T9 OS 재현성 체크 결과")
    print("=" * 60)

    total = len(all_keys)
    matched = len(ok)
    score = int(matched / total * 100) if total > 0 else 0

    print(f"\n재현성 점수: {score}% ({matched}/{total})")
    print()

    if ok:
        print(f"OK ({len(ok)}건) — CLAUDE.md 등록 + 파일 존재:")
        for f in ok:
            print(f"  [OK] {f}")

    if errors:
        print(f"\nERROR ({len(errors)}건) — CLAUDE.md에 등록됐으나 파일 없음:")
        for f in errors:
            print(f"  [ERROR] {f}")

    if warnings:
        print(f"\nWARNING ({len(warnings)}건) — 파일 있으나 CLAUDE.md 미등록:")
        for f in warnings:
            print(f"  [WARNING] {f}")

    print()
    print("=" * 60)

    # 에러가 있으면 exit 1
    if errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
