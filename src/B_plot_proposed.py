#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B_plot_proposed.py — BAN DO CAC NHANH DE XUAT DUA VAO LUOI

Ve MOI nhanh MIKE co survey 2020 (khoang cach chieu < nguong), phan tang de
xem nen bat dau tu dau. KHONG doc geometrie — ve TRUOC khi sinh luoi.

Nguon: nwk11 (toa do + connection) + catalog_survey.csv (survey 2020 da tra
theo toa do). Ten nhanh lay TRUC TIEP tu MIKE, khong chuan hoa.

RA output/audit/:
  proposed_network.png   — ban do: nhanh chinh (net lien) vs cu lao (net dut),
                           mau theo song me, cham survey 2020, nut noi
  proposed_tiers.png     — 4 bang con: tang tien / hau / truc / full
  proposed_table.png     — bang: nhanh, dai, n_survey, n_xsec_mike, US/DS
  proposed_report.txt

DUNG:
  python3 src/B_plot_proposed.py
  python3 src/B_plot_proposed.py --max-dist 200 --tier full
"""
import argparse
import math
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

# nhanh chinh (song me) -> mau
SONG_ME = {
    "Tien":       "#1f77b4",
    "BASSAC":     "#d62728",
    "VamNao":     "#9467bd",
    "CoChien":    "#2ca02c",
    "Ham Luong":  "#ff7f0e",
    "CuaTieu":    "#8c564b",
    "CuaDai":     "#e377c2",
    "CuaCoChien": "#7f7f7f",
    "CuaCungHau": "#bcbd22",
    "CuaDinhAn":  "#17becf",
    "CuaTranDe":  "#aec7e8",
}
# nhanh cu lao -> song me
def me_cua(ten):
    t = ten.strip()
    if t in SONG_ME:
        return t
    for p, m in (("Tien_", "Tien"), ("Hau_", "BASSAC"), ("CoChien_", "CoChien"),
                 ("HamLuong_", "Ham Luong"), ("CuaDai_", "CuaDai"),
                 ("VamNao", "VamNao"), ("BASSAC", "BASSAC")):
        if t.startswith(p):
            return m
    # nhanh ten rieng
    return {"CaiBe_TG": "Tien", "NamThon": "Tien", "Lap Vo": "Tien"}.get(t, "Tien")


TIERS = {
    "tien": ["Tien", "Tien_1", "Tien_2", "Tien_3", "Tien_4", "Tien_5", "Tien_6",
             "Tien_7", "Tien_8", "Tien_9", "CaiBe_TG", "NamThon"],
    "hau":  ["BASSAC", "Hau_1", "Hau_2", "Hau_3", "Hau_4", "Hau_5", "Hau_6",
             "Hau_7", "Hau_8", "Hau_9"],
}
TIERS["truc"] = TIERS["tien"] + TIERS["hau"] + ["VamNao"]


def read_nwk(nwk11):
    """-> {ten: {ch0, ch1, us, ds, xy:[(x,y)]}}"""
    text = Path(nwk11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    out = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'\s*,\s*'[^']*'\s*,"
                       r"\s*([\-\d.e]+)\s*,\s*([\-\d.e]+)", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if not (dm and pm):
            continue
        nm = dm.group(1)
        cm = re.search(r"connections\s*=\s*'([^']*)'\s*,\s*([\-\d.e]+)\s*,"
                       r"\s*'([^']*)'\s*,\s*([\-\d.e]+)", bt)
        v = [pts[int(p)] for p in pm.group(1).split(",")
             if p.strip() and int(p) in pts]
        if len(v) < 2:
            continue
        try:
            ch0, ch1 = float(dm.group(2)), float(dm.group(3))
        except ValueError:
            continue
        rec = out.setdefault(nm, {"ch0": ch0, "ch1": ch1, "us": None,
                                  "ds": None, "xy": []})
        rec["ch0"] = min(rec["ch0"], ch0)
        rec["ch1"] = max(rec["ch1"], ch1)
        rec["xy"].extend(v)
        if cm:
            if cm.group(1):
                rec["us"] = (cm.group(1), float(cm.group(2)))
            if cm.group(3):
                rec["ds"] = (cm.group(3), float(cm.group(4)))
    return out


def plen(xy):
    return sum(math.hypot(xy[i+1][0]-xy[i][0], xy[i+1][1]-xy[i][1])
               for i in range(len(xy)-1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-dist", type=float, default=200.0,
                    help="survey chieu xa hon nguong nay -> khong tinh")
    ap.add_argument("--tier", default="all",
                    choices=["all", "tien", "hau", "truc"])
    args = ap.parse_args()

    out = CFG.OUT.OUTPUT / "audit"
    out.mkdir(parents=True, exist_ok=True)
    print("=== BAN DO NHANH DE XUAT ===\n")

    cat_p = CFG.OUT.ROOT / "data_ref/catalog/catalog_survey.csv"
    if not cat_p.exists():
        raise SystemExit(f"[LOI] chua co {cat_p} — chay build_catalog.py truoc")
    cat = pd.read_csv(cat_p, sep=";")
    cat["d"] = pd.to_numeric(cat["mike1_d"], errors="coerce")
    sv = cat[(cat["co_z"] == "yes") & (cat["d"] < args.max_dist)]
    nsv = sv["mike1"].value_counts().to_dict()
    prop = sorted(nsv)
    print(f"Survey 2020 co z, chieu <{args.max_dist:.0f}m: {len(sv)} diem")
    print(f"Nhanh MIKE duoc chieu vao       : {len(prop)}\n")

    nwk = read_nwk(CFG.DATA.NWK11)
    print(f"nwk11: {len(nwk)} nhanh co polyline")
    miss = [b for b in prop if b not in nwk]
    if miss:
        print(f"[!] {len(miss)} nhanh khong thay trong nwk11: {miss}")
    prop = [b for b in prop if b in nwk]

    # xns MIKE
    nxs = {}
    mk_p = CFG.OUT.ROOT / "data_ref/catalog/catalog_mike.csv"
    if mk_p.exists():
        mk = pd.read_csv(mk_p, sep=";")
        nxs = mk["location_id"].value_counts().to_dict()

    # ------------- bang tong hop -------------
    rows = []
    for b in prop:
        r = nwk[b]
        me = me_cua(b)
        rows.append({
            "ten": b, "song_me": me,
            "loai": "chinh" if b in SONG_ME else "cu_lao",
            "dai_km": round(plen(r["xy"]) / 1000, 1),
            "n_survey": nsv.get(b, 0),
            "n_xsec_mike": nxs.get(b, 0),
            "US": f"{r['us'][0]}@{r['us'][1]:.0f}" if r["us"] else "TU_DO",
            "DS": f"{r['ds'][0]}@{r['ds'][1]:.0f}" if r["ds"] else "TU_DO",
        })
    d = pd.DataFrame(rows).sort_values(["song_me", "loai", "ten"],
                                       ascending=[True, False, True])
    d.to_csv(out / "proposed_branches.csv", sep=";", index=False)

    # ------------- HINH 1: ban do -------------
    fig, ax = plt.subplots(figsize=(17, 19))
    for _, r in d.iterrows():
        xy = nwk[r["ten"]]["xy"]
        X = [p[0] for p in xy]
        Y = [p[1] for p in xy]
        c = SONG_ME.get(r["song_me"], "#333333")
        chinh = r["loai"] == "chinh"
        ax.plot(X, Y, "-" if chinh else "--", color=c,
                lw=2.6 if chinh else 1.5, alpha=1.0 if chinh else .8, zorder=3)
        # nhan giua nhanh
        mid = xy[len(xy)//2]
        ax.annotate(r["ten"], mid, fontsize=7 if not chinh else 9,
                    weight="bold" if chinh else "normal", color=c, zorder=8,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white",
                              ec=c, alpha=.8, lw=.6))
    # cham survey 2020
    ax.scatter(pd.to_numeric(sv["x_utm"]), pd.to_numeric(sv["y_utm"]),
               s=16, c="k", marker="o", zorder=6,
               label=f"survey 2020 ({len(sv)})")
    # nut noi (diem US/DS)
    for _, r in d.iterrows():
        rec = nwk[r["ten"]]
        for conn in (rec["us"], rec["ds"]):
            if conn and conn[0] in nwk:
                xy = rec["xy"]
                p = xy[0] if conn is rec["us"] else xy[-1]
                ax.plot(p[0], p[1], "D", color="#ff7f0e", ms=5, zorder=7,
                        mec="k", mew=.5)

    h = [Line2D([0], [0], color=SONG_ME[s], lw=2.6, label=s) for s in SONG_ME]
    h += [Line2D([0], [0], color="k", lw=2.6, label="nhanh CHINH (net lien)"),
          Line2D([0], [0], color="k", lw=1.5, ls="--", label="nhanh CU LAO (net dut)"),
          Line2D([0], [0], marker="o", color="w", markerfacecolor="k", ms=7,
                 label=f"survey 2020 ({len(sv)})"),
          Line2D([0], [0], marker="D", color="w", markerfacecolor="#ff7f0e",
                 ms=8, label="nut noi")]
    ax.legend(handles=h, fontsize=9, loc="lower left", ncol=2)
    nch = (d["loai"] == "chinh").sum()
    ax.set_title(f"NHANH DE XUAT DUA VAO LUOI: {len(d)} nhanh "
                 f"({nch} chinh + {len(d)-nch} cu lao)\n"
                 f"{d['n_survey'].sum()} mat cat survey 2020, "
                 f"tong dai {d['dai_km'].sum():.0f} km", fontsize=14)
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_aspect("equal")
    ax.grid(alpha=.25)
    p1 = out / "proposed_network.png"
    fig.savefig(p1, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {p1}")

    # ------------- HINH 2: cac tang -------------
    tiers = [("tien", "TANG 1: song Tien"), ("hau", "TANG 2: song Hau"),
             ("truc", "TANG 3: truc chinh (Tien+Hau+VamNao)"),
             ("all", f"TANG 4: day du ({len(d)} nhanh)")]
    fig, axes = plt.subplots(2, 2, figsize=(19, 21))
    for ax, (key, ttl) in zip(axes.ravel(), tiers):
        sel = list(d["ten"]) if key == "all" else \
            [b for b in TIERS[key] if b in nwk]
        # them cua neu la tang truc/all
        if key in ("tien", "truc"):
            sel += [b for b in ("CuaTieu", "CuaDai", "CuaDai_1", "CuaDai_2",
                                "CuaDai_3") if b in nwk]
        if key in ("hau", "truc"):
            sel += [b for b in ("CuaDinhAn", "CuaTranDe") if b in nwk]
        # nen: moi nhanh (xam)
        for _, r in d.iterrows():
            xy = nwk[r["ten"]]["xy"]
            ax.plot([p[0] for p in xy], [p[1] for p in xy], "-",
                    color="#e0e0e0", lw=.8, zorder=1)
        ns = 0
        for b in sel:
            if b not in nwk:
                continue
            xy = nwk[b]["xy"]
            c = SONG_ME.get(me_cua(b), "#333")
            chinh = b in SONG_ME
            ax.plot([p[0] for p in xy], [p[1] for p in xy],
                    "-" if chinh else "--", color=c,
                    lw=2.4 if chinh else 1.4, zorder=3)
            ns += nsv.get(b, 0)
        sub = sv[sv["mike1"].isin(sel)]
        ax.scatter(pd.to_numeric(sub["x_utm"]), pd.to_numeric(sub["y_utm"]),
                   s=12, c="k", zorder=5)
        ax.set_title(f"{ttl}\n{len(sel)} nhanh, {ns} mat cat survey 2020",
                     fontsize=12)
        ax.set_aspect("equal")
        ax.grid(alpha=.2)
        ax.tick_params(labelsize=7)
    fig.suptitle("PHAN TANG XAY DUNG LUOI — moi tang phai FIN CORRECTE moi len tang sau",
                 fontsize=15)
    fig.tight_layout(rect=[0, 0, 1, .98])
    p2 = out / "proposed_tiers.png"
    fig.savefig(p2, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {p2}")

    # ------------- HINH 3: bang -------------
    fig, ax = plt.subplots(figsize=(16, 0.36 * len(d) + 2))
    ax.axis("off")
    cols = ["ten", "song_me", "loai", "dai_km", "n_survey", "n_xsec_mike",
            "US", "DS"]
    cells = d[cols].astype(str).values.tolist()
    t = ax.table(cellText=cells, colLabels=cols, loc="center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(8)
    t.scale(1, 1.35)
    for i, r in enumerate(d.itertuples()):
        c = SONG_ME.get(r.song_me, "#fff")
        for j in range(len(cols)):
            t[(i+1, j)].set_facecolor(c + "22" if c.startswith("#") else "#fff")
            if r.loai == "chinh":
                t[(i+1, j)].set_text_props(weight="bold")
    ax.set_title(f"BANG NHANH DE XUAT ({len(d)} nhanh) — dam = nhanh chinh",
                 fontsize=13, pad=16)
    fig.tight_layout()
    p3 = out / "proposed_table.png"
    fig.savefig(p3, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {p3}")

    # ------------- report -------------
    L = []
    A = L.append
    A("NHANH DE XUAT DUA VAO LUOI")
    A("=" * 70)
    A(f"\nNguong chieu survey : {args.max_dist:.0f} m")
    A(f"Tong nhanh          : {len(d)} ({nch} chinh + {len(d)-nch} cu lao)")
    A(f"Tong dai            : {d['dai_km'].sum():.0f} km")
    A(f"Mat cat survey 2020 : {d['n_survey'].sum()}")
    A(f"Mat cat MIKE        : {d['n_xsec_mike'].sum()}")
    A("\n--- THEO SONG ME ---")
    for me, g in d.groupby("song_me"):
        A(f"  {me:12s} {len(g):2d} nhanh, {g['dai_km'].sum():6.1f} km, "
          f"survey={g['n_survey'].sum():3d}, mike={g['n_xsec_mike'].sum():4d}")
    A("\n--- PHAN TANG DE XUAT ---")
    for key in ("tien", "hau", "truc"):
        sel = [b for b in TIERS[key] if b in nwk]
        ns = sum(nsv.get(b, 0) for b in sel)
        km = sum(plen(nwk[b]["xy"]) / 1000 for b in sel)
        A(f"  {key:6s} {len(sel):2d} nhanh, {km:6.1f} km, survey={ns:3d}")
    A(f"  {'all':6s} {len(d):2d} nhanh, {d['dai_km'].sum():6.1f} km, "
      f"survey={d['n_survey'].sum():3d}")
    A("\n--- CHI TIET ---")
    A(f"{'ten':14s} {'me':11s} {'loai':7s} {'km':>6s} {'sv':>4s} {'mike':>5s}  US -> DS")
    for _, r in d.iterrows():
        A(f"{r['ten']:14s} {r['song_me']:11s} {r['loai']:7s} {r['dai_km']:6.1f} "
          f"{r['n_survey']:4d} {r['n_xsec_mike']:5d}  {r['US']} -> {r['DS']}")

    (out / "proposed_report.txt").write_text("\n".join(L), encoding="utf-8")
    print(f"   -> {out}/proposed_report.txt")
    print("\n" + "\n".join(L))
    print(f"\nXONG -> {out}/")


if __name__ == "__main__":
    main()
