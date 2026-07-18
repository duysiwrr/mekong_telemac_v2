#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
plot_bo_cuoi.py — VE 65 NHANH BO (ranh Vam Co Tay) + kenh GIU

Nguyen tac Duy chot: VAM CO TAY lam ranh.
  - Phia NAM/TAY NAM Vam Co Tay = DBSCL (giu)
  - Phia BAC/DONG (phai) Vam Co Tay = Long An/HCM (bo), chi giu Vam Co Dong lam ranh
  - Cho Gao GIU (noi Tien — kenh Cho Gao he Go Cong/Bao Dinh)

65 nhanh bo = /tmp/bo_cuoi.txt:
  - 31 dong Vam Co Dong (An Ha, CongXang, ThamLuong, Long An noi dong)
  - Soai Rap/Nga Bay/Cua Can Gio (X>700k): S.NGA BAY, S.Dua, Dong Tranh, Long Tau
  - Campuchia: Cay Kho Lon/Nho, Truc Chinh, Rach Coc/Goc
  - T2/T4/T6/T8 (giua Vam Co Dong-Tay, khong tram)

DUNG: python3 tools/plot_bo_cuoi.py
"""
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def main():
    bo = set(l for l in open("/tmp/bo_cuoi.txt").read().split("\n") if l)
    giu = {r["ten_mike"]: float(r["width_m"] or 0)
           for r in csv.DictReader(open("output/ledger/branches.csv",
                                        encoding="utf-8"), delimiter=";")
           if r["giu"] == "GIU"}

    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    poly = {}
    for blk in re.split(r"\[branch\]", text)[1:]:
        e = blk.find("EndSect  // branch")
        bt = blk[:e] if e > 0 else blk
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if dm and pm:
            v = [pts[int(p)] for p in pm.group(1).split(",")
                 if p.strip() and int(p) in pts]
            if v:
                poly[dm.group(1)] = v

    RANH = {"Vam Co", "Vam Co Dong", "Vam Co Tay"}

    fig, ax = plt.subplots(figsize=(24, 20))
    n_bo = n_giu = 0
    for n, w in giu.items():
        v = poly.get(n)
        if not v:
            continue
        if n in RANH:
            c, lw, z = "#000080", 3, 6
        elif n in bo:
            c, lw, z = "#e00", 1.8, 5
            n_bo += 1
        else:
            c, lw, z = "#bbb", 0.5, 2
            n_giu += 1
        ax.plot([p[0] for p in v], [p[1] for p in v], "-",
                color=c, lw=lw, alpha=.85, zorder=z, solid_capstyle="round")
        if n in bo or n in RANH:
            mid = v[len(v) // 2]
            ax.annotate(n, mid, fontsize=5.5,
                        color="#000080" if n in RANH else "#e00",
                        zorder=10, xytext=(2, 2), textcoords="offset points")

    h = [
        Line2D([0], [0], color="#000080", lw=3, label="Vam Co/Dong/Tay (RANH, giu)"),
        Line2D([0], [0], color="#bbb", lw=1.5, label=f"GIU — DBSCL ({n_giu})"),
        Line2D([0], [0], color="#e00", lw=2, label=f"BO — ngoai vung ({n_bo})"),
    ]
    ax.legend(handles=h, fontsize=14, loc="lower left")
    ax.set_title("DANH SACH BO CUOI — 65 nhanh (ranh: Vam Co Tay)\n"
                 "DO = bo (Long An/HCM/Campuchia/Soai Rap) | XAM = giu DBSCL",
                 fontsize=16)
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_aspect("equal")
    ax.grid(alpha=.2)

    out = Path("output/vung_thuyloi")
    p = out / "bo_cuoi.png"
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    # ban do zoom vung Vam Co
    ax2 = None
    fig2, ax2 = plt.subplots(figsize=(22, 16))
    for n, w in giu.items():
        v = poly.get(n)
        if not v:
            continue
        cx = sum(p[0] for p in v) / len(v)
        if cx < 600000:
            continue
        if n in RANH:
            c, lw, z = "#000080", 3, 6
        elif n in bo:
            c, lw, z = "#e00", 2, 5
        else:
            c, lw, z = "#bbb", 0.6, 2
        ax2.plot([p[0] for p in v], [p[1] for p in v], "-",
                 color=c, lw=lw, alpha=.85, zorder=z, solid_capstyle="round")
        if n in bo or n in RANH:
            mid = v[len(v) // 2]
            ax2.annotate(n, mid, fontsize=7,
                         color="#000080" if n in RANH else "#e00",
                         zorder=10, xytext=(2, 2), textcoords="offset points")
    ax2.legend(handles=h, fontsize=13, loc="lower left")
    ax2.set_title("ZOOM vung Vam Co — 65 nhanh bo", fontsize=15)
    ax2.set_aspect("equal")
    ax2.grid(alpha=.2)
    ax2.set_xlim(600000, 725000)
    ax2.set_ylim(1135000, 1225000)
    p2 = out / "bo_cuoi_zoom.png"
    fig2.savefig(p2, dpi=140, bbox_inches="tight")
    plt.close(fig2)

    print(f"BO: {n_bo} | GIU: {n_giu} + ranh 3")
    print(f"-> {p}")
    print(f"-> {p2}")


if __name__ == "__main__":
    main()
