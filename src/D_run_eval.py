#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
D_run_eval.py — CHAY MASCARET (do thoi gian) + DANH GIA NSE/KGE

Hai che do:
  --run       chay mascaret, do thoi gian, roi eval
  (mac dinh)  chi eval tu .opt da co san

MAP TRAM: bang TOA DO (chieu vao polyline nwk11), khong bang ten.
Cong thuc NSE/KGE hoc tu 24e2 cua V1 (da kiem chung), nhung map tram viet lai
cho v2 vi v2 danh so bief theo sorted(mike) = alphabet.

.opt format (Opthyca):
  temps; bief; section; absc; ZREF; Z; QMIN; QMAJ; KMIN; KMAJ; FR; VMIN; Y; Q

RA <outdir>/eval/:
  eval_report.txt     — NSE/KGE tung tram + thoi gian chay
  timeseries.png      — Z(t), Q(t) mo phong vs thuc do, 5 tram
  froude.png          — Froude max doc tung bief (soi cho gan sieu toi han)
  longitudinal_t.png  — trac doc Z tai t=0 / giua / cuoi
  station_map.csv     — tram -> bief/section/khoang cach

DUNG:
  python3 src/D_run_eval.py --outdir output/grid/backbone --run \\
      --start 2011-10-01 --end 2011-10-31 --eval-start 2011-10-08
  python3 src/D_run_eval.py --outdir output/grid/backbone   # chi eval
"""
import argparse
import math
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# tram -> (x_utm, y_utm, nhanh MIKE, cot Q, cot WL, ch_ep)
#
# NGUON TOA DO (da doi chieu 3 nguon, chieu len mang MIKE de kiem chung):
#   1. `6-TVtrieu.xls` (DS tram thuy van vung trieu toan quoc, DDMMSS)
#      -> CHINH THUC, nhung o TAN CHAU SAI: KinhDo=1055100 (105°51') trong khi
#         hang xom Cho Moi=105°24', Long Xuyen=105°27', Vam Nao=105°21'.
#         Tan Chau o thuong nguon phai NHO hon -> ~105°14'. Loi nhap lieu.
#   2. Bang toa do UTM Duy cap -> dung cho TanChau (d=59m), ChauDoc (d=19m)
#   3. Uoc luong V1/AI -> BO HET (khong co co so, MyThuan d=2m chi la trung hop)
#
# KET QUA CHIEU (d = khoang cach toi tim nhanh MIKE):
#   TanChau  d=  59m  Tien@14050    OK
#   ChauDoc  d=  19m  BASSAC@38988  OK
#   VamNao   d= 590m  VamNao@18662  chap nhan (kenh dai 23km)
#   MyThuan  d= 848m  Tien@121672   Excel chinh thuc (cau My Thuan 105°54'E)
#   CanTho   d=1767m  BASSAC@149753 EP vao BASSAC — xem ghi chu duoi
#
# GHI CHU CANTHO: Excel ghi song = "Hau (K. Xang)". Ca 3 toa do deu chieu vao
#   nhanh `Can_Tho` (d=90-161m) chu KHONG phai `BASSAC` (d=1767-5226m).
#   Nhung Q_CanTho = 14400 m3/s -> do la Q SONG HAU, khong the la kenh nho.
#   => Nha tram dat o bo Kenh Xang (P. Cai Khe) nhung TUYEN DO Q vat ngang
#      song Hau. Ta EP map vao BASSAC tai chainage gan tram nhat.
#
# ch_ep: neu != None thi map theo CHAINAGE nay thay vi chieu toa do
#        (dung khi toa do tram khong nam tren nhanh can map)
STATIONS = {
    "TanChau": (526543, 1194295, "Tien",   "Q_TanChau", "H_TanChau", None),
    "ChauDoc": (514545, 1183537, "BASSAC", "Q_ChauDoc", "H_ChauDoc", None),
    "VamNao":  (539045, 1168470, "VamNao", "Q_VamNao",  None,        None),
    "MyThuan": (598558, 1135034, "Tien",   "Q_MyThuan", "H_MyThuan", None),
    "CanTho":  (586757, 1109202, "BASSAC", "Q_CanTho",  "H_CanTho",  149753),
}

# cot trong .opt (0-based)
C_T, C_BIEF, C_SEC, C_ABSC, C_ZREF, C_Z, C_QMIN = 0, 1, 2, 3, 4, 5, 6
C_KMIN, C_KMAJ, C_FR, C_VMIN, C_Y, C_Q = 8, 9, 10, 11, 12, 13


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


# --------------------------------------------------------------- nse / kge
def nse(sim, obs):
    """Hoc tu 24e2 (V1)."""
    if len(obs) < 2:
        return None
    mo = sum(obs) / len(obs)
    den = sum((o - mo) ** 2 for o in obs)
    return 1 - sum((s - o) ** 2 for s, o in zip(sim, obs)) / den if den > 0 else None


def kge(sim, obs):
    """Hoc tu 24e2 (V1). Gupta et al. 2009."""
    if len(obs) < 2:
        return None
    n = len(obs)
    ms, mo = sum(sim) / n, sum(obs) / n
    ss = (sum((s - ms) ** 2 for s in sim) / n) ** 0.5
    so = (sum((o - mo) ** 2 for o in obs) / n) ** 0.5
    if ss == 0 or so == 0 or mo == 0:
        return None
    r = (sum((s - ms) * (o - mo) for s, o in zip(sim, obs)) / n) / (ss * so)
    return 1 - ((r - 1) ** 2 + (ss / so - 1) ** 2 + (ms / mo - 1) ** 2) ** 0.5


# ----------------------------------------------------------------- doc file
def read_bief_map(outdir):
    """bief_map.txt -> {num: {ten, ch0, ch1, absc0, absc1}}"""
    p = outdir / "bief_map.txt"
    out = {}
    if not p.exists():
        return out
    for l in p.read_text(encoding="ascii", errors="replace").splitlines():
        if l.startswith("#") or not l.strip():
            continue
        q = l.split("\t")
        if len(q) >= 4:
            try:
                out[int(q[0])] = {"ten": q[1], "ch0": float(q[2]),
                                  "ch1": float(q[3])}
            except ValueError:
                continue
    return out


def read_polylines(nwk11):
    text = Path(nwk11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)"
                         r"\s*,\s*[\-\d.]+\s*,\s*([\-\d.]+)", text):
        x, y, ch = float(m.group(2)), float(m.group(3)), float(m.group(4))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y, ch)
    poly = defaultdict(list)
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if dm and pm:
            for p in pm.group(1).split(","):
                p = p.strip()
                if p and int(p) in pts:
                    poly[dm.group(1)].append(pts[int(p)])
    for k in poly:
        poly[k].sort(key=lambda t: t[2])
    return dict(poly)


def project(px, py, pl):
    """-> (d_min, chainage)"""
    best, bch = 1e18, 0.0
    for i in range(len(pl) - 1):
        x0, y0, c0 = pl[i]
        x1, y1, c1 = pl[i + 1]
        s = math.hypot(x1 - x0, y1 - y0)
        if s == 0:
            continue
        t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (s * s)
        t = max(0.0, min(1.0, t))
        cx, cy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
        d = math.hypot(px - cx, py - cy)
        if d < best:
            best, bch = d, c0 + t * (c1 - c0)
    return best, bch


def read_opt(path, want=None, verbose=True):
    """Doc .opt -> DataFrame. want = set (bief, section) can lay (giam RAM).

    File 158MB -> doc tung dong, khong dung pandas.read_csv de tranh het RAM.
    """
    rows = []
    n = 0
    with open(path, encoding="latin-1", errors="replace") as f:
        started = False
        for line in f:
            if not started:
                if line.strip().startswith("[resultats]"):
                    started = True
                continue
            q = line.split(";")
            if len(q) < 14:
                continue
            n += 1
            try:
                b = int(q[C_BIEF].strip().strip('"'))
                s = int(q[C_SEC].strip().strip('"'))
            except ValueError:
                continue
            if want is not None and (b, s) not in want:
                continue
            try:
                rows.append((float(q[C_T]), b, s, float(q[C_ABSC]),
                             float(q[C_ZREF]), float(q[C_Z]), float(q[C_QMIN]),
                             float(q[C_FR]), float(q[C_VMIN]), float(q[C_Y]),
                             float(q[C_Q])))
            except ValueError:
                continue
    if verbose:
        print(f"   doc {n} dong, giu {len(rows)}")
    return pd.DataFrame(rows, columns=["t", "bief", "sec", "absc", "zref",
                                       "Z", "QMIN", "FR", "VMIN", "Y", "Q"])


def read_obs(path):
    lines = Path(path).read_text(encoding="utf-8", errors="replace").splitlines()
    cols = re.split(r"\s+", lines[1].strip())[1:]
    data = {c: {} for c in cols}
    for l in lines[3:]:
        if not l.strip():
            continue
        parts = l.split("\t") if "\t" in l else re.split(r"\s{2,}", l.strip())
        if len(parts) < 2:
            continue
        try:
            t = datetime.strptime(parts[0].strip(), "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        vals = re.split(r"\s+", " ".join(parts[1:]).strip())
        for j, c in enumerate(cols):
            if j < len(vals):
                try:
                    data[c][t] = float(vals[j])
                except ValueError:
                    pass
    return cols, data


def find_col(cols, want):
    if want is None:
        return None
    nw = norm(want)
    for c in cols:
        if norm(c) == nw:
            return c
    return None


# --------------------------------------------------------- ban do tram+nut
def plot_station_map(path, outdir, smap, poly, bmap, df0):
    """Ban do: mang + NUT + BIEN + 5 TRAM hieu chinh + section duoc map."""
    from matplotlib.lines import Line2D
    x = (outdir / "mascaret.xcas").read_text(encoding="latin-1", errors="replace")
    # nut
    m = re.search(r"<listeNoeuds>(.*?)</listeNoeuds>", x, re.S)
    nodes = []
    if m:
        for g in re.findall(r"<num>([\d\s]+)</num>", m.group(1)):
            v = [int(k) for k in g.split() if int(k) > 0]
            if v:
                nodes.append(v)
    # bien
    m = re.search(r"<extrLibres>(.*?)</extrLibres>", x, re.S)
    free = {}
    if m:
        e = re.search(r"<numExtrem>([\d\s]+)</numExtrem>", m.group(1))
        c = re.search(r"<typeCond>([\d\s]+)</typeCond>", m.group(1))
        nn = re.findall(r"<string>([^<]*)</string>", m.group(1))
        if e and c:
            for i, (ee, tt) in enumerate(zip([int(v) for v in e.group(1).split()],
                                             [int(v) for v in c.group(1).split()])):
                free[ee] = {"type": tt, "nom": nn[i] if i < len(nn) else "?"}

    def xy_at(ten, ch):
        pl = poly.get(ten)
        if not pl or len(pl) < 2:
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
        return (x0 + t * (x1 - x0), y0 + t * (y1 - y0))

    songs = sorted({v["ten"] for v in bmap.values()})
    cmap = plt.get_cmap("tab20")
    col = {s: cmap(i % 20) for i, s in enumerate(songs)}

    fig, ax = plt.subplots(figsize=(16, 18))
    for s in songs:
        pl = poly.get(s)
        if pl:
            ax.plot([p[0] for p in pl], [p[1] for p in pl], "-",
                    color=col[s], lw=2.2, zorder=2, label=s)
    # nhan bief
    for b, v in bmap.items():
        p = xy_at(v["ten"], 0.5 * (v["ch0"] + v["ch1"]))
        if p:
            ax.annotate(f"B{b}", p, fontsize=9, weight="bold", zorder=8,
                        bbox=dict(boxstyle="round,pad=0.18", fc="yellow",
                                  ec="k", alpha=.85))
    # NUT
    for i, grp in enumerate(nodes):
        pos = []
        for e in grp:
            b = (e + 1) // 2
            if b in bmap:
                p = xy_at(bmap[b]["ten"],
                          bmap[b]["ch0"] if e % 2 == 1 else bmap[b]["ch1"])
                if p:
                    pos.append(p)
        if pos:
            cx = float(np.mean([p[0] for p in pos]))
            cy = float(np.mean([p[1] for p in pos]))
            bs = sorted({(e + 1) // 2 for e in grp})
            ax.plot(cx, cy, "D", color="#ff7f0e", ms=15, zorder=7, mec="k", mew=1.2)
            ax.annotate(f"N{i+1}\n{bs}", (cx, cy), fontsize=8, weight="bold",
                        color="#7f3f00", zorder=9, xytext=(10, -18),
                        textcoords="offset points",
                        bbox=dict(boxstyle="round,pad=0.2", fc="#fff3e0",
                                  ec="#ff7f0e", alpha=.9))
    # BIEN
    for e, f in free.items():
        b = (e + 1) // 2
        if b not in bmap:
            continue
        p = xy_at(bmap[b]["ten"],
                  bmap[b]["ch0"] if e % 2 == 1 else bmap[b]["ch1"])
        if not p:
            continue
        c = "#d62728" if f["type"] == 1 else "#17becf"
        ax.plot(p[0], p[1], "*", color=c, ms=30, zorder=9, mec="k", mew=1.2)
        ax.annotate(f["nom"], p, fontsize=10, weight="bold", color=c, zorder=10,
                    xytext=(12, 12), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.25", fc="w", ec=c, alpha=.92))
    # TRAM HIEU CHINH
    for st, m2 in smap.items():
        sx, sy = STATIONS[st][0], STATIONS[st][1]
        ax.plot(sx, sy, "P", color="#9467bd", ms=17, zorder=10, mec="k", mew=1.2)
        p = xy_at(bmap[m2["bief"]]["ten"], m2["ch"])
        if p:
            ax.plot([sx, p[0]], [sy, p[1]], "--", color="#9467bd", lw=1.5, zorder=8)
            ax.plot(p[0], p[1], "o", color="#9467bd", ms=9, zorder=10,
                    mec="k", mew=1)
        ax.annotate(f"{st}\nB{m2['bief']} s{m2['sec']}\nd={m2['d_xy']:.0f}m",
                    (sx, sy), fontsize=9, weight="bold", color="#4b2882",
                    zorder=11, xytext=(14, -30), textcoords="offset points",
                    bbox=dict(boxstyle="round,pad=0.25", fc="#f3e5f5",
                              ec="#9467bd", alpha=.95))

    h = [Line2D([0], [0], color=col[s], lw=2.5, label=s) for s in songs]
    h += [Line2D([0], [0], marker="D", color="w", markerfacecolor="#ff7f0e",
                 ms=13, label=f"nut giao ({len(nodes)})"),
          Line2D([0], [0], marker="*", color="w", markerfacecolor="#d62728",
                 ms=20, label="bien Q (thuc do)"),
          Line2D([0], [0], marker="*", color="w", markerfacecolor="#17becf",
                 ms=20, label="bien Z (thuc do)"),
          Line2D([0], [0], marker="P", color="w", markerfacecolor="#9467bd",
                 ms=15, label=f"TRAM hieu chinh ({len(smap)})"),
          Line2D([0], [0], marker="o", color="w", markerfacecolor="#9467bd",
                 ms=9, label="section duoc map")]
    ax.legend(handles=h, fontsize=10, loc="lower left", ncol=2)
    ax.set_title("MANG LUOI + NUT + BIEN + TRAM HIEU CHINH\n"
                 f"{len(bmap)} bief, {len(nodes)} nut, {len(free)} bien, "
                 f"{len(smap)} tram", fontsize=14)
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_aspect("equal")
    ax.grid(alpha=.25)
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--run", action="store_true", help="chay mascaret truoc khi eval")
    ap.add_argument("--start", default="2011-10-01")
    ap.add_argument("--end", default="2011-10-31")
    ap.add_argument("--eval-start", default=None,
                    help="bo warm-up: chi eval tu ngay nay (YYYY-MM-DD)")
    ap.add_argument("--q-txt", default=str(CFG.DATA.Q_OBS))
    ap.add_argument("--wl-txt", default=str(CFG.DATA.WL_OBS))
    args = ap.parse_args()

    out = Path(args.outdir)
    ed = out / "eval"
    ed.mkdir(parents=True, exist_ok=True)
    start = datetime.strptime(args.start, "%Y-%m-%d")
    ev0 = datetime.strptime(args.eval_start, "%Y-%m-%d") if args.eval_start else start

    L = []
    def P(s=""):
        print(s)
        L.append(s)

    P("=== CHAY + DANH GIA MASCARET ===\n")

    # ---------- 1. chay (do thoi gian) ----------
    dt_run = None
    if args.run:
        P("Chay mascaret...")
        t0 = time.time()
        r = subprocess.run(["mascaret.py", "mascaret.xcas"], cwd=str(out),
                           capture_output=True, text=True)
        dt_run = time.time() - t0
        ok = "My work is done" in (r.stdout + r.stderr)
        P(f"   THOI GIAN CHAY: {dt_run:.1f}s = {dt_run/60:.2f} phut")
        P(f"   Ket qua: {'OK' if ok else 'LOI'}")
        if not ok:
            P("   --- stderr ---")
            P(r.stderr[-800:])
            raise SystemExit(1)

    optp = out / "ResultatsOpthyca.opt"
    if not optp.exists():
        raise SystemExit(f"[LOI] khong thay {optp}")
    sz = optp.stat().st_size / 1e6
    P(f"\n.opt: {sz:.1f} MB")

    # ---------- 2. map tram bang TOA DO ----------
    P("\nMap tram -> bief/section (bang TOA DO):")
    bmap = read_bief_map(out)
    poly = read_polylines(CFG.DATA.NWK11)
    # doc absc cua moi section tai t=0
    P("   doc .opt (t=0) de lay vi tri section...")
    df0 = read_opt(optp, verbose=False)
    df0 = df0[df0["t"] == df0["t"].min()]

    smap = {}
    for st, (sx, sy, want, qc, wc, ch_ep) in STATIONS.items():
        pl = poly.get(want)
        if not pl:
            P(f"   {st:9s} [!] khong thay nhanh '{want}' trong nwk11")
            continue
        d, ch = project(sx, sy, pl)
        if ch_ep is not None:
            print(f"   {st:9s} [EP] toa do chieu d={d:.0f}m -> dung ch_ep={ch_ep}")
            ch = float(ch_ep)
        # bief nao chua chainage do
        cand = [n for n, v in bmap.items()
                if v["ten"] == want and v["ch0"] - 1 <= ch <= v["ch1"] + 1]
        if not cand:
            cand = [n for n, v in bmap.items() if v["ten"] == want]
        if not cand:
            P(f"   {st:9s} [!] khong co bief nao ten '{want}'")
            continue
        # section gan chainage nhat trong cac bief ung vien
        best = None
        for b in cand:
            sub = df0[df0["bief"] == b]
            if not len(sub):
                continue
            OFF = (b - 1) * 1_000_000
            ch_loc = sub["absc"] - OFF + bmap[b]["ch0"]
            i = (ch_loc - ch).abs().idxmin()
            dd = abs(ch_loc.loc[i] - ch)
            if best is None or dd < best[2]:
                best = (b, int(sub.loc[i, "sec"]), dd)
        if best is None:
            P(f"   {st:9s} [!] khong co section")
            continue
        smap[st] = {"bief": best[0], "sec": best[1], "d_xy": d,
                    "d_ch": best[2], "ch": ch, "q_col": qc, "wl_col": wc}
        P(f"   {st:9s} -> Bief_{best[0]:<2d} sec {best[1]:<4d} "
          f"(ch={ch:7.0f}, lech toa do {d:5.0f}m, lech ch {best[2]:5.0f}m)")

    pd.DataFrame([{"tram": k, **v} for k, v in smap.items()]).to_csv(
        ed / "station_map.csv", sep=";", index=False)

    # ---------- 3. doc .opt tai cac section can ----------
    want = {(v["bief"], v["sec"]) for v in smap.values()}
    P(f"\nDoc .opt tai {len(want)} section...")
    df = read_opt(optp, want=want)

    # ---------- 4. doc thuc do ----------
    qcols, qdata = read_obs(args.q_txt)
    wcols, wdata = read_obs(args.wl_txt)

    # ---------- 5. NSE / KGE ----------
    P(f"\n=== NSE / KGE (eval tu {ev0:%Y-%m-%d}) ===")
    P(f"{'Tram':10s} {'WL_NSE':>9s} {'WL_KGE':>8s} {'Q_NSE':>9s} {'Q_KGE':>8s} {'n':>5s}")
    res = {}
    for st, m in smap.items():
        sub = df[(df["bief"] == m["bief"]) & (df["sec"] == m["sec"])].sort_values("t")
        if not len(sub):
            continue
        tt = [start + timedelta(seconds=float(s)) for s in sub["t"]]
        sim_z = dict(zip(tt, sub["Z"]))
        sim_q = dict(zip(tt, sub["Q"]))
        row = {"tram": st}
        for tag, sim, col, data, cols in (
                ("WL", sim_z, m["wl_col"], wdata, wcols),
                ("Q", sim_q, m["q_col"], qdata, qcols)):
            real = find_col(cols, col)
            if real is None:
                row[f"{tag}_NSE"] = row[f"{tag}_KGE"] = None
                row[f"{tag}_n"] = 0
                continue
            pair = [(sim[t], data[real][t]) for t in sim
                    if t >= ev0 and t in data[real]]
            if len(pair) < 2:
                row[f"{tag}_NSE"] = row[f"{tag}_KGE"] = None
                row[f"{tag}_n"] = len(pair)
                continue
            s_, o_ = [p[0] for p in pair], [p[1] for p in pair]
            row[f"{tag}_NSE"] = nse(s_, o_)
            row[f"{tag}_KGE"] = kge(s_, o_)
            row[f"{tag}_n"] = len(pair)
        res[st] = row
        def f(v):
            return f"{v:9.3f}" if v is not None else "        -"
        P(f"{st:10s} {f(row.get('WL_NSE'))} {f(row.get('WL_KGE'))[1:]} "
          f"{f(row.get('Q_NSE'))} {f(row.get('Q_KGE'))[1:]} "
          f"{max(row.get('WL_n',0), row.get('Q_n',0)):5d}")

    if dt_run:
        P(f"\nTHOI GIAN CHAY: {dt_run:.1f}s = {dt_run/60:.2f} phut "
          f"({(datetime.strptime(args.end,'%Y-%m-%d')-start).days} ngay mo phong)")

    P("\n--- Baseline V1 de so (LUU Y: V1 ha day >10m, SAI VAT LY) ---")
    P("  MyThuan Q_KGE=0.84 | CanTho WL_KGE=0.53 | TanChau Q_KGE=0.53")

    # ---------- 6. hinh ----------
    print("\nVe hinh...")
    n = len(smap)
    fig, axes = plt.subplots(n, 2, figsize=(16, 2.8 * n), squeeze=False)
    for i, (st, m) in enumerate(smap.items()):
        sub = df[(df["bief"] == m["bief"]) & (df["sec"] == m["sec"])].sort_values("t")
        tt = [start + timedelta(seconds=float(s)) for s in sub["t"]]
        for j, (tag, ycol, col, data, cols, unit) in enumerate((
                ("WL", "Z", m["wl_col"], wdata, wcols, "m"),
                ("Q", "Q", m["q_col"], qdata, qcols, "m3/s"))):
            ax = axes[i][j]
            ax.plot(tt, sub[ycol], "-", color="#1f77b4", lw=1.2, label="mo phong")
            real = find_col(cols, col)
            if real:
                ot = sorted(t for t in data[real] if start <= t <= tt[-1])
                ax.plot(ot, [data[real][t] for t in ot], "-", color="#d62728",
                        lw=1.0, alpha=.75, label="thuc do")
            ax.axvline(ev0, color="k", ls="--", lw=.8, alpha=.6)
            r = res.get(st, {})
            k = r.get(f"{tag}_KGE")
            ns = r.get(f"{tag}_NSE")
            ttl = f"{st} — {tag} ({unit})"
            if k is not None:
                ttl += f"   KGE={k:.3f}  NSE={ns:.3f}"
            ax.set_title(ttl, fontsize=9,
                         color="green" if (k or -9) > 0.5 else "black")
            ax.tick_params(labelsize=7)
            ax.grid(alpha=.3)
            if i == 0:
                ax.legend(fontsize=7)
    fig.suptitle("MO PHONG vs THUC DO — duong dut = bat dau eval (bo warm-up)",
                 fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, .98])
    fig.savefig(ed / "timeseries.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {ed}/timeseries.png")

    # ban do tram + nut + bien
    plot_station_map(ed / "station_map.png", out, smap, poly, bmap, df0)

    # trac doc Z theo thoi gian
    print("   doc .opt lay trac doc...")
    dfa = read_opt(optp, verbose=False)
    ts = sorted(dfa["t"].unique())
    pick = [ts[0], ts[len(ts) // 2], ts[-1]]
    nb = sorted(dfa["bief"].unique())
    ncol = 3
    nrow = int(np.ceil(len(nb) / ncol))
    fig, axes = plt.subplots(nrow, ncol, figsize=(6 * ncol, 3.2 * nrow))
    axes = np.atleast_1d(axes).ravel()
    for k, b in enumerate(nb):
        ax = axes[k]
        g0 = dfa[(dfa["bief"] == b) & (dfa["t"] == pick[0])].sort_values("absc")
        xkm = (g0["absc"] - g0["absc"].min()) / 1000
        ax.fill_between(xkm, g0["zref"], g0["zref"].min(), color="#d9c9a3",
                        alpha=.5, zorder=1)
        ax.plot(xkm, g0["zref"], "-", color="#8b5a2b", lw=1.5, zorder=3,
                label="day")
        for t, c, lb in zip(pick, ("#1f77b4", "#2ca02c", "#d62728"),
                            ("t=0", "giua", "cuoi")):
            g = dfa[(dfa["bief"] == b) & (dfa["t"] == t)].sort_values("absc")
            ax.plot((g["absc"] - g["absc"].min()) / 1000, g["Y"] + g["zref"],
                    "-", color=c, lw=1.3, zorder=4,
                    label=f"Z {lb} ({t/86400:.0f}d)")
        ten = bmap.get(b, {}).get("ten", "?")
        frmax = dfa[dfa["bief"] == b]["FR"].max()
        ax.set_title(f"Bief_{b} {ten}  Fr_max={frmax:.2f}", fontsize=9,
                     color="red" if frmax >= 1 else "black")
        ax.set_xlabel("km", fontsize=7)
        ax.set_ylabel("cao do (m)", fontsize=7)
        ax.tick_params(labelsize=7)
        ax.grid(alpha=.25)
        if k == 0:
            ax.legend(fontsize=6)
    for k in range(len(nb), len(axes)):
        axes[k].axis("off")
    fig.suptitle("TRAC DOC Z THEO THOI GIAN (t=0 / giua / cuoi)", fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, .97])
    fig.savefig(ed / "longitudinal_t.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {ed}/longitudinal_t.png")

    # Froude (dung lai dfa da doc o tren)
    fr = dfa.groupby(["bief", "sec"])["FR"].max().reset_index()
    fig, ax = plt.subplots(figsize=(14, 6))
    for b, g in fr.groupby("bief"):
        ax.plot(g["sec"], g["FR"], "-o", ms=3, lw=1, label=f"B{b}")
    ax.axhline(1.0, color="r", ls="--", lw=1.5, label="Fr=1 (sieu toi han)")
    ax.set_xlabel("section")
    ax.set_ylabel("Froude max")
    ax.set_title(f"FROUDE MAX moi section (max toan mang = {fr['FR'].max():.3f})")
    ax.legend(fontsize=7, ncol=4)
    ax.grid(alpha=.3)
    fig.savefig(ed / "froude.png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {ed}/froude.png")
    P(f"\nFroude max toan mang: {fr['FR'].max():.3f} "
      f"({'OK' if fr['FR'].max() < 1 else 'CANH BAO: sieu toi han'})")

    (ed / "eval_report.txt").write_text("\n".join(L), encoding="utf-8")
    print(f"   -> {ed}/eval_report.txt")
    print(f"\nXONG -> {ed}/")


if __name__ == "__main__":
    main()
