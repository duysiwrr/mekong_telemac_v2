#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C_assign_boundaries.py — GAN BIEN THUC DO 2011 vao 9 file .loi

Thay bien tam (trieu sin) bang so lieu THUC DO, va cap nhat tempsMax/pasTemps
trong mascaret.xcas cho khop chuoi bien.

KHONG lam init.lig — viec do CUA `C_init_smart.py`.
  Ban dau script nay co ham rebuild_init_smart() copy tu 24d2 (V1), dung
  cong thuc `frac = bief / bmax` -> Z doc theo SO THU TU bief. V1 danh so
  bief xuoi dong nen tinh co dung; v2 danh so theo sorted(mike) = ALPHABET
  (BASSAC->Bief_1, VamNao->Bief_15) -> Vam Nao o giua mang bi gan Z thap
  nhat -> chenh 5.6m tai nut N1 -> "Cross Section is dry".
  -> DA GO BO. C_init_smart.py lan truyen Z bang BFS topology tu cua bien.

QUY TRINH DUNG:
  B_build_grid.py  ->  C_assign_boundaries.py  ->  C_init_smart.py
                       (bien .loi + xcas)          (init.lig)
                                                ->  D_run_eval.py

MAP BIEN -> TRAM (bang BND, xac minh bang toa do trong catalog):
  Q_TanChau <- Q_TanChau | Q_ChauDoc <- Q_ChauDoc
  Z_CuaTieu/CuaDai   <- H_VamKenh
  Z_HamLuong         <- H_AnThuan
  Z_CuaCoChien/CungHau <- H_BenTrai
  Z_CuaDinhAn/TranDe <- H_TranDe

DUNG:
  python3 src/C_assign_boundaries.py --outdir output/grid/backbone \
      --start 2011-10-01 --end 2011-10-31
"""
import argparse
import re
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

# (ten bien v2, nguon 'Q'|'H', ten cot OBS, typeLoi) — theo BND cua 24d2
BND = [
    ("Q_TanChau",         "Q", "Q_TanChau", 1),
    ("Q_ChauDoc",         "Q", "Q_ChauDoc", 1),
    ("Z_CuaTieu_16",      "H", "H_VamKenh", 2),
    ("Z_CuaDai_12",       "H", "H_VamKenh", 2),
    ("Z_Ham_Luong_20",    "H", "H_AnThuan", 2),
    ("Z_CuaCoChien_8",    "H", "H_BenTrai", 2),
    ("Z_CuaCungHau_10",   "H", "H_BenTrai", 2),
    ("Z_CuaDinhAn_14",    "H", "H_TranDe",  2),
    ("Z_CuaTranDe_18",    "H", "H_TranDe",  2),
]


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def read_txt(path):
    """Doc file quan trac MIKE-export. Tra (cols, {colname: {datetime: val}})."""
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    header = re.split(r"\s+", lines[1].strip())
    cols = header[1:]
    data = {c: {} for c in cols}
    for l in lines[3:]:
        if not l.strip():
            continue
        parts = l.split("\t") if "\t" in l else re.split(r"\s{2,}", l.strip())
        if len(parts) < 2:
            continue
        try:
            t = datetime.strptime(parts[0].strip(), "%Y-%m-%d %H:%M:%S")
        except Exception:
            continue
        vals = re.split(r"\s+", " ".join(parts[1:]).strip())
        for j, c in enumerate(cols):
            if j < len(vals):
                try:
                    data[c][t] = float(vals[j])
                except Exception:
                    pass
    return cols, data


def find_col(cols, want):
    nw = norm(want)
    for c in cols:
        if norm(c) == nw:
            return c
    return None


def series_in_window(coldata, start, end):
    out = [((t - start).total_seconds(), v)
           for t, v in coldata.items() if start <= t <= end]
    out.sort(key=lambda x: x[0])
    return out


def write_loi(path, comment, unit_line, pairs):
    with open(path, "w", encoding="ascii") as f:
        f.write(f"# {comment}\n# {unit_line}\n S\n")
        for t, v in pairs:
            f.write(f" {t:.3f} {v:.3f}\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--q-txt", default=str(CFG.DATA.Q_OBS))
    ap.add_argument("--wl-txt", default=str(CFG.DATA.WL_OBS))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    out = Path(args.outdir)
    if not (out / "mascaret.xcas").exists():
        raise SystemExit(f"[LOI] khong thay {out}/mascaret.xcas — chay B_build_grid truoc")

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    dur = (end - start).total_seconds()

    print("=== GAN BIEN THUC DO + SMART INIT ===\n")

    print("Doc quan trac...")
    qcols, qdata = read_txt(args.q_txt)
    wcols, wdata = read_txt(args.wl_txt)
    print(f"  Q: {len(qcols)} cot | WL: {len(wcols)} cot\n")

    print("Gan 9 bien:")
    for name, src, srccol, typ in BND:
        cols, data = (qcols, qdata) if src == "Q" else (wcols, wdata)
        real = find_col(cols, srccol)
        if real is None:
            print(f"  [LOI] khong thay cot '{srccol}' cho bien {name}")
            print(f"        cot co: {cols}")
            raise SystemExit(1)
        ser = series_in_window(data[real], start, end)
        if len(ser) < 2:
            print(f"  [LOI] bien {name}: cot {real} khong co du lieu "
                  f"trong [{args.start},{args.end}]")
            raise SystemExit(1)
        unit = "Temps(S) Debit" if typ == 1 else "Temps(S) Cote"
        write_loi(out / f"{name}.loi", f"{name} <- {real}", unit, ser)
        v0 = ser[0][1]
        vmin = min(v for _, v in ser)
        vmax = max(v for _, v in ser)
        print(f"  {name:18s} <- {real:12s} : {len(ser):5d} diem, "
              f"dau={v0:8.2f}, min={vmin:8.2f}, max={vmax:8.2f}")

    # --- cap nhat xcas: tempsMax + pasTemps + pasStock (tham so 24d2) ---
    xp = out / "mascaret.xcas"
    x = xp.read_text(encoding="latin-1", errors="replace")
    x = re.sub(r"<tempsMax>[\d.eE+]+</tempsMax>", f"<tempsMax>{dur:.1f}</tempsMax>", x)
    x = re.sub(r"<pasTemps>[\d.eE+]+</pasTemps>", "<pasTemps>300.0</pasTemps>", x)
    x = re.sub(r"<pasStock>\d+</pasStock>", "<pasStock>12</pasStock>", x)
    x = re.sub(r"<pasTempsVar>true</pasTempsVar>", "<pasTempsVar>false</pasTempsVar>", x)
    xp.write_text(x, encoding="latin-1")
    print(f"\nxcas: tempsMax={dur:.0f}s ({dur/86400:.0f} ngay), pasTemps=300, pasStock=12")

    print(f"\nXONG. Tiep theo:")
    print(f"   python3 src/C_init_smart.py --outdir {out} "
          f"--z-sea 3.0 --slope 2.0 --h-min 8.0")


if __name__ == "__main__":
    main()
