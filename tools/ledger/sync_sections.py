#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
sync_sections.py — ĐỒNG BỘ MẶT CẮT SURVEY <-> MẠNG MIKE (bằng TỌA ĐỘ thuần)

Giải bài "tên lộn xộn": tên Excel (CC10P) không khớp shapefile (CC10P1/P2),
hoa/thường lẫn lộn, hậu tố P/P1/P2/CT/CD = nhánh ôm cù lao. KHÔNG khớp theo tên.

CHIẾN LƯỢC (tọa độ là chân lý):
  1. Đọc TẤT CẢ điểm shapefile Vi tri MCN -> tọa độ (giữ mọi biến thể tên).
  2. Mỗi điểm shp -> chiếu vào nhánh MIKE gần nhất (branch, chainage, dist).
     Điểm P/P1/P2 tự rơi vào nhánh cù lao tương ứng vì tọa độ nó ở đó.
  3. Nối số liệu z (Excel) vào điểm shp bằng tên chuẩn hóa + khớp gần nhất.
  4. Xuất index đồng bộ: survey_name, shp_name, x,y, mike_branch, chainage,
     dist_proj, role(chinh/nhanh_phu), có_z(số liệu mặt cắt).

RA data_ref/cross_sections/sync_index.csv + sync_map.png

DÙNG: ~/TELEMAC_1D_MEKONG/.venv/bin/python src/sync_sections.py --plot
"""
import argparse
import re
import sys
import math
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.config import CFG

import numpy as np
import pandas as pd

SURVEY_CLEAN = Path("/mnt/d/OneDrive/De Tai/De Tai TELEMAC/TELEMAC_1D_MEKONG"
                    "/01_data/processed/cross_sections/clean")
SHP_VITRI = SURVEY_CLEAN / "Shapefiles" / "Vi tri MCN.shp"
SURVEY_FILES = {"SongTien": "Tien", "SongHau": "BASSAC", "SongVamNao": "VamNao",
                "SongCoChien": "CoChien", "SongHamLuong": "HamLuong"}

# tiền tố tên survey -> sông (để ưu tiên map đúng sông)
PREFIX_RIVER = {"ST": "Tien", "SH": "BASSAC", "VN": "VamNao",
                "CC": "CoChien", "HL": "HamLuong"}


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def parse_name(nm):
    """Tách tên -> (gốc, hậu tố, role). VD CC10P1 -> (CC10, P1, nhanh_phu)."""
    m = re.match(r"^([A-Za-z]+\d+)([A-Za-z0-9]*)$", nm.strip())
    if not m:
        return nm, "", "dac_biet"
    base, suf = m.group(1), m.group(2)
    su = suf.upper()
    if su == "":
        role = "chinh"
    elif su in ("A", "B", "AB"):
        role = "nhanh_AB"
    elif su.startswith("P") or su.startswith("CT") or su.startswith("CD") or su.startswith("CP"):
        role = "nhanh_phu"
    else:
        role = "khac"
    return base, suf, role


# ============================================================================
def load_shp_points(path):
    """Trả list (name, x, y). Giữ MỌI điểm (kể cả trùng tên biến thể)."""
    import geopandas as gpd
    g = gpd.read_file(path)
    out = []
    for _, row in g.iterrows():
        nm = str(row.get("Name", "")).strip()
        if row.geometry is None or not nm or nm.lower() == "none":
            continue
        try:
            out.append((nm, float(row.geometry.x), float(row.geometry.y)))
        except Exception:
            continue
    return out


def load_mike_polylines(nwk11):
    text = Path(nwk11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    poly = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        dm = re.search(r"definitions\s*=\s*'([^']*)'", block)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", block)
        if dm and pm:
            ids = [int(p) for p in pm.group(1).split(",") if p.strip()]
            v = [pts[i] for i in ids if i in pts]
            if len(v) >= 2:
                poly[dm.group(1)] = v
    return poly


def project(px, py, poly, kept_only=None):
    """Nhánh + chainage gần nhất. kept_only = set nhánh giữ (từ ledger) nếu có."""
    best = (None, 0.0, 1e18)
    for name, pl in poly.items():
        if kept_only is not None and name not in kept_only:
            continue
        acc = 0.0
        for i in range(len(pl) - 1):
            (x0, y0), (x1, y1) = pl[i], pl[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg == 0:
                continue
            t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (seg * seg)
            t = max(0.0, min(1.0, t))
            cx, cy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            d = math.hypot(px - cx, py - cy)
            if d < best[2]:
                best = (name, acc + t * seg, d)
            acc += seg
    return best


def load_excel_names():
    """Trả set tên chuẩn hóa có SỐ LIỆU z trong Excel (để biết điểm nào có mặt cắt)."""
    names = set()
    NAME_RE = re.compile(r"([A-Za-z]+\d+[A-Za-z]?)\s*\((\d+)\+(\d+)\)")
    for stem in SURVEY_FILES:
        xl = SURVEY_CLEAN / f"{stem}__clean.xlsx"
        if not xl.exists():
            continue
        df = pd.read_excel(xl, header=None)
        for i in range(len(df)):
            for col in (0, 1):
                if col < df.shape[1]:
                    m = NAME_RE.match(str(df.iloc[i, col]).strip())
                    if m:
                        names.add(norm(m.group(1)))
    return names


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true")
    ap.add_argument("--use-ledger", action="store_true",
                    help="chỉ map vào nhánh GIỮ trong ledger (từ GĐ A)")
    args = ap.parse_args()

    print("=== ĐỒNG BỘ MẶT CẮT <-> MẠNG MIKE (tọa độ thuần) ===")
    print("1. Đọc điểm shapefile...")
    shp = load_shp_points(SHP_VITRI)
    print(f"   {len(shp)} điểm (giữ mọi biến thể tên)")

    print("2. Đọc polyline MIKE...")
    poly = load_mike_polylines(CFG.DATA.NWK11)
    print(f"   {len(poly)} nhánh")

    kept = None
    if args.use_ledger:
        lj = CFG.OUT.LEDGER / "ledger.json"
        if lj.exists():
            import json
            kept = set(json.loads(lj.read_text(encoding="utf-8"))["kept"])
            print(f"   dùng ledger: chỉ map vào {len(kept)} nhánh GIỮ")

    print("3. Đọc tên có số liệu z (Excel)...")
    excel_names = load_excel_names()
    print(f"   {len(excel_names)} tên có mặt cắt trong Excel")

    print("4. Chiếu từng điểm shp vào nhánh MIKE...")
    rows = []
    for nm, x, y in shp:
        base, suf, role = parse_name(nm)
        mb, mch, dist = project(x, y, poly, kept)
        rows.append({
            "shp_name": nm, "base": base, "suffix": suf, "role": role,
            "x_utm": round(x, 1), "y_utm": round(y, 1),
            "mike_branch": mb or "", "mike_chainage": round(mch, 1) if mb else "",
            "dist_proj_m": round(dist, 1) if dist < 1e17 else "",
            "co_z": "yes" if norm(base) in excel_names or norm(nm) in excel_names else "no",
        })
    idx = pd.DataFrame(rows)

    out = CFG.OUT.ROOT / "data_ref" / "cross_sections"
    out.mkdir(parents=True, exist_ok=True)
    idx.to_csv(out / "sync_index.csv", sep=";", index=False)
    print(f"   -> {out/'sync_index.csv'} ({len(idx)} điểm)")

    # thống kê
    print("\n=== THỐNG KÊ ===")
    print(idx["role"].value_counts().to_string())
    d = pd.to_numeric(idx["dist_proj_m"], errors="coerce").dropna()
    print(f"\ndist chiếu: median={d.median():.0f}m, <100m={sum(d<100)}, "
          f">500m(nghi sai)={sum(d>500)}")
    far = idx[pd.to_numeric(idx["dist_proj_m"], errors="coerce") > 500]
    if len(far):
        print("  map xa:", list(far["shp_name"][:15]))
    # điểm có z nhưng không map (dac_biet)
    special = idx[idx["role"] == "dac_biet"]
    if len(special):
        print(f"\n{len(special)} điểm đặc biệt (tên bất thường):",
              list(special["shp_name"]))

    if args.plot:
        plot_sync(out / "sync_map.png", poly, idx, kept)

    print("\nXONG. Kiểm sync_index.csv + sync_map.png")


def plot_sync(path, poly, idx, kept):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(13, 15))
    # mạng nền
    for name, pl in poly.items():
        keep = (kept is None) or (name in kept)
        xs, ys = zip(*pl)
        ax.plot(xs, ys, "-", lw=0.8 if keep else 0.3,
                color="#cccccc", zorder=1)
    # điểm mặt cắt theo role
    colors = {"chinh": "#1f77b4", "nhanh_phu": "#d62728",
              "nhanh_AB": "#2ca02c", "khac": "#ff7f0e", "dac_biet": "#9467bd"}
    for role, c in colors.items():
        sub = idx[idx["role"] == role]
        if len(sub):
            ax.scatter(pd.to_numeric(sub["x_utm"]), pd.to_numeric(sub["y_utm"]),
                       s=14, c=c, label=f"{role} ({len(sub)})", zorder=3)
    ax.set_title(f"Đồng bộ mặt cắt survey 2020 <-> mạng MIKE ({len(idx)} điểm)")
    ax.set_aspect("equal"); ax.legend(fontsize=9)
    ax.set_xlabel("UTM X"); ax.set_ylabel("UTM Y")
    fig.savefig(path, dpi=170, bbox_inches="tight")
    print(f"   bản đồ -> {path}")


if __name__ == "__main__":
    main()
