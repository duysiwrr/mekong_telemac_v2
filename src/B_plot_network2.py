#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B_plot_network2.py — BAN DO LUOI (ban DE NHIN, thay 5_network_map.png)

KHAC B_plot_network.py:
  1. NET SONG VE THEO BE RONG THAT — song chinh (1000-2400m) net day,
     cu lao (190-600m) net manh. Nhin la biet nhanh nao lon.
  2. NHAN BIEF THUA — chi ghi 1 nhan/NHANH (o giua), khong ghi 47 nhan chen nhau.
     Muon xem chi tiet bief -> doc bief_map.txt.
  3. NUT nho lai (ms 6 thay 13), khong ghi nhan N<so> — 28-51 nhan lam roi.
     Nut chi de THAY VI TRI, tra so hieu o file.
  4. Vach mat cat MANH hon, mau theo Froude neu co .opt.
  5. Ten SONG ghi theo mau nhanh, dat o cuoi nhanh — khong che tuyen.

DUNG:
  python3 src/B_plot_network2.py --outdir output/grid/truc_du
  python3 src/B_plot_network2.py --outdir output/grid/truc_du --nhan-bief  # ghi ca bief
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
            for i, (ee, tt) in enumerate(zip(
                    [int(v) for v in e.group(1).split()],
                    [int(v) for v in c.group(1).split()])):
                free[ee] = {"type": tt, "nom": n[i] if i < len(n) else "?"}
    return nb, nodes, free


def load_polylines(names):
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
        for pid in [int(p) for p in pm.group(1).split(",") if p.strip()]:
            if pid in pts:
                poly[nm].append((pts[pid][0], pts[pid][1], pch[pid]))
    for k in poly:
        poly[k].sort(key=lambda t: t[2])
    return poly


def interp_at(pl, ch):
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


def lw_theo_rong(w, wmin, wmax, lo=0.8, hi=6.0):
    """Be day net TI LE be rong that (can bac 2 cho de nhin)."""
    if wmax <= wmin:
        return (lo + hi) / 2
    t = (math.sqrt(max(w, 1)) - math.sqrt(wmin)) / (math.sqrt(wmax) - math.sqrt(wmin))
    return lo + t * (hi - lo)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--nhan-bief", action="store_true",
                    help="ghi ca nhan B<so> (mac dinh CHI ghi ten song)")
    ap.add_argument("--wide", type=float, default=2500.0)
    args = ap.parse_args()

    out = Path(args.outdir)
    pdir = out / "plots"
    pdir.mkdir(parents=True, exist_ok=True)

    print("=== BAN DO LUOI (ban de nhin) ===\n")
    profs = read_geometrie(out / "geometrie")
    nb, nodes, free = read_xcas(out / "mascaret.xcas")
    songs = sorted({p["song"] for p in profs})
    print(f"geometrie: {len(profs)} PROFIL / {nb} bief | {len(songs)} song")

    poly = load_polylines(songs)
    pmap = {}
    for s in songs:
        for k in poly:
            if norm(k) == norm(s):
                pmap[s] = poly[k]
                break

    # be rong TB moi song -> quyet dinh do day net
    w_song = {}
    for s in songs:
        w = [p["y"][-1] - p["y"][0] for p in profs if p["song"] == s]
        w_song[s] = float(np.mean(w)) if w else 0.0
    wmin, wmax = min(w_song.values()), max(w_song.values())
    print(f"Be rong TB: {wmin:.0f}m ({min(w_song, key=w_song.get)}) .. "
          f"{wmax:.0f}m ({max(w_song, key=w_song.get)})")

    # mau: song chinh dam, cu lao nhat
    CHINH = {"Tien", "BASSAC", "VamNao", "CoChien", "Ham_Luong", "Ham Luong"}
    cmap = plt.get_cmap("tab20")
    colors = {s: cmap(i % 20) for i, s in enumerate(songs)}

    fig, ax = plt.subplots(figsize=(18, 20))

    # ---------- 1. TUYEN SONG — net theo be rong that ----------
    for s in songs:
        pl = pmap.get(s)
        if not pl:
            continue
        lw = lw_theo_rong(w_song[s], wmin, wmax)
        ax.plot([p[0] for p in pl], [p[1] for p in pl], "-",
                color=colors[s], lw=lw, zorder=3, alpha=.9,
                solid_capstyle="round")

    # ---------- 2. VACH MAT CAT — manh, chi to do neu rong bat thuong ----------
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
        px, py = -dy, dx
        h = w / 2.0
        if w > args.wide:
            n_wide += 1
            ax.plot([x - px*h, x + px*h], [y - py*h, y + py*h], "-",
                    color="#d62728", lw=1.6, zorder=5, alpha=.9)
        else:
            ax.plot([x - px*h, x + px*h], [y - py*h, y + py*h], "-",
                    color="#555555", lw=0.5, zorder=4, alpha=.55)

    # ---------- 3. NUT — ve tai TUNG DAU BIEF, khong lay trung binh ----------
    # BUG BAN CU (ke thua tu B_plot_network.py): ve nut o TRUNG BINH CONG toa do
    # cac dau bief. Nut noi 3 bief ma 3 dau khong trung nhau -> trung binh roi
    # GIUA DONG -> nut "choi voi" khong gan vao song nao.
    # SUA: moi dau bief 1 cham. Nut = cum cham sat nhau tren cac nhanh that.
    by = defaultdict(list)
    for p in profs:
        by[p["bief"]].append(p)
    n_nut_ve = 0
    for grp in nodes:
        for e in grp:
            b = (e + 1) // 2
            ps = by.get(b)
            if not ps:
                continue
            ps.sort(key=lambda q: q["ch"])
            q = ps[0] if e % 2 == 1 else ps[-1]   # ext le = dau bief, chan = cuoi
            pl = pmap.get(q["song"])
            if not pl:
                continue
            r = interp_at(pl, q["ch"])
            if r:
                ax.plot(r[0], r[1], "o", color="#ff7f0e", ms=5, zorder=7,
                        mec="k", mew=.6)
                n_nut_ve += 1

    # ---------- 4. NHAN: chi TEN SONG, dat o cuoi nhanh ----------
    for s in songs:
        pl = pmap.get(s)
        if not pl:
            continue
        # dat nhan o 85% chieu dai -> tranh chum o nut giao
        i = int(len(pl) * 0.85)
        x, y = pl[i][0], pl[i][1]
        chinh = s in CHINH
        ax.annotate(s, (x, y), fontsize=11 if chinh else 8,
                    weight="bold" if chinh else "normal",
                    color=colors[s], zorder=10,
                    xytext=(6, 6), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.2", fc="white",
                              ec=colors[s], alpha=.85, lw=.8))

    # ---------- 5. NHAN BIEF — chi khi yeu cau ----------
    if args.nhan_bief:
        for b, ps in by.items():
            ps.sort(key=lambda q: q["ch"])
            mid = ps[len(ps)//2]
            pl = pmap.get(mid["song"])
            if pl:
                r = interp_at(pl, mid["ch"])
                if r:
                    ax.annotate(f"{b}", (r[0], r[1]), fontsize=7,
                                color="#333", zorder=9, ha="center", va="center",
                                bbox=dict(boxstyle="circle,pad=0.12", fc="#ffe",
                                          ec="#999", alpha=.75, lw=.4))

    # ---------- 6. BIEN — sao, nhan ro ----------
    for e, f in free.items():
        b = (e + 1) // 2
        ps = by.get(b)
        if not ps:
            continue
        ps.sort(key=lambda q: q["ch"])
        q = ps[0] if e % 2 == 1 else ps[-1]
        pl = pmap.get(q["song"])
        if not pl:
            continue
        r = interp_at(pl, q["ch"])
        if not r:
            continue
        col = "#d62728" if f["type"] == 1 else "#17becf"
        ax.plot(r[0], r[1], "*", color=col, ms=24, zorder=9, mec="k", mew=.9)
        ax.annotate(f["nom"], (r[0], r[1]), fontsize=9, weight="bold",
                    color=col, zorder=11, xytext=(12, 10),
                    textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.22", fc="w", ec=col, alpha=.92))

    # ---------- legend: do day net = be rong ----------
    h = []
    for w, lbl in ((wmin, f"{wmin:.0f}m (hep nhat)"),
                   (500, "~500m"), (1000, "~1000m"),
                   (wmax, f"{wmax:.0f}m (rong nhat)")):
        if wmin <= w <= wmax:
            h.append(Line2D([0], [0], color="#666", lw=lw_theo_rong(w, wmin, wmax),
                            label=f"be rong {lbl}"))
    h += [
        Line2D([0], [0], color="#555", lw=.5, label="mat cat"),
        Line2D([0], [0], color="#d62728", lw=1.6,
               label=f"mat cat RONG >{args.wide:.0f}m ({n_wide})"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#ff7f0e",
               ms=6, label=f"dau bief tai nut ({len(nodes)} nut)"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#d62728",
               ms=16, label="bien Q"),
        Line2D([0], [0], marker="*", color="w", markerfacecolor="#17becf",
               ms=16, label="bien Z"),
    ]
    ax.legend(handles=h, fontsize=10, loc="lower left", framealpha=.93)

    ax.set_title(f"LUOI TINH TOAN: {len(songs)} nhanh -> {nb} bief, "
                 f"{len(nodes)} nut, {len(free)} bien, {len(profs)} mat cat\n"
                 f"DO DAY NET = BE RONG SONG THAT ({wmin:.0f}..{wmax:.0f}m TB)",
                 fontsize=15)
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_aspect("equal")
    ax.grid(alpha=.2, lw=.4)
    p5 = pdir / "5b_network_clean.png"
    fig.savefig(p5, dpi=170, bbox_inches="tight")
    plt.close(fig)
    print(f"\n   -> {p5}")
    print(f"\nMat cat rong >{args.wide:.0f}m: {n_wide}/{len(profs)}")
    print("Do day net theo be rong TB:")
    for s in sorted(songs, key=lambda k: -w_song[k]):
        print(f"   {s:14s} {w_song[s]:6.0f}m  lw={lw_theo_rong(w_song[s], wmin, wmax):.1f}")


if __name__ == "__main__":
    main()
