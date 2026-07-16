#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B_plot_network.py — BAN DO KHONG GIAN LUOI DANG TINH

Ve DUNG cac nhanh dang co trong model (doc geometrie de biet bief nao co that),
lay toa do tu nwk11. KHAC plot_network_xsec.py (ve toan bo 1899 nhanh ledger).

RA <outdir>/plots/:
  5_network_map.png    — ban do: nhanh (mau rieng), ranh gioi bief, nut, bien,
                         vach mat cat ve DUNG BE RONG THAT -> lo mat cat lac cho
  6_width_profile.png  — be rong doc theo tung song: soi cho nhay bat thuong

DUNG:
  python3 src/B_plot_network.py --outdir output/grid/backbone
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
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def read_geometrie(p):
    lines = p.read_text(encoding="latin-1", errors="replace").splitlines()
    profs, cur = [], None
    for l in lines:
        if l.startswith("PROFIL"):
            if cur:
                profs.append(cur)
            q = l.split()
            m = re.search(r"Bief_(\d+)", q[1])
            # ten profil = <song>_<chainage>
            mm = re.match(r"(.+)_(\d+)$", q[2])
            cur = {"bief": int(m.group(1)) if m else 0,
                   "song": mm.group(1) if mm else q[2],
                   "ch": float(mm.group(2)) if mm else 0.0,
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


def read_xcas(p):
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


def load_polylines(names):
    """{ten: [(x,y,chainage)...]} tu nwk11, chi cac nhanh trong `names`."""
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    pts, pch = {}, {}
    for m in re.finditer(
            r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,"
            r"\s*[\-\d.]+\s*,\s*([\-\d.]+)", text):
        pid = int(m.group(1))
        x, y, ch = float(m.group(2)), float(m.group(3)), float(m.group(4))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[pid] = (x, y)
            pch[pid] = ch
    nn = {norm(n) for n in names}
    poly = defaultdict(list)
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if not (dm and pm):
            continue
        nm = dm.group(1)
        if norm(nm) not in nn:
            continue
        ids = [int(p) for p in pm.group(1).split(",") if p.strip()]
        for pid in ids:
            if pid in pts:
                poly[nm].append((pts[pid][0], pts[pid][1], pch[pid]))
    for k in poly:
        poly[k].sort(key=lambda t: t[2])
    return poly


def interp_at(pl, ch):
    """Toa do + huong tai chainage ch tren polyline pl=[(x,y,ch)...]."""
    if len(pl) < 2:
        return None
    chs = [p[2] for p in pl]
    if ch <= chs[0]:
        i = 0
    elif ch >= chs[-1]:
        i = len(pl) - 2
    else:
        i = max(j for j in range(len(pl) - 1) if chs[j] <= ch)
    x0, y0, c0 = pl[i]
    x1, y1, c1 = pl[i + 1]
    t = (ch - c0) / (c1 - c0) if c1 > c0 else 0.0
    t = max(0.0, min(1.0, t))
    x, y = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    return (x, y, dx / d, dy / d) if d > 0 else (x, y, 1.0, 0.0)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--wide", type=float, default=2500.0,
                    help="be rong (m) tren nguong nay -> to do canh bao")
    args = ap.parse_args()

    out = Path(args.outdir)
    pdir = out / "plots"
    pdir.mkdir(parents=True, exist_ok=True)

    print("=== BAN DO LUOI DANG TINH ===\n")
    profs = read_geometrie(out / "geometrie")
    nb, nodes, free = read_xcas(out / "mascaret.xcas")

    songs = sorted({p["song"] for p in profs})
    print(f"geometrie: {len(profs)} PROFIL / {nb} bief")
    print(f"Song trong model ({len(songs)}): {songs}\n")

    poly = load_polylines(songs)
    print("Polyline tu nwk11:")
    for s in songs:
        pl = poly.get(s) or poly.get(s.replace("_", " "))
        if pl:
            L = sum(math.hypot(pl[i+1][0]-pl[i][0], pl[i+1][1]-pl[i][1])
                    for i in range(len(pl)-1))
            print(f"   {s:14s} {len(pl):4d} diem, dai {L/1000:6.1f} km")
        else:
            print(f"   {s:14s} [!] KHONG TIM THAY trong nwk11")

    # gan song -> polyline (xu ly 'Ham Luong' vs 'Ham_Luong')
    pmap = {}
    for s in songs:
        for k in poly:
            if norm(k) == norm(s):
                pmap[s] = poly[k]
                break

    # ---------------- HINH 5: ban do ----------------
    cmap = plt.get_cmap("tab20")
    colors = {s: cmap(i % 20) for i, s in enumerate(songs)}

    fig, ax = plt.subplots(figsize=(17, 19))

    # tuyen song
    for s in songs:
        pl = pmap.get(s)
        if not pl:
            continue
        X = [p[0] for p in pl]
        Y = [p[1] for p in pl]
        ax.plot(X, Y, "-", color=colors[s], lw=2.2, zorder=2, label=s)

    # vach mat cat — DUNG BE RONG THAT
    n_wide = 0
    for p in profs:
        pl = pmap.get(p["song"])
        if not pl:
            continue
        r = interp_at(pl, p["ch"])
        if not r:
            continue
        x, y, dx, dy = r
        w = p["y"][-1] - p["y"][0]
        px, py = -dy, dx           # vuong goc
        h = w / 2.0
        col = "#d62728" if w > args.wide else "#2ca02c"
        if w > args.wide:
            n_wide += 1
        ax.plot([x - px*h, x + px*h], [y - py*h, y + py*h], "-",
                color=col, lw=1.0, zorder=4)

    # ranh gioi bief (dau/cuoi moi bief)
    by = defaultdict(list)
    for p in profs:
        by[p["bief"]].append(p)
    for b, ps in by.items():
        ps.sort(key=lambda q: q["ch"])
        for q, mk in ((ps[0], "o"), (ps[-1], "s")):
            pl = pmap.get(q["song"])
            if not pl:
                continue
            r = interp_at(pl, q["ch"])
            if r:
                ax.plot(r[0], r[1], mk, color="k", ms=5, zorder=6,
                        mfc="w", mew=1.2)
        # nhan bief o giua
        mid = ps[len(ps)//2]
        pl = pmap.get(mid["song"])
        if pl:
            r = interp_at(pl, mid["ch"])
            if r:
                ax.annotate(f"B{b}", (r[0], r[1]), fontsize=11, weight="bold",
                            color="k", zorder=8,
                            bbox=dict(boxstyle="round,pad=0.2", fc="yellow",
                                      ec="k", alpha=.85))

    # bien: ext -> bief -> dau hoac cuoi
    for e, f in free.items():
        b = (e + 1) // 2
        ps = by.get(b)
        if not ps:
            continue
        q = ps[0] if e % 2 == 1 else ps[-1]
        pl = pmap.get(q["song"])
        if not pl:
            continue
        r = interp_at(pl, q["ch"])
        if not r:
            continue
        col = "#d62728" if f["type"] == 1 else "#17becf"
        ax.plot(r[0], r[1], "*", color=col, ms=26, zorder=9,
                mec="k", mew=1.0)
        ax.annotate(f["nom"], (r[0], r[1]), fontsize=10, weight="bold",
                    color=col, zorder=10, xytext=(10, 10),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.25", fc="w", ec=col, alpha=.9))

    # nut giao
    for i, grp in enumerate(nodes):
        bs = sorted(set((x + 1) // 2 for x in grp))
        pos = []
        for b in bs:
            ps = by.get(b)
            if not ps:
                continue
            for q in (ps[0], ps[-1]):
                pl = pmap.get(q["song"])
                if pl:
                    r = interp_at(pl, q["ch"])
                    if r:
                        pos.append((r[0], r[1]))
        if pos:
            cx = float(np.mean([p[0] for p in pos]))
            cy = float(np.mean([p[1] for p in pos]))
            ax.plot(cx, cy, "D", color="#ff7f0e", ms=13, zorder=7,
                    mec="k", mew=1.0)
            ax.annotate(f"N{i+1}", (cx, cy), fontsize=10, weight="bold",
                        color="#7f3f00", zorder=8, xytext=(8, -14),
                        textcoords="offset points")

    h = [Line2D([0], [0], color=colors[s], lw=2.5, label=s) for s in songs]
    h += [
        Line2D([0], [0], color="#2ca02c", lw=2,
               label=f"mat cat (rong <= {args.wide:.0f}m)"),
        Line2D([0], [0], color="#d62728", lw=2,
               label=f"mat cat RONG > {args.wide:.0f}m ({n_wide})"),
        Line2D([0], [0], marker="D", color="w", markerfacecolor="#ff7f0e",
               ms=11, label=f"nut giao ({len(nodes)})"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#d62728",
               ms=18, label="bien Q"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#17becf",
               ms=18, label="bien Z"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="w",
               markeredgecolor="k", ms=8, label="dau bief"),
        Line2D([0], [0], marker="s", color="w", markerfacecolor="w",
               markeredgecolor="k", ms=8, label="cuoi bief"),
    ]
    ax.legend(handles=h, fontsize=9, loc="lower left", ncol=2)
    ax.set_title(f"LUOI DANG TINH: {len(songs)} nhanh -> {nb} bief, "
                 f"{len(nodes)} nut, {len(free)} bien, {len(profs)} mat cat\n"
                 f"(vach = mat cat ve dung be rong that)", fontsize=14)
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_aspect("equal")
    ax.grid(alpha=.25)
    p5 = pdir / "5_network_map.png"
    fig.savefig(p5, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"\n   -> {p5}")

    # ---------------- HINH 6: be rong doc song ----------------
    fig, axes = plt.subplots(len(songs), 1, figsize=(15, 2.3 * len(songs)),
                             squeeze=False)
    for i, s in enumerate(songs):
        ax = axes[i][0]
        ps = sorted([p for p in profs if p["song"] == s], key=lambda q: q["ch"])
        ch = np.array([p["ch"] for p in ps]) / 1000.0
        w = np.array([p["y"][-1] - p["y"][0] for p in ps])
        ax.plot(ch, w, "-o", color="#1f77b4", ms=3, lw=1.2)
        bad = w > args.wide
        if bad.any():
            ax.plot(ch[bad], w[bad], "o", color="#d62728", ms=6,
                    label=f"rong > {args.wide:.0f}m ({bad.sum()})")
            ax.legend(fontsize=7)
        # danh dau ranh gioi bief
        for b in sorted({p["bief"] for p in ps}):
            q = [p for p in ps if p["bief"] == b]
            ax.axvline(q[0]["ch"]/1000.0, color="#999", ls="--", lw=.7)
            ax.annotate(f"B{b}", (q[0]["ch"]/1000.0, ax.get_ylim()[1]),
                        fontsize=7, color="#555", va="top")
        ax.set_title(f"{s} — {len(ps)} mat cat, rong {w.min():.0f}..{w.max():.0f}m "
                     f"(TB {w.mean():.0f}m)", fontsize=9)
        ax.set_ylabel("rong (m)", fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=.3)
    axes[-1][0].set_xlabel("chainage (km)")
    fig.suptitle("BE RONG MAT CAT DOC THEO SONG (soi cho nhay bat thuong)",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, .98])
    p6 = pdir / "6_width_profile.png"
    fig.savefig(p6, dpi=140, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {p6}")

    # ---------------- bao cao ----------------
    print(f"\nMat cat rong > {args.wide:.0f}m: {n_wide}/{len(profs)}")
    print("\nBe rong theo song:")
    for s in songs:
        ps = [p for p in profs if p["song"] == s]
        w = [p["y"][-1] - p["y"][0] for p in ps]
        print(f"   {s:14s} n={len(ps):3d}  rong {min(w):6.0f}..{max(w):6.0f}m  "
              f"TB={np.mean(w):6.0f}m")
    print(f"\nXONG -> {pdir}/")


if __name__ == "__main__":
    main()
