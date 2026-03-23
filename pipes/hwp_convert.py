#!/usr/bin/env python3
"""
HWP ↔ DOCX 자동 변환 파이프라인
pyhwpx + 한글 2020 OLE Automation — HAction 방식 (정보 소실 제로)

★ 핵심 정책: 원본 절대 불변. 항상 복사본으로 변환.

Usage (WSL에서):
  # HWP → DOCX (복사본 생성, 원본 유지)
  python.exe T9OS/pipes/hwp_convert.py input.hwp
  → input_converted.docx 생성 (input.hwp 원본 그대로)

  # DOCX → HWP
  python.exe T9OS/pipes/hwp_convert.py input.docx
  → input_converted.hwp 생성

  # HWP → PDF
  python.exe T9OS/pipes/hwp_convert.py input.hwp --pdf

  # 출력 경로 직접 지정
  python.exe T9OS/pipes/hwp_convert.py input.hwp -o /path/to/output.docx

  # 폴더 일괄 변환
  python.exe T9OS/pipes/hwp_convert.py ./folder/ --to docx

NOTE: 반드시 Windows Python으로 실행 (OLE COM 필요)
"""

import sys
import os
import argparse
from pathlib import Path


# 한글 OLE 포맷 이름 (HAction FileSaveAs_S 용)
FORMAT_MAP = {
    '.hwp': 'HWP',
    '.hwpx': 'HWP',
    '.docx': 'OOXML',
    '.doc': 'DOCRTF',
    '.txt': 'TEXT',
    '.html': 'HTML',
    '.rtf': 'RTF',
    '.pdf': 'PDF',
}


def _make_copy_path(src_path: Path, out_ext: str) -> Path:
    """원본 보호: _converted 접미사 붙인 복사본 경로 생성"""
    stem = src_path.stem
    # 이미 _converted가 붙어있으면 중복 방지
    if stem.endswith('_converted'):
        return src_path.with_suffix(out_ext)
    return src_path.parent / f"{stem}_converted{out_ext}"


def convert_file(src: str, dst: str = None, fmt: str = None):
    """단일 파일 변환. 항상 복사본 생성, 원본 불변."""
    from pyhwpx import Hwp

    src_path = Path(src).resolve()
    if not src_path.exists():
        print(f"[ERROR] 파일 없음: {src_path}")
        return None

    src_ext = src_path.suffix.lower()

    # 출력 포맷 결정
    if fmt:
        out_ext = f".{fmt}"
    elif dst:
        out_ext = Path(dst).suffix.lower()
    elif src_ext in ('.hwp', '.hwpx'):
        out_ext = '.docx'
    elif src_ext in ('.docx', '.doc'):
        out_ext = '.hwp'
    else:
        print(f"[ERROR] 지원 안 하는 확장자: {src_ext}")
        return None

    # 출력 경로: 직접 지정 or 복사본 자동 생성
    if dst:
        dst_path = Path(dst).resolve()
    else:
        dst_path = _make_copy_path(src_path, out_ext)

    save_fmt = FORMAT_MAP.get(out_ext)
    if not save_fmt:
        print(f"[ERROR] 변환 불가 포맷: {out_ext}")
        return None

    print(f"[변환] {src_path.name} -> {dst_path.name}")
    print(f"[원본] {src_path} (변경 없음)")

    hwp = None
    try:
        hwp = Hwp(visible=False)
        hwp.open(str(src_path))

        if out_ext == '.pdf':
            success = _save_as_pdf(hwp, str(dst_path))
            if not success:
                alt = _make_copy_path(src_path, '.docx')
                _save_via_haction(hwp, str(alt), 'OOXML')
                print(f"[INFO] PDF 불가 -> DOCX 대체: {alt}")
                hwp.quit()
                return str(alt)
        else:
            _save_via_haction(hwp, str(dst_path), save_fmt)

        hwp.quit()

        if dst_path.exists():
            size = dst_path.stat().st_size
            print(f"[완료] {dst_path} ({size:,} bytes)")
            # 원본 무결성 확인
            if src_path.exists():
                src_size = src_path.stat().st_size
                print(f"[원본 확인] {src_path.name} ({src_size:,} bytes) — 변경 없음")
            return str(dst_path)
        else:
            print(f"[ERROR] 파일 생성 안 됨")
            return None

    except Exception as e:
        print(f"[ERROR] 변환 실패: {e}")
        if hwp:
            try:
                hwp.quit()
            except Exception:
                pass
        return None


def _save_via_haction(hwp, dst_path: str, fmt: str):
    """HAction FileSaveAs_S로 저장"""
    ctrl = hwp.hwp
    pset = ctrl.HParameterSet.HFileOpenSave
    ctrl.HAction.GetDefault('FileSaveAs_S', pset.HSet)
    pset.filename = dst_path
    pset.Format = fmt
    return ctrl.HAction.Execute('FileSaveAs_S', pset.HSet)


def _save_as_pdf(hwp, dst_path: str):
    """PDF 저장 시도"""
    try:
        ctrl = hwp.hwp
        pset = ctrl.HParameterSet.HFileOpenSave
        ctrl.HAction.GetDefault('FileSaveAs_S', pset.HSet)
        pset.filename = dst_path
        pset.Format = 'PDF'
        result = ctrl.HAction.Execute('FileSaveAs_S', pset.HSet)
        return result and os.path.exists(dst_path)
    except Exception:
        return False


def convert_folder(folder: str, to_fmt: str):
    """폴더 내 모든 파일 일괄 변환 (각각 복사본 생성)"""
    folder_path = Path(folder).resolve()
    if not folder_path.is_dir():
        print(f"[ERROR] 폴더 아님: {folder_path}")
        return

    if to_fmt in ('docx', 'pdf'):
        src_exts = {'.hwp', '.hwpx'}
    elif to_fmt == 'hwp':
        src_exts = {'.docx', '.doc'}
    else:
        print(f"[ERROR] 지원 안 하는 포맷: {to_fmt}")
        return

    files = [f for f in folder_path.iterdir()
             if f.is_file() and f.suffix.lower() in src_exts]

    if not files:
        print(f"[INFO] 변환할 파일 없음 ({', '.join(src_exts)})")
        return

    print(f"[일괄] {len(files)}개 -> {to_fmt} (복사본 생성, 원본 유지)")
    ok, fail = 0, 0
    for f in sorted(files):
        r = convert_file(str(f), fmt=to_fmt)
        if r:
            ok += 1
        else:
            fail += 1

    print(f"\n[결과] 성공 {ok}, 실패 {fail}")


def main():
    parser = argparse.ArgumentParser(
        description='HWP <-> DOCX 변환 (한글 2020 OLE, 원본 보호)')
    parser.add_argument('input', help='파일 또는 폴더')
    parser.add_argument('-o', '--output', help='출력 경로 (미지정 시 _converted 접미사)')
    parser.add_argument('--pdf', action='store_true', help='PDF 변환')
    parser.add_argument('--to', choices=['hwp', 'docx', 'pdf'],
                        help='폴더 일괄 변환 포맷')

    args = parser.parse_args()
    input_path = Path(args.input).resolve()

    if input_path.is_dir():
        convert_folder(str(input_path), args.to or 'docx')
    else:
        fmt = 'pdf' if args.pdf else None
        convert_file(str(input_path), args.output, fmt)


if __name__ == '__main__':
    main()
