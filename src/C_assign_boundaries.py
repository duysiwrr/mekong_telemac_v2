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

# BAN CU hardcode so extremite ('Z_CuaTieu_16') -> CHET khi doi subset:
#   luoi 11 nhanh -> ext 16 | luoi 34 nhanh -> ext 68 -> ghi sai ten .loi
#   -> bien Z ma xcas dung van la TRIEU SIN GIA -> Erreur 701 (loi 6 playbook).
# BAN NAY doc ten bien THAT tu <string> trong mascaret.xcas, boc so duoi,
# roi tra theo TEN SONG. Quy luat anh xa bien->tram khong doi theo subset.
MAP_SONG = {
    "CuaTieu":    ("H", "H_VamKenh", 2),
    "CuaDai":     ("H", "H_VamKenh", 2),
    "Ham_Luong":  ("H", "H_AnThuan", 2),
    "HamLuong":   ("H", "H_AnThuan", 2),
    "CuaCoChien": ("H", "H_BenTrai", 2),
    "CuaCungHau": ("H", "H_BenTrai", 2),
    "CuaDinhAn":  ("H", "H_TranDe",  2),
    "CuaTranDe":  ("H", "H_TranDe",  2),
    # bien Q — ten khong co so duoi
    "TanChau":    ("Q", "Q_TanChau", 1),
    "ChauDoc":    ("Q", "Q_ChauDoc", 1),
}


def doc_bien_tu_xcas(outdir):
    """mascaret.xcas -> [(ten_bien, nguon, cot_obs, typeLoi)] theo dung thu tu.

    'Z_CuaTieu_68' -> boc 'Z_' + '_68' -> 'CuaTieu' -> tra MAP_SONG.
    'Q_TanChau'    -> boc 'Q_'         -> 'TanChau' -> tra MAP_SONG.
    """
    x = (Path(outdir) / "mascaret.xcas").read_text(encoding="latin-1",
                                                   errors="replace")
    m = re.search(r"<extrLibres>(.*?)</extrLibres>", x, re.S)
    if not m:
        raise SystemExit("[LOI] xcas khong co khoi <extrLibres>")
    noms = re.findall(r"<string>([^<]*)</string>", m.group(1))
    out, thieu = [], []
    for nom in noms:
        # boc tien to Z_/Q_ va hau to _<so>
        s = re.sub(r"^[ZQ]_", "", nom)
        s = re.sub(r"_\d+$", "", s)
        if s in MAP_SONG:
            src, col, typ = MAP_SONG[s]
            out.append((nom, src, col, typ))
        else:
            thieu.append(f"{nom} (-> '{s}')")
    if thieu:
        print(f"  [LOI] {len(thieu)} bien khong tra duoc trong MAP_SONG:")
        for t in thieu:
            print(f"        {t}")
        print(f"        MAP_SONG co: {sorted(MAP_SONG)}")
        raise SystemExit(1)
    return out


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

    BND = doc_bien_tu_xcas(out)
    print(f"Bien doc tu xcas: {len(BND)}")

    # --- DON .loi CU: file khong con trong xcas (doi subset -> doi so ext) ---
    can = {f"{n}.loi" for n, *_r in BND}
    du = [p for p in out.glob("*.loi") if p.name not in can]
    if du:
        print(f"  [!] xoa {len(du)} file .loi thua (khong con trong xcas):")
        print(f"      {sorted(p.name for p in du)}")
        for p in du:
            p.unlink()

    print(f"\nGan {len(BND)} bien:")
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

    # --- KIEM: moi bien xcas phai co .loi THUC DO (khong con sin gia) ---
    print("\nKiem file .loi:")
    loi = sorted(p.name for p in out.glob("*.loi"))
    thieu = [n for n, *_r in BND if f"{n}.loi" not in loi]
    sin = []
    for n, *_r in BND:
        p = out / f"{n}.loi"
        if p.exists():
            h = p.read_text(encoding="ascii", errors="replace").splitlines()[0]
            if "trieu sin" in h or "tam -" in h:
                sin.append(n)
    print(f"  {len(loi)} file .loi | xcas can {len(BND)} bien")
    if thieu:
        print(f"  [LOI] {len(thieu)} bien THIEU file .loi: {thieu}")
        raise SystemExit(1)
    if sin:
        print(f"  [LOI] {len(sin)} bien van la TRIEU SIN GIA: {sin}")
        raise SystemExit(1)
    print("  OK — moi bien deu co .loi thuc do, khong con sin gia")

    # slope goi y theo do sau mang (d_cua max) — luoi cang nhieu bief cang nho
    print(f"\nXONG. Tiep theo:")
    print(f"   python3 src/C_init_smart.py --outdir {out} "
          f"--z-sea 3.0 --slope <slope> --h-min 8.0")
    print(f"   (slope: chon sao cho z_sea + slope*d_cua_max ~ 9m."
          f" luoi 15 bief -> 2.0 | luoi 82 bief -> 0.55)")


if __name__ == "__main__":
    main()
