#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
import_data.py — BUILD KHO DỮ LIỆU CHUẨN (chạy MỘT LẦN)

Gom + chuẩn hóa toàn bộ số liệu thực đo về data_ref/ để mọi giai đoạn sau
truy xuất nhanh, nhất quán, không phụ thuộc đường dẫn OneDrive dài.

XỬ LÝ:
  1. Mặt cắt survey 2020 (5 file Excel): đọc theo công thức đã kiểm chứng
     - Mỗi mặt cắt = 3 hàng: [tên TÊN(km+m)] / [khoảng cách] / [cao độ z]
     - y = cumsum(khoảng cách) ; z = hàng cao độ
     - Đánh dấu điểm bờ nhập tay (ADCP không đo sát bờ) bằng heuristic
  2. Vị trí mặt cắt: đọc Vi tri MCN.shp (238 điểm, tên VN1..., EPSG 32648)
  3. ĐỒNG BỘ survey <-> MIKE qua TỌA ĐỘ: mỗi mặt cắt survey -> nhánh MIKE
     gần nhất + chainage, kèm khoảng cách chiếu để kiểm chứng (map xa = cảnh báo)
  4. Số liệu biên Q/WL (từ OBS/): copy sang CSV chuẩn

RA data_ref/:
  cross_sections/index.csv     — 1 dòng/mặt cắt: survey_name, sông, x,y_utm,
                                 mike_branch, mike_chainage, dist_proj_m, n_pts,
                                 width_m, z_bed, z_bank_L, z_bank_R, file
  cross_sections/sec/<name>.csv — mỗi mặt cắt: y, z, kind(do/bo)
  cross_sections/qc/<name>.png  — hình mặt cắt kiểm mắt (nếu --plot)
  boundaries/Q_2011.csv, WL_2011.csv
  build_report.txt

CÁCH DÙNG:
  ~/TELEMAC_1D_MEKONG/.venv/bin/python src/import_data.py --plot
  (cần venv vì dùng geopandas + openpyxl)
"""
import argparse
import re
import sys
import math
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.config import CFG

import numpy as np
import pandas as pd

# ---- nguồn survey (repo cũ, ngoài MIKE11-DBSCL) ----
SURVEY_CLEAN = Path("/mnt/d/OneDrive/De Tai/De Tai TELEMAC/TELEMAC_1D_MEKONG"
                    "/01_data/processed/cross_sections/clean")
SURVEY_FILES = {
    "SongTien": "Tien", "SongHau": "BASSAC", "SongVamNao": "VamNao",
    "SongCoChien": "CoChien", "SongHamLuong": "HamLuong",
}
SHP_VITRI = SURVEY_CLEAN / "Shapefiles" / "Vi tri MCN.shp"

NAME_RE = re.compile(r"([A-Za-z]+\d+[A-Za-z]?)\s*\((\d+)\+(\d+)\)")


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


# ============================================================================
# 1. ĐỌC MẶT CẮT TỪ EXCEL  (công thức đã kiểm chứng: y=cumsum(kc), z=cao độ)
# ============================================================================
def parse_survey_excel(path, river):
    """Trả list dict: {name, chainage_survey, y[], z[], kind[]}."""
    df = pd.read_excel(path, header=None)
    n = len(df)
    out = []
    i = 0
    while i < n:
        # tìm hàng tên ở cột 0 hoặc 1
        name, ch = None, None
        for col in (0, 1):
            if col < df.shape[1]:
                m = NAME_RE.match(str(df.iloc[i, col]).strip())
                if m:
                    name = m.group(1)
                    ch = float(int(m.group(2)) * 1000 + int(m.group(3)))
                    break
        if name is None:
            i += 1
            continue
        # 2 hàng dưới = khoảng cách + cao độ
        if i + 2 >= n:
            break
        dist = pd.to_numeric(df.iloc[i + 1, 1:], errors="coerce").dropna().values
        zval = pd.to_numeric(df.iloc[i + 2, 1:], errors="coerce").dropna().values
        m2 = min(len(dist), len(zval))
        if m2 >= 3:
            dist, zval = dist[:m2], zval[:m2]
            y = np.cumsum(dist)
            y = y - y.min()  # gốc 0 ở bờ trái
            kind = mark_bank_points(y, zval)
            out.append({"name": name, "chainage_survey": ch,
                        "y": y, "z": zval, "kind": kind})
        i += 3
    return out


def mark_bank_points(y, z):
    """Đánh dấu điểm bờ nhập tay (ADCP): điểm z cao gần 2 mép, ít điểm.
    Heuristic: điểm ở 2% đầu/cuối theo bề rộng và z > (median z lòng + 2m)."""
    n = len(y)
    kind = ["do"] * n
    if n < 5:
        return kind
    width = y[-1] - y[0]
    z_med = np.median(z)
    for i in range(n):
        near_edge = (y[i] - y[0] < 0.03 * width) or (y[-1] - y[i] < 0.03 * width)
        high = z[i] > z_med + 2.0
        if near_edge and high:
            kind[i] = "bo"
    return kind


def xsec_stats(y, z, water_level):
    """Bề rộng, đáy, 2 bờ, diện tích ướt tại mực water_level."""
    width = float(y[-1] - y[0])
    z_bed = float(np.min(z))
    z_bank_L = float(z[0])
    z_bank_R = float(z[-1])
    # A_wet: tích phân (water_level - z) ở nơi z < water_level
    a = 0.0
    for i in range(len(y) - 1):
        h0 = max(0.0, water_level - z[i])
        h1 = max(0.0, water_level - z[i + 1])
        a += 0.5 * (h0 + h1) * (y[i + 1] - y[i])
    return width, z_bed, z_bank_L, z_bank_R, float(a)


# ============================================================================
# 2. VỊ TRÍ MẶT CẮT + POLYLINE MIKE  (để đồng bộ qua tọa độ)
# ============================================================================
def load_vitri_shp(path):
    """Trả {norm(name): (x, y)} từ shapefile vị trí. Khử trùng lấy điểm đầu."""
    import geopandas as gpd
    g = gpd.read_file(path)
    pts = {}
    for _, row in g.iterrows():
        nm = norm(row.get("Name", ""))
        geom = row.geometry
        if geom is None or nm in pts:
            continue
        try:
            pts[nm] = (float(geom.x), float(geom.y))
        except Exception:
            continue
    return pts


def load_mike_polylines(nwk11):
    """{branch: [(x,y)...]} — kế thừa từ GĐ A."""
    text = Path(nwk11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(
        r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
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


def project_to_polylines(px, py, poly, prefer_norm=None):
    """Tìm nhánh + chainage gần điểm (px,py) nhất. Trả (branch, chainage, dist)."""
    best = (None, 0.0, 1e18)
    for name, pl in poly.items():
        if prefer_norm and norm(name) != prefer_norm:
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


# ============================================================================
# 3. BIÊN Q/WL
# ============================================================================
def import_boundaries(outdir):
    """Copy Q_OBS, WL_OBS sang CSV chuẩn (time + các cột trạm)."""
    def read_obs(path):
        lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
        cols = re.split(r"\s+", lines[1].strip())
        rows = []
        for l in lines[3:]:
            if not l.strip():
                continue
            parts = l.split("\t") if "\t" in l else re.split(r"\s{2,}", l.strip())
            if len(parts) >= 2:
                rows.append(parts)
        return cols, rows

    bdir = outdir / "boundaries"
    bdir.mkdir(parents=True, exist_ok=True)
    for src, name in ((CFG.DATA.Q_OBS, "Q_2011.csv"), (CFG.DATA.WL_OBS, "WL_2011.csv")):
        try:
            cols, rows = read_obs(src)
            with open(bdir / name, "w", encoding="utf-8") as f:
                f.write(";".join(cols) + "\n")
                for r in rows:
                    f.write(";".join(str(x) for x in r) + "\n")
            print(f"  biên -> {bdir/name} ({len(rows)} dòng, {len(cols)} cột)")
        except Exception as e:
            print(f"  [!] lỗi đọc {src}: {e}")


# ============================================================================
# MAIN
# ============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plot", action="store_true", help="vẽ QC mỗi mặt cắt")
    ap.add_argument("--water-level", type=float, default=CFG.QC.QC_WATER_LEVEL)
    args = ap.parse_args()

    out = CFG.OUT.ROOT / "data_ref"
    csdir = out / "cross_sections"
    secdir = csdir / "sec"
    qcdir = csdir / "qc"
    for d in (secdir, qcdir):
        d.mkdir(parents=True, exist_ok=True)

    print("=== BUILD KHO DỮ LIỆU ===")
    print("1. Đọc vị trí mặt cắt (Vi tri MCN.shp)...")
    try:
        vitri = load_vitri_shp(SHP_VITRI)
        print(f"   {len(vitri)} vị trí (đã khử trùng)")
    except Exception as e:
        print(f"   [!] không đọc được shapefile: {e}")
        vitri = {}

    print("2. Đọc polyline MIKE (để đồng bộ tọa độ)...")
    poly = load_mike_polylines(CFG.DATA.NWK11)
    print(f"   {len(poly)} nhánh có polyline")

    print("3. Đọc + chuẩn hóa mặt cắt survey 2020...")
    index_rows = []
    for stem, river in SURVEY_FILES.items():
        xl = SURVEY_CLEAN / f"{stem}__clean.xlsx"
        if not xl.exists():
            print(f"   [bỏ qua] không thấy {xl.name}")
            continue
        secs = parse_survey_excel(xl, river)
        print(f"   {stem}: {len(secs)} mặt cắt")
        for s in secs:
            nm = s["name"]
            width, z_bed, zL, zR, awet = xsec_stats(s["y"], s["z"], args.water_level)
            # vị trí + đồng bộ MIKE
            xy = vitri.get(norm(nm))
            mb, mch, dist = (None, 0.0, None)
            if xy:
                mb, mch, dist = project_to_polylines(xy[0], xy[1], poly)
            # ghi file mặt cắt
            secfile = secdir / f"{stem}_{nm}.csv"
            with open(secfile, "w", encoding="utf-8") as f:
                f.write("y_m;z_m;kind\n")
                for yy, zz, kk in zip(s["y"], s["z"], s["kind"]):
                    f.write(f"{yy:.2f};{zz:.3f};{kk}\n")
            index_rows.append({
                "survey_name": nm, "river": river, "file_stem": stem,
                "chainage_survey": s["chainage_survey"],
                "x_utm": xy[0] if xy else "", "y_utm": xy[1] if xy else "",
                "mike_branch": mb or "", "mike_chainage": round(mch, 1) if mb else "",
                "dist_proj_m": round(dist, 1) if dist is not None else "",
                "n_pts": len(s["y"]), "width_m": round(width, 1),
                "z_bed": round(z_bed, 2), "z_bank_L": round(zL, 2),
                "z_bank_R": round(zR, 2), "awet_m2": round(awet, 1),
                "sec_file": secfile.name,
            })
            if args.plot:
                plot_xsec(qcdir / f"{stem}_{nm}.png", s, nm, river, width, z_bed)

    # index.csv
    idx = pd.DataFrame(index_rows)
    idx_path = csdir / "index.csv"
    idx.to_csv(idx_path, sep=";", index=False)
    print(f"\n   index -> {idx_path} ({len(idx)} mặt cắt)")

    # cảnh báo map xa
    if len(idx) and "dist_proj_m" in idx:
        far = idx[pd.to_numeric(idx["dist_proj_m"], errors="coerce") > 500]
        if len(far):
            print(f"   [!] {len(far)} mặt cắt chiếu XA MIKE >500m (kiểm map): "
                  f"{list(far['survey_name'][:10])}")

    print("4. Import biên Q/WL...")
    import_boundaries(out)

    # report
    with open(out / "build_report.txt", "w", encoding="utf-8") as f:
        f.write(f"KHO DỮ LIỆU — build {pd.Timestamp.now()}\n")
        f.write(f"Mặt cắt survey 2020: {len(idx)}\n")
        f.write(f"Vị trí (shp): {len(vitri)}\n")
        if len(idx):
            f.write(f"Bề rộng TB: {pd.to_numeric(idx['width_m']).mean():.0f}m\n")
            f.write(f"Đáy sâu nhất: {pd.to_numeric(idx['z_bed']).min():.1f}m\n")
    print(f"\nXONG. Kho -> {out}/")
    print("Kiểm: data_ref/cross_sections/index.csv + qc/*.png")


def plot_xsec(path, s, name, river, width, z_bed):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(10, 4))
    y, z, kind = s["y"], s["z"], s["kind"]
    ax.plot(y, z, "-", color="#1f77b4", lw=1)
    do = [i for i, k in enumerate(kind) if k == "do"]
    bo = [i for i, k in enumerate(kind) if k == "bo"]
    ax.plot([y[i] for i in do], [z[i] for i in do], ".", ms=3, color="#1f77b4", label="ADCP đo")
    if bo:
        ax.plot([y[i] for i in bo], [z[i] for i in bo], "o", ms=5, color="#d62728", label="bờ nhập tay")
    ax.set_title(f"{name} ({river}) — rộng {width:.0f}m, đáy {z_bed:.1f}m")
    ax.set_xlabel("y (m)"); ax.set_ylabel("z (m)"); ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8)
    fig.savefig(path, dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
