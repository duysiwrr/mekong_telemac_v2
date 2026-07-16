#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B_plot_grid.py — IN HINH LUOI TINH TOAN (kiem mat truoc khi chay MASCARET)

Ve DUNG cai dang tinh: doc geometrie + mascaret.xcas + init.lig + *.loi
trong 1 thu muc model, KHONG doc ledger/nwk11 (khac plot_network_xsec.py —
cai do ve toan bo 1899 nhanh, khong phai luoi dang chay).

RA 4 hinh trong <outdir>/plots/:
  1_longitudinal.png  — TRAC DOC tung bief: day (min/max), Z init, vach mat cat,
                        vi tri bien (Q do / Z xanh), nut giao. Cot chinh de soi
                        cho kho va cho chenh Z.
  2_nodes.png         — SO DO NUT: Z init moi bief tai moi nut, to do neu chenh
                        > nguong. Thay ngay cho nao nuoc se xa.
  3_sections.png      — MAT CAT NGANG: ve N mat cat dai dien + duong Z init,
                        do sau nuoc h = Z - day.
  4_summary.png       — BANG TONG HOP: moi bief 1 dong (n_prof, day, Z, h_min,
                        rong TB, bien gan vao).

DUNG:
  python3 src/B_plot_grid.py --outdir output/grid/backbone
  python3 src/B_plot_grid.py --outdir output/grid/backbone --nsec 12
"""
import argparse
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


# ---------------------------------------------------------------- doc du lieu
def read_geometrie(p):
    """-> list profil {bief, ten, absc, y[], z[]}"""
    lines = p.read_text(encoding="latin-1", errors="replace").splitlines()
    profs, cur = [], None
    for l in lines:
        if l.startswith("PROFIL"):
            if cur:
                profs.append(cur)
            q = l.split()
            m = re.search(r"Bief_(\d+)", q[1])
            cur = {"bief": int(m.group(1)) if m else 0, "ten": q[2],
                   "absc": float(q[3]), "y": [], "z": []}
        elif cur and l.strip():
            q = l.split()
            if len(q) >= 2:
                try:
                    cur["y"].append(float(q[0]))
                    cur["z"].append(float(q[1]))
                except ValueError:
                    pass
    if cur:
        profs.append(cur)
    return profs


def read_init(p):
    """-> (X[], Z[], Q[])"""
    t = p.read_text(encoding="ascii", errors="replace")

    def blk(a, b):
        m = re.search(rf"\n {a}\n(.*?)\n {b}\n", t, re.S)
        return [float(v) for v in m.group(1).split()] if m else []
    return blk("X", "Z"), blk("Z", "Q"), blk("Q", "FIN")


def read_xcas(p):
    """-> (nb_bief, nodes[list of ext], free{ext:{type,nom}})"""
    x = p.read_text(encoding="latin-1", errors="replace")
    nb = int(re.search(r"<listeBranches>\s*<nb>(\d+)</nb>", x, re.S).group(1))
    m = re.search(r"<listeNoeuds>(.*?)</listeNoeuds>", x, re.S)
    nodes = []
    if m:
        for g in re.findall(r"<num>([\d\s]+)</num>", m.group(1)):
            v = [int(k) for k in g.split() if int(k) > 0]
            if v:
                nodes.append(v)
    m = re.search(r"<extrLibres>(.*?)</extrLibres>", x, re.S)
    free = {}
    if m:
        e = re.search(r"<numExtrem>([\d\s]+)</numExtrem>", m.group(1))
        c = re.search(r"<typeCond>([\d\s]+)</typeCond>", m.group(1))
        n = re.findall(r"<string>([^<]*)</string>", m.group(1))
        if e and c:
            for i, (ee, tt) in enumerate(zip([int(v) for v in e.group(1).split()],
                                             [int(v) for v in c.group(1).split()])):
                free[ee] = {"type": tt, "nom": n[i] if i < len(n) else "?"}
    return nb, nodes, free


def read_loi_first(p):
    """gia tri dau tien trong file .loi"""
    for l in p.read_text(encoding="ascii", errors="replace").splitlines():
        l = l.strip()
        if l and not l.startswith("#") and l != "S":
            q = l.split()
            if len(q) >= 2:
                try:
                    return float(q[1])
                except ValueError:
                    pass
    return None


# ------------------------------------------------------------------ hinh 1
def plot_longitudinal(path, profs, Z, nb, free, loi0, bief_ext):
    by = defaultdict(list)
    for i, p in enumerate(profs):
        by[p["bief"]].append((p, Z[i] if i < len(Z) else np.nan, i + 1))

    ncol = 3
    nrow = int(np.ceil(nb / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(6 * ncol, 3.2 * nrow))
    axes = np.atleast_1d(axes).ravel()

    for k in range(nb):
        ax = axes[k]
        b = k + 1
        items = by.get(b, [])
        if not items:
            ax.text(.5, .5, f"Bief_{b}\nKHONG CO PROFIL", ha="center",
                    va="center", color="red", transform=ax.transAxes)
            ax.set_xticks([]); ax.set_yticks([])
            continue
        x = np.array([it[0]["absc"] for it in items])
        x_km = (x - x.min()) / 1000.0
        bed = np.array([min(it[0]["z"]) for it in items])
        top = np.array([max(it[0]["z"]) for it in items])
        zi = np.array([it[1] for it in items])

        ax.fill_between(x_km, bed, top, color="#d9c9a3", alpha=.45, zorder=1,
                        label="long song")
        ax.plot(x_km, bed, "-", color="#8b5a2b", lw=1.4, zorder=3, label="day (min)")
        ax.plot(x_km, top, "-", color="#b0895c", lw=.7, zorder=3, label="bo (max)")
        ax.plot(x_km, zi, "-", color="#1f77b4", lw=1.8, zorder=4, label="Z init")
        ax.fill_between(x_km, bed, zi, where=(zi > bed), color="#9ecae1",
                        alpha=.55, zorder=2)
        for xx in x_km:
            ax.axvline(xx, color="#2ca02c", lw=.4, alpha=.5, zorder=1)

        h = zi - bed
        dry = h < 0.5
        if dry.any():
            ax.plot(x_km[dry], zi[dry], "v", color="red", ms=7, zorder=6,
                    label=f"KHO h<0.5m ({dry.sum()})")

        # bien gan vao bief nay
        for e in (2 * b - 1, 2 * b):
            if e in free:
                f = free[e]
                xe = x_km[0] if e == 2 * b - 1 else x_km[-1]
                col = "#d62728" if f["type"] == 1 else "#17becf"
                ax.axvline(xe, color=col, lw=2.5, zorder=5)
                v0 = loi0.get(f["nom"])
                lbl = f["nom"] + (f"\n{v0:.2f}" if v0 is not None else "")
                ax.annotate(lbl, (xe, ax.get_ylim()[1]), color=col, fontsize=7,
                            ha="left" if e == 2 * b - 1 else "right",
                            va="top", zorder=7)
                if f["type"] == 2 and v0 is not None:
                    ax.axhline(v0, color=col, ls=":", lw=1, zorder=4)

        hmin = float(np.nanmin(h))
        ttl = f"Bief_{b}  {items[0][0]['ten'].split('_')[0]}  n={len(items)}"
        ax.set_title(ttl + f"   h_min={hmin:.2f}m",
                     fontsize=9, color="red" if hmin < 0.5 else "black")
        ax.set_xlabel("km trong bief", fontsize=7)
        ax.set_ylabel("cao do (m)", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=.25)
        if k == 0:
            ax.legend(fontsize=6, loc="lower right")

    for k in range(nb, len(axes)):
        axes[k].axis("off")

    fig.suptitle("TRAC DOC TUNG BIEF — day, Z init, mat cat (vach xanh la), "
                 "bien (do=Q, xanh=Z)", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, .97])
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


# ------------------------------------------------------------------ hinh 2
def plot_nodes(path, profs, Z, nodes, free, warn=1.0):
    zb = {}
    for i, p in enumerate(profs):
        if i < len(Z):
            zb.setdefault(p["bief"], []).append(Z[i])
    zb = {b: float(np.mean(v)) for b, v in zb.items()}

    fig, ax = plt.subplots(figsize=(13, 6))
    xs, labels = [], []
    for i, grp in enumerate(nodes):
        bs = sorted(set((e + 1) // 2 for e in grp))
        vals = [zb.get(b, np.nan) for b in bs]
        d = np.nanmax(vals) - np.nanmin(vals)
        col = "#d62728" if d > warn else "#2ca02c"
        for j, (b, v) in enumerate(zip(bs, vals)):
            ax.plot(i, v, "o", color=col, ms=9, zorder=3)
            ax.annotate(f"B{b}", (i, v), fontsize=7, xytext=(4, 3),
                        textcoords="offset points")
        ax.plot([i, i], [np.nanmin(vals), np.nanmax(vals)], "-",
                color=col, lw=2.5, zorder=2)
        ax.annotate(f"{d:.2f}m", (i, np.nanmax(vals)), fontsize=8, color=col,
                    ha="center", va="bottom", xytext=(0, 8),
                    textcoords="offset points", weight="bold")
        xs.append(i); labels.append(f"N{i+1}")
    ax.axhline(0, color="k", lw=.5)
    ax.set_xticks(xs); ax.set_xticklabels(labels)
    ax.set_ylabel("Z init (m)")
    ax.set_title(f"CHENH Z INIT TAI MOI NUT (do = chenh > {warn}m -> nguy co xa nuoc)")
    ax.grid(alpha=.3, axis="y")
    ax.legend(handles=[
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2ca02c",
               ms=9, label=f"chenh <= {warn}m (OK)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#d62728",
               ms=9, label=f"chenh > {warn}m (NGUY)")], fontsize=9)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


# ------------------------------------------------------------------ hinh 3
def plot_sections(path, profs, Z, nsec=9):
    idx = np.linspace(0, len(profs) - 1, min(nsec, len(profs))).astype(int)
    ncol = 3
    nrow = int(np.ceil(len(idx) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(5.5 * ncol, 3 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for k, i in enumerate(idx):
        ax = axes[k]
        p = profs[i]
        y, z = np.array(p["y"]), np.array(p["z"])
        zi = Z[i] if i < len(Z) else np.nan
        ax.fill_between(y, z, z.max(), color="#e8e0cc", alpha=.5)
        ax.plot(y, z, "-", color="#8b5a2b", lw=1.3)
        ax.plot(y, z, ".", color="#8b5a2b", ms=2)
        if not np.isnan(zi):
            ax.axhline(zi, color="#1f77b4", lw=1.6)
            ax.fill_between(y, z, zi, where=(zi > z), color="#9ecae1", alpha=.6)
            h = zi - z.min()
            ax.set_title(f"#{i+1} {p['ten'][:18]}  Bief_{p['bief']}\n"
                         f"h={h:.1f}m  rong={y[-1]-y[0]:.0f}m",
                         fontsize=8, color="red" if h < 0.5 else "black")
        ax.set_xlabel("y (m)", fontsize=7)
        ax.set_ylabel("z (m)", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=.25)
    for k in range(len(idx), len(axes)):
        axes[k].axis("off")
    fig.suptitle("MAT CAT NGANG dai dien — nau=day, xanh=Z init, "
                 "vung xanh nhat=nuoc", fontsize=12)
    fig.tight_layout(rect=[0, 0, 1, .96])
    fig.savefig(path, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


# ------------------------------------------------------------------ hinh 4
def plot_summary(path, profs, Z, nb, free, loi0):
    rows = []
    by = defaultdict(list)
    for i, p in enumerate(profs):
        by[p["bief"]].append((p, Z[i] if i < len(Z) else np.nan))
    for b in range(1, nb + 1):
        it = by.get(b, [])
        if not it:
            rows.append([f"Bief_{b}", "0", "-", "-", "-", "-", "-", "KHONG PROFIL"])
            continue
        bed = [min(p["z"]) for p, _ in it]
        zi = [z for _, z in it]
        h = [z - min(p["z"]) for p, z in it]
        w = [p["y"][-1] - p["y"][0] for p, _ in it]
        bnd = []
        for e in (2 * b - 1, 2 * b):
            if e in free:
                v = loi0.get(free[e]["nom"])
                bnd.append(free[e]["nom"] + (f"={v:.2f}" if v is not None else ""))
        rows.append([f"Bief_{b}", str(len(it)), it[0][0]["ten"].split("_")[0][:10],
                     f"{min(bed):.1f}", f"{max(bed):.1f}", f"{np.mean(zi):.2f}",
                     f"{min(h):.2f}", ", ".join(bnd) if bnd else "-"])

    fig, ax = plt.subplots(figsize=(15, 0.5 * nb + 2))
    ax.axis("off")
    cols = ["bief", "n_prof", "song", "day_min", "day_max", "Z_init",
            "h_min", "bien"]
    t = ax.table(cellText=rows, colLabels=cols, loc="center", cellLoc="left")
    t.auto_set_font_size(False)
    t.set_fontsize(9)
    t.scale(1, 1.5)
    for i, r in enumerate(rows):
        try:
            if float(r[6]) < 0.5:
                for j in range(len(cols)):
                    t[(i + 1, j)].set_facecolor("#ffcccc")
        except (ValueError, KeyError):
            pass
    ax.set_title("TONG HOP LUOI TINH TOAN (do = bief co mat cat kho h<0.5m)",
                 fontsize=12, pad=18)
    fig.tight_layout()
    fig.savefig(path, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--nsec", type=int, default=9, help="so mat cat ve o hinh 3")
    ap.add_argument("--warn-drop", type=float, default=1.0)
    args = ap.parse_args()

    out = Path(args.outdir)
    pdir = out / "plots"
    pdir.mkdir(parents=True, exist_ok=True)

    print("=== IN HINH LUOI TINH TOAN ===\n")
    profs = read_geometrie(out / "geometrie")
    X, Z, Q = read_init(out / "init.lig")
    nb, nodes, free = read_xcas(out / "mascaret.xcas")
    loi0 = {}
    for f in sorted(out.glob("*.loi")):
        loi0[f.stem] = read_loi_first(f)

    print(f"geometrie : {len(profs)} PROFIL / {nb} bief")
    print(f"init.lig  : {len(Z)} diem Z ({min(Z):.2f}..{max(Z):.2f}m), "
          f"Q={Q[0] if Q else '?'}")
    print(f"xcas      : {len(nodes)} nut, {len(free)} bien tu do")
    print(f"loi       : {len(loi0)} file — " +
          ", ".join(f"{k}={v:.2f}" for k, v in list(loi0.items())[:3]) + " ...")

    if len(profs) != len(Z):
        print(f"\n[!] LECH: {len(profs)} PROFIL nhung {len(Z)} gia tri Z")

    # mat cat kho
    dry = [(i + 1, p["ten"], p["bief"], Z[i] - min(p["z"]))
           for i, p in enumerate(profs)
           if i < len(Z) and Z[i] - min(p["z"]) < 0.5]
    print(f"\nMat cat KHO (h<0.5m): {len(dry)}")
    for i, ten, b, h in dry[:10]:
        print(f"   #{i} {ten} (Bief_{b}) h={h:.2f}m")

    bief_ext = {}
    print("\nVe hinh...")
    plot_longitudinal(pdir / "1_longitudinal.png", profs, Z, nb, free, loi0, bief_ext)
    plot_nodes(pdir / "2_nodes.png", profs, Z, nodes, free, args.warn_drop)
    plot_sections(pdir / "3_sections.png", profs, Z, args.nsec)
    plot_summary(pdir / "4_summary.png", profs, Z, nb, free, loi0)
    print(f"\nXONG -> {pdir}/")


if __name__ == "__main__":
    main()
