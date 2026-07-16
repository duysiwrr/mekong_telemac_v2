#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_catalog.py — BANG TRA CUU TONG HOP MAT CAT (survey 2020 + MIKE)

Lap 1 bang duy nhat cho moi mat cat, tra duoc bang: ten, toa do, song, nhanh MIKE.
Toa do la MOC — moi lien ket deu qua toa do, khong qua ten.

XU LY 3 VAN DE DAT TEN da phat hien:
  1. Chu 'Đ' tieng Viet trong Excel (ST37CĐ) vs 'D' trong shapefile (ST37CD)
     -> vn_norm() bo dau truoc khi so khop
  2. norm() xoa dau cach gop 'CO CHIEN'(topo 2006) + 'COCHIEN'(topo 2021)
     -> giu ten GOC, khong gop
  3. Ten survey ST37CT/ST37CĐ/ST37CĐP = 3 nhanh NGANG HANG (cu lao), cung so 37
     -> tach (pre, num, suf); cung num = cung vi tri doc song, khac nhanh

RA data_ref/catalog/:
  catalog_survey.csv  — moi mat cat survey 2020: ten, x, y, song, num, suf,
                        co_z, rong_tuyen, nhanh MIKE + chainage + d_chieu (top 3)
  catalog_mike.csv    — moi mat cat MIKE: location_id, topo_id, chainage, rong, day
  catalog_branch.csv  — moi nhanh MIKE: ten, ch0, ch1, US, DS, link, giu(ledger),
                        n_xsec_mike, n_survey_2020
  catalog_report.txt

DUNG:
  python3 src/build_catalog.py
  python3 src/build_catalog.py --shp-dir /duong/dan/Shapefiles
"""
import argparse
import csv
import math
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import pandas as pd

SURVEY_DIRS = [
    Path("/mnt/d/OneDrive/De Tai/De Tai TELEMAC/TELEMAC_1D_MEKONG"
         "/01_data/processed/cross_sections/clean"),
    Path("/mnt/c/Users/win/OneDrive/De Tai/De Tai TELEMAC/TELEMAC_1D_MEKONG"
         "/01_data/processed/cross_sections/clean"),
]
SURVEY_FILES = {"SongTien": "Tien", "SongHau": "BASSAC", "SongVamNao": "VamNao",
                "SongCoChien": "CoChien", "SongHamLuong": "HamLuong"}
# tien to ten survey -> song
PREFIX = {"ST": "Tien", "SH": "BASSAC", "VN": "VamNao",
          "CC": "CoChien", "HL": "HamLuong"}

# ten (ten Excel) — bat MOI ky tu, ke ca 'Đ'
NAME_RE = re.compile(r"([^\s(]+)\s*\((\d+)\+(\d+)\)")
# tach ten: tien to chu + so + hau to
SPLIT_RE = re.compile(r"^([A-Z]+?)(\d+)([A-Z0-9]*)$")


def vn_norm(s):
    """Bo dau tieng Viet + ky tu dac biet. 'ST37CĐ' -> 'ST37CD'."""
    s = str(s).replace("Đ", "D").replace("đ", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def split_name(vn):
    """'ST37CDP' -> ('ST', 37, 'CDP'). Tra (None,None,None) neu khong khop."""
    m = SPLIT_RE.match(vn)
    return (m.group(1), int(m.group(2)), m.group(3)) if m else (None, None, None)


# ---------------------------------------------------------------- doc nguon
def find_survey_dir():
    for d in SURVEY_DIRS:
        if d.exists():
            return d
    return None


def read_shp_points(shp_path):
    """-> list {name, vn, x, y, kmz}"""
    import os
    os.environ["SHAPE_RESTORE_SHX"] = "YES"
    import geopandas as gpd
    g = gpd.read_file(str(shp_path))
    out = []
    for _, r in g.iterrows():
        nm = str(r.get("Name", "")).strip()
        if not nm or nm.lower() in ("none", "nan") or r.geometry is None:
            continue
        try:
            x, y = float(r.geometry.x), float(r.geometry.y)
        except Exception:
            continue
        kmz = ""
        fp = str(r.get("FolderPath", ""))
        m = re.search(r"/(\w+)\.kmz", fp)
        if m:
            kmz = m.group(1)
        out.append({"name": nm, "vn": vn_norm(nm), "x": x, "y": y, "kmz": kmz})
    return out


def read_tuyen(shp_path):
    """Tuyen do ADCP -> {vn_diem_gan_nhat: chieu_dai_tuyen}. Rong that cua song."""
    import os
    os.environ["SHAPE_RESTORE_SHX"] = "YES"
    import geopandas as gpd
    if not shp_path.exists():
        return []
    g = gpd.read_file(str(shp_path))
    out = []
    for _, r in g.iterrows():
        if r.geometry is None or r.geometry.geom_type != "LineString":
            continue
        mid = r.geometry.interpolate(0.5, normalized=True)
        out.append({"len": r.geometry.length, "mx": mid.x, "my": mid.y})
    return out


def read_excel_z(survey_dir):
    """-> {vn_ten: {file, ten_goc, chainage, n_pt, rong, z_day, z_bo_L, z_bo_R}}"""
    out = {}
    for stem in SURVEY_FILES:
        xl = survey_dir / f"{stem}__clean.xlsx"
        if not xl.exists():
            continue
        df = pd.read_excel(xl, header=None)
        n = len(df)
        i = 0
        while i < n:
            nm, ch = None, None
            for col in (0, 1):
                if col < df.shape[1]:
                    m = NAME_RE.match(str(df.iloc[i, col]).strip())
                    if m:
                        nm = m.group(1)
                        ch = float(int(m.group(2)) * 1000 + int(m.group(3)))
                        break
            if nm is None:
                i += 1
                continue
            if i + 2 >= n:
                break
            dist = pd.to_numeric(df.iloc[i + 1, 1:], errors="coerce").dropna().values
            zval = pd.to_numeric(df.iloc[i + 2, 1:], errors="coerce").dropna().values
            m2 = min(len(dist), len(zval))
            if m2 >= 3:
                import numpy as np
                y = np.cumsum(dist[:m2])
                y = y - y.min()
                z = zval[:m2]
                out[vn_norm(nm)] = {
                    "file": stem, "ten_goc": nm, "chainage": ch, "n_pt": int(m2),
                    "rong": float(y[-1] - y[0]), "z_day": float(z.min()),
                    "z_bo_L": float(z[0]), "z_bo_R": float(z[-1]),
                }
            i += 3
    return out


def read_mike_branches(nwk11):
    """-> (branches{ten: [seg]}, polylines{ten: [(x,y)]})"""
    text = Path(nwk11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    branches, poly = {}, defaultdict(list)
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'\s*,\s*'[^']*'\s*,"
                       r"\s*([\-\d.e]+)\s*,\s*([\-\d.e]+)", bt)
        if not dm:
            continue
        nm = dm.group(1)
        cm = re.search(r"connections\s*=\s*'([^']*)'\s*,\s*([\-\d.e]+)\s*,"
                       r"\s*'([^']*)'\s*,\s*([\-\d.e]+)", bt)
        us = (cm.group(1), float(cm.group(2))) if cm and cm.group(1) else None
        ds = (cm.group(3), float(cm.group(4))) if cm and cm.group(3) else None
        try:
            ch0, ch1 = float(dm.group(2)), float(dm.group(3))
        except ValueError:
            continue
        branches.setdefault(nm, []).append({
            "ch0": ch0, "ch1": ch1, "us": us, "ds": ds,
            "link": ("[linkchannel]" in bt) or ("[storagearea]" in bt)})
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if pm:
            for p in pm.group(1).split(","):
                p = p.strip()
                if p and int(p) in pts:
                    poly[nm].append(pts[int(p)])
    return branches, dict(poly)


def read_mike_xsec(xns11):
    """-> list {location_id, topo_id, chainage, rong, z_day, n_pt}"""
    try:
        import mikeio1d
    except ImportError:
        print("  [!] thieu mikeio1d")
        return []
    xns = mikeio1d.open(str(xns11))
    df = xns.to_dataframe().reset_index()
    out = []
    for _, r in df.iterrows():
        try:
            raw = r["cross_section"].raw
            if raw is None or len(raw) < 2:
                continue
            xs = [float(v) for v in raw["x"].values]
            zs = [float(v) for v in raw["z"].values]
            out.append({"location_id": str(r["location_id"]),
                        "topo_id": str(r["topo_id"]),
                        "chainage": float(r["chainage"]),
                        "rong": max(xs) - min(xs), "z_day": min(zs),
                        "n_pt": len(zs)})
        except Exception:
            continue
    return out


def project(px, py, pl):
    """-> (d_min, chainage_tren_polyline)"""
    best, acc, bc = 1e18, 0.0, 0.0
    for i in range(len(pl) - 1):
        (x0, y0), (x1, y1) = pl[i], pl[i + 1]
        s = math.hypot(x1 - x0, y1 - y0)
        if s == 0:
            continue
        t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (s * s)
        t = max(0.0, min(1.0, t))
        cx, cy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        d = math.hypot(px - cx, py - cy)
        if d < best:
            best, bc = d, acc + t * s
        acc += s
    return best, bc


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shp-dir", default=None)
    ap.add_argument("--top", type=int, default=3, help="so nhanh MIKE gan nhat luu lai")
    args = ap.parse_args()

    out = CFG.OUT.ROOT / "data_ref" / "catalog"
    out.mkdir(parents=True, exist_ok=True)
    print("=== BANG TRA CUU MAT CAT (survey 2020 + MIKE) ===\n")

    sd = find_survey_dir()
    if sd is None:
        raise SystemExit("[LOI] khong thay thu muc survey clean")
    shpdir = Path(args.shp_dir) if args.shp_dir else sd / "Shapefiles"
    print(f"Survey : {sd}")
    print(f"Shp    : {shpdir}\n")

    # --- 1. doc nguon ---
    print("1. Doc shapefile vi tri...")
    shp_p = shpdir / "Vi tri MCN.shp"
    if not shp_p.exists():
        shp_p = shpdir / "Vi_tri_MCN.shp"
    pts = read_shp_points(shp_p)
    print(f"   {len(pts)} diem")

    print("2. Doc tuyen do ADCP (rong that)...")
    t_p = shpdir / "Tuyen do.shp"
    if not t_p.exists():
        t_p = shpdir / "Tuyen_do.shp"
    tuyen = read_tuyen(t_p)
    print(f"   {len(tuyen)} tuyen")

    print("3. Doc so lieu z tu Excel...")
    zdat = read_excel_z(sd)
    print(f"   {len(zdat)} mat cat co z")

    print("4. Doc mang MIKE (nwk11)...")
    branches, poly = read_mike_branches(CFG.DATA.NWK11)
    print(f"   {len(branches)} nhanh, {len(poly)} co polyline")

    print("5. Doc mat cat MIKE (xns11)...")
    mx = read_mike_xsec(CFG.DATA.XNS11)
    print(f"   {len(mx)} mat cat")

    print("6. Doc ledger GD A...")
    led = {}
    lp = CFG.OUT.LEDGER / "branches.csv"
    if lp.exists():
        with open(lp, encoding="utf-8") as f:
            for r in csv.DictReader(f, delimiter=";"):
                led[r["ten_mike"]] = (r["giu"], r["ly_do"])
    print(f"   {len(led)} nhanh trong ledger\n")

    # --- 2. catalog_survey ---
    print("Lap catalog_survey...")
    rows = []
    for p in pts:
        pre, num, suf = split_name(p["vn"])
        z = zdat.get(p["vn"])
        # rong that tu tuyen do gan nhat
        w_tuyen = ""
        if tuyen:
            best = min(tuyen, key=lambda t: math.hypot(t["mx"] - p["x"],
                                                       t["my"] - p["y"]))
            dd = math.hypot(best["mx"] - p["x"], best["my"] - p["y"])
            if dd < 500 and best["len"] < 10000:
                w_tuyen = round(best["len"], 1)
        # top-N nhanh MIKE gan nhat
        cand = []
        for bn, pl in poly.items():
            if len(pl) < 2:
                continue
            d, ch = project(p["x"], p["y"], pl)
            if d < 3000:
                cand.append((d, bn, ch))
        cand.sort()
        r = {"ten": p["name"], "vn": p["vn"], "kmz": p["kmz"],
             "song": PREFIX.get(pre, ""), "pre": pre or "", "num": num if num else "",
             "suf": suf or "", "x_utm": round(p["x"], 1), "y_utm": round(p["y"], 1),
             "co_z": "yes" if z else "no",
             "ch_survey": z["chainage"] if z else "",
             "rong_excel": round(z["rong"], 1) if z else "",
             "rong_tuyen": w_tuyen,
             "z_day": round(z["z_day"], 2) if z else "",
             "n_pt": z["n_pt"] if z else "",
             "file_excel": z["file"] if z else ""}
        for k in range(args.top):
            if k < len(cand):
                d, bn, ch = cand[k]
                r[f"mike{k+1}"] = bn
                r[f"mike{k+1}_ch"] = round(ch, 1)
                r[f"mike{k+1}_d"] = round(d, 1)
            else:
                r[f"mike{k+1}"] = r[f"mike{k+1}_ch"] = r[f"mike{k+1}_d"] = ""
        rows.append(r)
    dsv = pd.DataFrame(rows).sort_values(["song", "num", "suf"], na_position="last")
    dsv.to_csv(out / "catalog_survey.csv", sep=";", index=False)
    print(f"   -> catalog_survey.csv ({len(dsv)} diem)")

    # --- 3. catalog_mike ---
    dmk = pd.DataFrame(mx)
    if len(dmk):
        dmk = dmk.sort_values(["location_id", "chainage"])
        dmk.to_csv(out / "catalog_mike.csv", sep=";", index=False)
    print(f"   -> catalog_mike.csv ({len(dmk)} mat cat)")

    # --- 4. catalog_branch ---
    nxs = defaultdict(int)
    for m in mx:
        nxs[m["location_id"]] += 1
    nsv = defaultdict(int)
    for _, r in dsv.iterrows():
        if r["co_z"] == "yes" and r["mike1"] and r["mike1_d"] != "" \
                and float(r["mike1_d"]) < 200:
            nsv[r["mike1"]] += 1
    brows = []
    for nm, segs in branches.items():
        g, ly = led.get(nm, ("", ""))
        s0 = min(s["ch0"] for s in segs)
        s1 = max(s["ch1"] for s in segs)
        us = "; ".join(f"{s['us'][0]}@{s['us'][1]:.0f}" for s in segs if s["us"])
        ds = "; ".join(f"{s['ds'][0]}@{s['ds'][1]:.0f}" for s in segs if s["ds"])
        tp = ""
        sub = [m for m in mx if m["location_id"] == nm]
        if sub:
            tp = ", ".join(sorted({m["topo_id"] for m in sub}))
        brows.append({"ten_mike": nm, "so_doan": len(segs),
                      "ch0": s0, "ch1": s1, "dai_km": round((s1 - s0) / 1000, 2),
                      "US": us or "TU_DO", "DS": ds or "TU_DO",
                      "link": "yes" if all(s["link"] for s in segs) else "no",
                      "giu_ledger": g, "ly_do": ly,
                      "n_xsec_mike": nxs.get(nm, 0), "topo_id": tp,
                      "n_survey2020": nsv.get(nm, 0)})
    dbr = pd.DataFrame(brows).sort_values("ten_mike")
    dbr.to_csv(out / "catalog_branch.csv", sep=";", index=False)
    print(f"   -> catalog_branch.csv ({len(dbr)} nhanh)")

    # --- 5. report ---
    lines = []
    A = lines.append
    A("BANG TRA CUU MAT CAT — survey 2020 + MIKE")
    A("=" * 70)
    A(f"\nShapefile : {len(pts)} diem")
    A(f"Excel z   : {len(zdat)} mat cat")
    A(f"Khop      : {(dsv['co_z']=='yes').sum()}")
    A(f"Thieu z   : {(dsv['co_z']=='no').sum()}")
    A(f"Tuyen ADCP: {len(tuyen)}")
    A(f"MIKE      : {len(branches)} nhanh, {len(mx)} mat cat")

    A("\n--- SURVEY THEO SONG ---")
    for s in sorted(set(PREFIX.values())):
        sub = dsv[dsv["song"] == s]
        A(f"  {s:10s} {len(sub):3d} diem, co_z={(sub['co_z']=='yes').sum():3d}")

    A("\n--- HAU TO (suf) THEO SONG: cung num = cung vi tri, khac nhanh ---")
    ct = pd.crosstab(dsv["song"], dsv["suf"])
    A(ct.to_string())

    A("\n--- VI TRI CO NHIEU NHANH (cu lao) ---")
    for s in sorted(set(PREFIX.values())):
        sub = dsv[(dsv["song"] == s) & (dsv["num"] != "")]
        for n, grp in sub.groupby("num"):
            if len(grp) > 1:
                items = " | ".join(
                    f"{r['ten']}->{r['mike1']}(d={r['mike1_d']}m)"
                    for _, r in grp.iterrows())
                A(f"  {s} #{n} [{len(grp)} nhanh]: {items}")

    A("\n--- NHANH MIKE CO >1 topo_id (KHONG duoc tron) ---")
    for _, r in dbr[dbr["topo_id"].str.contains(",", na=False)].iterrows():
        A(f"  {r['ten_mike']:16s} {r['topo_id']}  n_xsec={r['n_xsec_mike']}")

    A("\n--- NHANH CO SURVEY 2020 nhung ledger BO ---")
    bad = dbr[(dbr["n_survey2020"] > 0) & (dbr["giu_ledger"] != "GIU")]
    for _, r in bad.iterrows():
        A(f"  {r['ten_mike']:16s} n_survey={r['n_survey2020']}  ly_do={r['ly_do']}")
    if not len(bad):
        A("  (khong co — ledger GD A giu du)")

    (out / "catalog_report.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"   -> catalog_report.txt")
    print("\n" + "\n".join(lines))
    print(f"\nXONG -> {out}/")


if __name__ == "__main__":
    main()
