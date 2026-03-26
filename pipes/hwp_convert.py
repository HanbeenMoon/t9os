#!/usr/bin/env python3
"""
HWP ↔ DOCX auto convert pipeline
pyhwpx + 2020 OLE Automation — HAction ()

★ : original . copyconvert.

Usage (WSL):
  # HWP → DOCX (copycreate, original )
  python.exe T9OS/pipes/hwp_convert.py input.hwp
  → input_converted.docx create (input.hwp original )

  # DOCX → HWP
  python.exe T9OS/pipes/hwp_convert.py input.docx
  → input_converted.hwp create

  # HWP → PDF
  python.exe T9OS/pipes/hwp_convert.py input.hwp --pdf

  # output path
  python.exe T9OS/pipes/hwp_convert.py input.hwp -o /path/to/output.docx

  # folder convert
  python.exe T9OS/pipes/hwp_convert.py ./folder/ --to docx

NOTE: Windows Pythonexecution (OLE COM )
"""

import sys
import os
import argparse
from pathlib import Path


# OLE name (HAction FileSaveAs_S )
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
    """original : _converted copypath create"""
    stem = src_path.stem
    # _convertedduplicate
    if stem.endswith('_converted'):
        return src_path.with_suffix(out_ext)
    return src_path.parent / f"{stem}_converted{out_ext}"


def convert_file(src: str, dst: str = None, fmt: str = None):
    """file convert. copycreate, original ."""
    from pyhwpx import Hwp

    src_path = Path(src).resolve()
    if not src_path.exists():
        print(f"[ERROR] file not found: {src_path}")
        return None

    src_ext = src_path.suffix.lower()

    # output
    if fmt:
        out_ext = f".{fmt}"
    elif dst:
        out_ext = Path(dst).suffix.lower()
    elif src_ext in ('.hwp', '.hwpx'):
        out_ext = '.docx'
    elif src_ext in ('.docx', '.doc'):
        out_ext = '.hwp'
    else:
        print(f"[ERROR] : {src_ext}")
        return None

    # output path: or copyauto create
    if dst:
        dst_path = Path(dst).resolve()
    else:
        dst_path = _make_copy_path(src_path, out_ext)

    save_fmt = FORMAT_MAP.get(out_ext)
    if not save_fmt:
        print(f"[ERROR] convert : {out_ext}")
        return None

    print(f"[convert] {src_path.name} -> {dst_path.name}")
    print(f"[original] {src_path} (change not found)")

    hwp = None
    try:
        hwp = Hwp(visible=False)
        hwp.open(str(src_path))

        if out_ext == '.pdf':
            success = _save_as_pdf(hwp, str(dst_path))
            if not success:
                alt = _make_copy_path(src_path, '.docx')
                _save_via_haction(hwp, str(alt), 'OOXML')
                print(f"[INFO] PDF -> DOCX : {alt}")
                hwp.quit()
                return str(alt)
        else:
            _save_via_haction(hwp, str(dst_path), save_fmt)

        hwp.quit()

        if dst_path.exists():
            size = dst_path.stat().st_size
            print(f"[completed] {dst_path} ({size:,} bytes)")
            # original integrity check
            if src_path.exists():
                src_size = src_path.stat().st_size
                print(f"[original check] {src_path.name} ({src_size:,} bytes) — change not found")
            return str(dst_path)
        else:
            print(f"[ERROR] file create ")
            return None

    except Exception as e:
        print(f"[ERROR] convert failed: {e}")
        if hwp:
            try:
                hwp.quit()
            except Exception:
                pass
        return None


def _save_via_haction(hwp, dst_path: str, fmt: str):
    """HAction FileSaveAs_Ssave"""
    ctrl = hwp.hwp
    pset = ctrl.HParameterSet.HFileOpenSave
    ctrl.HAction.GetDefault('FileSaveAs_S', pset.HSet)
    pset.filename = dst_path
    pset.Format = fmt
    return ctrl.HAction.Execute('FileSaveAs_S', pset.HSet)


def _save_as_pdf(hwp, dst_path: str):
    """PDF save """
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
    """folder file convert (copycreate)"""
    folder_path = Path(folder).resolve()
    if not folder_path.is_dir():
        print(f"[ERROR] folder : {folder_path}")
        return

    if to_fmt in ('docx', 'pdf'):
        src_exts = {'.hwp', '.hwpx'}
    elif to_fmt == 'hwp':
        src_exts = {'.docx', '.doc'}
    else:
        print(f"[ERROR] : {to_fmt}")
        return

    files = [f for f in folder_path.iterdir()
             if f.is_file() and f.suffix.lower() in src_exts]

    if not files:
        print(f"[INFO] convertfile not found ({', '.join(src_exts)})")
        return

    print(f"[] {len(files)}-> {to_fmt} (copycreate, original )")
    ok, fail = 0, 0
    for f in sorted(files):
        r = convert_file(str(f), fmt=to_fmt)
        if r:
            ok += 1
        else:
            fail += 1

    print(f"\n[result] success {ok}, failed {fail}")


def main():
    parser = argparse.ArgumentParser(
        description='HWP <-> DOCX convert ( 2020 OLE, original )')
    parser.add_argument('input', help='file  folder')
    parser.add_argument('-o', '--output', help='output path (  _converted )')
    parser.add_argument('--pdf', action='store_true', help='PDF convert')
    parser.add_argument('--to', choices=['hwp', 'docx', 'pdf'],
                        help='folder  convert ')

    args = parser.parse_args()
    input_path = Path(args.input).resolve()

    if input_path.is_dir():
        convert_folder(str(input_path), args.to or 'docx')
    else:
        fmt = 'pdf' if args.pdf else None
        convert_file(str(input_path), args.output, fmt)


if __name__ == '__main__':
    main()
