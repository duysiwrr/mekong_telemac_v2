#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_network_xsec.py — VẼ MẠNG + VỊ TRÍ MẶT CẮT (kiểm mắt)

Vẽ mạng lưới giữ (xanh) + gạch ngang nhỏ tại mỗi vị trí có mặt cắt.
Gạch vẽ VUÔNG GÓC với hướng sông tại điểm đó (như ký hiệu mặt cắt trên bản đồ).

Màu gạch:
  xanh lá = mặt cắt MIKE 2011 (.xns11)
  đỏ      = mặt cắt survey 2020 (ADCP)

RA: output/audit/network_xsec_map.png (+ bản zoom nếu --zoom)

DÙNG:
  python3 src/plot_network_xsec.py
  python3 src/plot_network_xsec.py --zoom 500000 1180000 560000 1220000   # xmin ymin xmax ymax
"""
import argparse
import csv
import math
import re
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    import mikeio1d
except Exception:
    mikeio1d = None


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def load_network():
    """Trả (branch_segs, points). branch_segs: name -> list of point-id lists."""
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    pts, pch = {}, {}
    for m in re.finditer(
        r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,\s*[\-\d.]+\s*,\s*([\-\d.]+)", text):
        pid, x, y, ch = int(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[pid] = (x, y)
            pch[pid] = ch
    segs = defaultdict(list)
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if dm and pm:
            ids = [int(p) for p in pm.group(1).split(",") if p.strip()]
            segs[dm.group(1)].append(ids)
    return segs, pts, pch


def xsec_positions(segs, pts, pch, kept):
    """Với mỗi mặt cắt MIKE (loc, chainage) -> tìm tọa độ + hướng trên polyline.
    Trả list (x, y, dx, dy) — dx,dy là vector đơn vị dọc sông tại đó."""
    if mikeio1d is None:
        print("[!] thiếu mikeio1d")
        return []
    xns = mikeio1d.open(str(CFG.DATA.XNS11))
    df = xns.to_dataframe().reset_index()
    # gom chainage theo location
    by_loc = defaultdict(list)
    for _, r in df.iterrows():
        try:
            by_loc[norm(r["location_id"])].append(float(r["chainage"]))
        except Exception:
            continue

    out = []
    for nm in kept:
        chs = by_loc.get(norm(nm))
        if not chs:
            continue
        # dựng polyline (gộp mọi đoạn) + chainage từng điểm
        pl = []
        for ids in segs.get(nm, []):
            for pid in ids:
                if pid in pts:
                    pl.append((pch[pid], pts[pid]))
        if len(pl) < 2:
            continue
        pl.sort(key=lambda t: t[0])
        chs_pl = [p[0] for p in pl]
        xy_pl = [p[1] for p in pl]
        for ch in chs:
            # tìm đoạn chứa ch -> nội suy tọa độ + hướng
            if ch < chs_pl[0] or ch > chs_pl[-1]:
                continue
            for i in range(len(chs_pl) - 1):
                if chs_pl[i] <= ch <= chs_pl[i + 1]:
                    span = chs_pl[i + 1] - chs_pl[i]
                    t = (ch - chs_pl[i]) / span if span > 0 else 0
                    x0, y0 = xy_pl[i]
                    x1, y1 = xy_pl[i + 1]
                    x = x0 + t * (x1 - x0)
                    y = y0 + t * (y1 - y0)
                    dx, dy = x1 - x0, y1 - y0
                    d = math.hypot(dx, dy)
                    if d > 0:
                        out.append((x, y, dx / d, dy / d))
                    break
    return out


def survey_positions():
    """Vị trí mặt cắt survey 2020 từ sync_index.csv."""
    p = CFG.OUT.ROOT / "data_ref" / "cross_sections" / "sync_index.csv"
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            try:
                if r.get("co_z") == "yes":
                    out.append((float(r["x_utm"]), float(r["y_utm"])))
            except (ValueError, KeyError):
                continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zoom", nargs=4, type=float, metavar=("XMIN","YMIN","XMAX","YMAX"))
    ap.add_argument("--tick", type=float, default=900.0, help="nửa chiều dài gạch (m)")
    args = ap.parse_args()

    print("Đọc mạng...")
    segs, pts, pch = load_network()

    kept = set()
    with open(CFG.OUT.LEDGER / "branches.csv", encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["giu"] == "GIU":
                kept.add(r["ten_mike"])
    print(f"   {len(kept)} nhánh giữ")

    print("Tìm vị trí mặt cắt MIKE...")
    xs = xsec_positions(segs, pts, pch, kept)
    print(f"   {len(xs)} mặt cắt MIKE có tọa độ")

    sv = survey_positions()
    print(f"   {len(sv)} mặt cắt survey 2020")

    print("Vẽ...")
    fig, ax = plt.subplots(figsize=(16, 18))
    # mạng
    for nm, seglist in segs.items():
        keep = nm in kept
        for ids in seglist:
            pl = [pts[p] for p in ids if p in pts]
            if len(pl) < 2:
                continue
            X, Y = zip(*pl)
            ax.plot(X, Y, "-", lw=0.9 if keep else 0.3,
                    color="#1f77b4" if keep else "#e8e8e8",
                    zorder=2 if keep else 1)
    # gạch mặt cắt MIKE: vuông góc hướng sông
    L = args.tick
    for (x, y, dx, dy) in xs:
        px, py = -dy, dx           # vector vuông góc
        ax.plot([x - px * L, x + px * L], [y - py * L, y + py * L],
                "-", lw=0.8, color="#2ca02c", zorder=3)
    # survey 2020: chấm đỏ
    if sv:
        SX, SY = zip(*sv)
        ax.scatter(SX, SY, s=10, c="#d62728", zorder=4, label=f"survey 2020 ({len(sv)})")

    from matplotlib.lines import Line2D
    handles = [
        Line2D([0], [0], color="#1f77b4", lw=2, label=f"nhánh giữ ({len(kept)})"),
        Line2D([0], [0], color="#2ca02c", lw=2, label=f"mặt cắt MIKE ({len(xs)})"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d62728",
               markersize=7, label=f"survey 2020 ({len(sv)})"),
    ]
    ax.legend(handles=handles, fontsize=11, loc="lower right")
    ax.set_title("Mạng lưới + vị trí mặt cắt (gạch xanh lá = MIKE, chấm đỏ = survey 2020)",
                 fontsize=13)
    ax.set_xlabel("UTM X"); ax.set_ylabel("UTM Y")
    ax.set_aspect("equal")

    outdir = CFG.OUT.OUTPUT / "audit"
    outdir.mkdir(parents=True, exist_ok=True)
    if args.zoom:
        x0, y0, x1, y1 = args.zoom
        ax.set_xlim(x0, x1); ax.set_ylim(y0, y1)
        p = outdir / "network_xsec_zoom.png"
    else:
        p = outdir / "network_xsec_map.png"
    fig.savefig(p, dpi=180, bbox_inches="tight")
    print(f"-> {p}")


if __name__ == "__main__":
    main()
