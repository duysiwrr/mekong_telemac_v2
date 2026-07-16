#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C_assign_boundaries.py — GAN BIEN THUC DO + SMART INIT

Thay 9 file .loi tam (trieu sin) bang so lieu THUC DO 2011, va dung lai
init.lig theo cong thuc SMART INIT cua ban 24d2 da chay FIN CORRECTE.

KHAC 24d2 O MOT DIEM (bat buoc):
  24d2 nhan dien cua bang "bief >= 9" — dung cho mang 71 bief danh so
  song-chinh-truoc-cua-sau. v2 danh so theo BACKBONE list nen nguong do SAI.
  Script nay doc mascaret.xcas, tim bief nao co extremite gan bien type Z
  -> do la cua. Chinh xac theo topology, khong phu thuoc thu tu.

CONG THUC (copy 24d2 rebuild_init_smart):
  - Song chinh: z = max(init_high - frac*(high-low), day+5.0)   [san chong kho]
  - Cua/phan luu: z = min(max(day+4.0, cua_floor), cua_level)

DUNG:
  python3 src/C_assign_boundaries.py --outdir output/grid/backbone \\
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


def find_cua_biefs(outdir):
    """Doc mascaret.xcas -> tap bief co extremite gan bien type Z (=cua).

    extremite: bief i chiem ext (2i-1, 2i). extrLibres cho biet ext nao tu do,
    typeCond=2 => bien Z => bief do la cua.
    """
    xcas = (outdir / "mascaret.xcas").read_text(encoding="latin-1", errors="replace")
    m_ext = re.search(r"<numExtrem>([^<]*)</numExtrem>", xcas)
    m_typ = re.search(r"<typeCond>([^<]*)</typeCond>", xcas)
    if not (m_ext and m_typ):
        raise SystemExit("[LOI] khong doc duoc extrLibres trong mascaret.xcas")
    exts = [int(x) for x in m_ext.group(1).split()]
    typs = [int(x) for x in m_typ.group(1).split()]
    cua = set()
    for e, t in zip(exts, typs):
        if t == 2:                       # bien Z = cua bien
            cua.add((e + 1) // 2)        # ext -> bief
    return cua


def rebuild_init_smart(outdir, cua_biefs, init_high=9.0, init_low=3.0,
                       cua_floor=3.0, cua_level=3.0, q_init=10000.0):
    """SMART INIT — copy cong thuc 24d2, nhan dien cua bang topology."""
    lines = (outdir / "geometrie").read_text(encoding="latin-1",
                                             errors="replace").splitlines()
    profs, cur = [], None
    for l in lines:
        if l.startswith("PROFIL"):
            if cur:
                profs.append(cur)
            m = re.search(r"Bief_(\d+)", l)
            p = l.split()
            cur = {"bief": int(m.group(1)) if m else 0,
                   "absc": float(p[3]), "zs": []}
        elif cur and l.strip():
            p = l.split()
            if len(p) >= 2:
                try:
                    cur["zs"].append(float(p[1]))
                except Exception:
                    pass
    if cur:
        profs.append(cur)

    bmax = max(pr["bief"] for pr in profs) if profs else 1
    all_x, all_z, order, cnt = [], [], [], {}
    zinfo = {}
    for pr in profs:
        bed = min(pr["zs"]) if pr["zs"] else 0.0
        if pr["bief"] in cua_biefs:
            z = min(max(bed + 4.0, cua_floor), cua_level)
        else:
            frac = pr["bief"] / bmax
            z = max(init_high - frac * (init_high - init_low), bed + 5.0)
        all_x.append(pr["absc"])
        all_z.append(z)
        cnt[pr["bief"]] = cnt.get(pr["bief"], 0) + 1
        zinfo.setdefault(pr["bief"], []).append(z)
        if pr["bief"] not in order:
            order.append(pr["bief"])

    imax = len(all_x)
    ranges, idx = [], 1
    for b in order:
        ranges.append((idx, idx + cnt[b] - 1))
        idx += cnt[b]

    def fmt(vals, per=5):
        return "\n".join("".join(f"{v:13.2f}" for v in vals[i:i + per])
                         for i in range(0, len(vals), per))

    i1i2 = []
    for a, b in ranges:
        i1i2 += [a, b]
    hdr = [" I1,I2 = " + "".join(f"{v:6d}" for v in i1i2[i:i + 10])
           for i in range(0, len(i1i2), 10)]
    lig = ["RESULTATS CALCUL,DATE : 16/07/26 00:00", "FICHIER RESULTAT MASCARET",
           "-" * 71, f" IMAX  = {imax:4d} NBBIEF= {len(order):4d}"]
    lig += hdr
    lig += [" X", fmt(all_x), " Z", fmt(all_z), " Q", fmt([q_init] * imax), " FIN"]
    (outdir / "init.lig").write_text("\n".join(lig) + "\n", encoding="ascii")
    return imax, min(all_z), max(all_z), zinfo


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--q-txt", default=str(CFG.DATA.Q_OBS))
    ap.add_argument("--wl-txt", default=str(CFG.DATA.WL_OBS))
    ap.add_argument("--start", required=True, help="YYYY-MM-DD")
    ap.add_argument("--end", required=True, help="YYYY-MM-DD")
    ap.add_argument("--init-high", type=float, default=9.0)
    ap.add_argument("--init-low", type=float, default=3.0)
    ap.add_argument("--cua-level", type=float, default=3.0)
    ap.add_argument("--q-init", type=float, default=10000.0)
    args = ap.parse_args()

    out = Path(args.outdir)
    if not (out / "mascaret.xcas").exists():
        raise SystemExit(f"[LOI] khong thay {out}/mascaret.xcas — chay B_build_grid truoc")

    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    dur = (end - start).total_seconds()

    print("=== GAN BIEN THUC DO + SMART INIT ===\n")

    # --- nhan dien cua bang topology ---
    cua = find_cua_biefs(out)
    print(f"Bief la CUA (co bien Z): {sorted(cua)}")
    print(f"Bief song chinh        : {sorted(set(range(1, 16)) - cua)}\n")

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

    # --- SMART INIT ---
    imax, zmn, zmx, zinfo = rebuild_init_smart(
        out, cua, init_high=args.init_high, init_low=args.init_low,
        cua_floor=args.cua_level, cua_level=args.cua_level, q_init=args.q_init)
    print(f"\ninit.lig SMART: {imax} diem, Z tu {zmn:.2f} toi {zmx:.2f}m, "
          f"Q init={args.q_init:.0f}")
    print("  Z init tung bief:")
    for b in sorted(zinfo):
        zs = zinfo[b]
        tag = "CUA" if b in cua else "   "
        print(f"    Bief_{b:<3d} {tag} n={len(zs):3d}  Z={min(zs):6.2f} .. {max(zs):6.2f}")

    # --- cap nhat xcas: tempsMax + pasTemps + pasStock (tham so 24d2) ---
    xp = out / "mascaret.xcas"
    x = xp.read_text(encoding="latin-1", errors="replace")
    x = re.sub(r"<tempsMax>[\d.eE+]+</tempsMax>", f"<tempsMax>{dur:.1f}</tempsMax>", x)
    x = re.sub(r"<pasTemps>[\d.eE+]+</pasTemps>", "<pasTemps>300.0</pasTemps>", x)
    x = re.sub(r"<pasStock>\d+</pasStock>", "<pasStock>12</pasStock>", x)
    x = re.sub(r"<pasTempsVar>true</pasTempsVar>", "<pasTempsVar>false</pasTempsVar>", x)
    xp.write_text(x, encoding="latin-1")
    print(f"\nxcas: tempsMax={dur:.0f}s ({dur/86400:.0f} ngay), pasTemps=300, pasStock=12")

    print(f"\nXONG. Chay: cd {out} && mascaret.py mascaret.xcas")


if __name__ == "__main__":
    main()
