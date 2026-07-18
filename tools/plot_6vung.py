#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_6vung.py — VE 6 BAN DO VUNG DBSCL voi TEN KENH

Muc dich: Duy nhin tung vung -> chi quy luat loc kenh phu.
Khong dung bien Z (roi mat), chi ve TUYEN + TEN KENH + nut giao.
Net theo be rong. Kenh truc (>=300m) dam, kenh phu nhat.

6 VUNG (theo toa do trung tam nhanh):
  1_TGLX      tay bac       Hau -> bien Tay
  2_TNSH      giua tay      Hau -> bien Tay
  3_DTM       dong bac      Tien -> Vam Co
  4_BDCM      cuc nam       ban dao Ca Mau
  5_NamMangThit dong nam    Co Chien <-> Hau
  6_TRUC      giua          Tien/Hau + cua (giu cung)

DUNG:
  python3 plot_6vung.py                 # ve ca 6 vung
  python3 plot_6vung.py --vung 1_TGLX   # 1 vung
"""
import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def phan_vung(cx, cy):
    if cx < 540000 and cy > 1140000:
        return "1_TGLX"
    if cy < 1050000:
        return "4_BDCM"
    if cx < 570000 and cy < 1120000:
        return "2_TNSH"
    if cx > 600000 and cy > 1145000:
        return "3_DTM"
    if cx > 615000 and cy < 1125000:
        return "5_NamMangThit"
    return "6_TRUC"


def load():
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    poly = defaultdict(list)
    for blk in re.split(r"\[branch\]", text)[1:]:
        e = blk.find("EndSect  // branch")
        bt = blk[:e] if e > 0 else blk
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if dm and pm:
            poly[dm.group(1)] += [pts[int(p)] for p in pm.group(1).split(",")
                                  if p.strip() and int(p) in pts]
    giu = {r["ten_mike"]: float(r["width_m"] or 0)
           for r in csv.DictReader(open("output/ledger/branches.csv",
                                        encoding="utf-8"), delimiter=";")
           if r["giu"] == "GIU"}
    return poly, giu


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vung", default=None)
    args = ap.parse_args()

    poly, giu = load()
    # gan vung cho moi nhanh
    vung_of = {}
    for n in giu:
        v = poly.get(n, [])
        if not v:
            continue
        cx = sum(p[0] for p in v) / len(v)
        cy = sum(p[1] for p in v) / len(v)
        vung_of[n] = phan_vung(cx, cy)

    vungs = sorted(set(vung_of.values()))
    if args.vung:
        vungs = [v for v in vungs if v == args.vung]

    outdir = Path("output/vung_maps")
    outdir.mkdir(exist_ok=True)

    for vg in vungs:
        nhs = [n for n in giu if vung_of.get(n) == vg]
        fig, ax = plt.subplots(figsize=(20, 20))
        for n in nhs:
            v = poly.get(n)
            if not v:
                continue
            w = giu[n]
            lw = 0.5 + min(w, 2000) / 2000 * 4.5
            truc = w >= 300
            ax.plot([p[0] for p in v], [p[1] for p in v], "-",
                    lw=lw, alpha=.85 if truc else .5,
                    color="#1f4e79" if truc else "#8aa",
                    solid_capstyle="round", zorder=3 if truc else 2)
            # ten kenh o giua
            mid = v[len(v) // 2]
            ax.annotate(n, mid, fontsize=8 if truc else 6,
                        weight="bold" if truc else "normal",
                        color="#c00" if truc else "#555",
                        zorder=10, xytext=(3, 3),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.15", fc="white",
                                  ec="#ccc", alpha=.75, lw=.3))
        h = [
            Line2D([0], [0], color="#1f4e79", lw=3, label="kenh truc (>=300m)"),
            Line2D([0], [0], color="#8aa", lw=1, label="kenh phu (<300m)"),
        ]
        ax.legend(handles=h, fontsize=12, loc="best")
        ax.set_title(f"VUNG {vg}: {len(nhs)} nhanh\n"
                     f"(do do net = be rong | do = truc | xam = phu)",
                     fontsize=16)
        ax.set_xlabel("UTM X (m)")
        ax.set_ylabel("UTM Y (m)")
        ax.set_aspect("equal")
        ax.grid(alpha=.2)
        p = outdir / f"vung_{vg}.png"
        fig.savefig(p, dpi=130, bbox_inches="tight")
        plt.close(fig)
        print(f"  {vg:16s} {len(nhs):4d} nhanh -> {p}")

    print(f"\nXONG -> {outdir}/")


if __name__ == "__main__":
    main()
