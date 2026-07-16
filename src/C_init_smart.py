#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C_init_smart.py — SMART INIT v2 (Z lan truyen theo TOPOLOGY, khong theo so bief)

VI SAO KHONG DUNG CONG THUC V1:
  V1 (24d2) dung `frac = bief / bmax` -> Z dốc theo SO THU TU bief. Chi dung khi
  bief duoc danh so xuoi dong (mang 71 bief cua V1 vo tinh nhu vay).
  v2 danh so theo sorted(mike) = ALPHABET: BASSAC->Bief_1, VamNao->Bief_15.
  Ket qua: Vam Nao (giua mang) bi gan Z thap nhat 3.0m, trong khi Bief_1 (Hau)
  duoc 8.6m -> chenh 5.6m tai nut N1 -> nuoc xa ao -> "Cross Section is dry".

CACH LAM v2 (dung vat ly):
  1. Dung do thi mang tu <listeNoeuds> + <extrLibres> trong mascaret.xcas.
  2. BFS tu cac bief CO BIEN Z (cua bien) — do la muc chuan.
  3. Z(bief) = z_sea + slope * (khoang cach topo toi cua, tinh bang so bief).
     Bief cang xa cua -> Z cang cao. Dung huong dong chay thuc, khong phu thuoc
     thu tu danh so.
  4. San chong kho: Z = max(Z, day_max_cua_bief + h_min).
     Dung day CAO NHAT trong bief (khong phai thap nhat) de moi mat cat deu ngap.
  5. Kiem chenh Z tai moi nut -> in canh bao neu > nguong.

DUNG:
  python3 src/C_init_smart.py --outdir output/grid/backbone
  python3 src/C_init_smart.py --outdir output/grid/backbone --z-sea 0.0 --slope 0.35
"""
import argparse
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG


def read_xcas_topology(outdir):
    """Doc mascaret.xcas -> (nodes, free_ext, typecond, nb_bief).

    nodes: list cac nhom extremite noi nhau tai 1 nut
    free_ext: {ext: type} — type 1=Q, 2=Z
    """
    x = (outdir / "mascaret.xcas").read_text(encoding="latin-1", errors="replace")

    nb = int(re.search(r"<listeBranches>\s*<nb>(\d+)</nb>", x, re.S).group(1))

    # nut: chi lay trong khoi <listeNoeuds>
    m = re.search(r"<listeNoeuds>(.*?)</listeNoeuds>", x, re.S)
    nodes = []
    if m:
        for g in re.findall(r"<num>([\d\s]+)</num>", m.group(1)):
            v = [int(k) for k in g.split() if int(k) > 0]
            if v:
                nodes.append(v)

    # bien tu do
    m = re.search(r"<extrLibres>(.*?)</extrLibres>", x, re.S)
    free = {}
    if m:
        e = re.search(r"<numExtrem>([\d\s]+)</numExtrem>", m.group(1))
        t = re.search(r"<typeCond>([\d\s]+)</typeCond>", m.group(1))
        n = re.findall(r"<string>([^<]*)</string>", m.group(1))
        if e and t:
            exts = [int(v) for v in e.group(1).split()]
            typs = [int(v) for v in t.group(1).split()]
            for i, (ee, tt) in enumerate(zip(exts, typs)):
                free[ee] = {"type": tt, "nom": n[i] if i < len(n) else "?"}
    return nodes, free, nb


def read_geometrie(outdir):
    """Doc geometrie -> profs[list] va bed_stats[bief]."""
    lines = (outdir / "geometrie").read_text(encoding="latin-1",
                                             errors="replace").splitlines()
    profs, cur = [], None
    for l in lines:
        if l.startswith("PROFIL"):
            if cur:
                profs.append(cur)
            p = l.split()
            m = re.search(r"Bief_(\d+)", p[1])
            cur = {"bief": int(m.group(1)) if m else 0, "ten": p[2],
                   "absc": float(p[3]), "zs": []}
        elif cur and l.strip():
            p = l.split()
            if len(p) >= 2:
                try:
                    cur["zs"].append(float(p[1]))
                except ValueError:
                    pass
    if cur:
        profs.append(cur)
    return profs


def bief_graph(nodes, nb):
    """Do thi ke bief-bief qua cac nut. ext -> bief: (ext+1)//2."""
    adj = defaultdict(set)
    for grp in nodes:
        bs = sorted(set((e + 1) // 2 for e in grp))
        for a in bs:
            for b in bs:
                if a != b:
                    adj[a].add(b)
    return adj


def dist_to_sea(adj, sea_biefs, nb):
    """BFS: khoang cach topo (so bief) tu moi bief toi cua gan nhat."""
    dist = {b: None for b in range(1, nb + 1)}
    dq = deque()
    for b in sea_biefs:
        dist[b] = 0
        dq.append(b)
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if dist.get(v) is None:
                dist[v] = dist[u] + 1
                dq.append(v)
    return dist


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--z-sea", type=float, default=1.0,
                    help="Z init tai bief co bien Z (cua bien)")
    ap.add_argument("--slope", type=float, default=0.30,
                    help="Z tang bao nhieu m moi buoc bief roi xa cua")
    ap.add_argument("--h-min", type=float, default=3.0,
                    help="do sau toi thieu tren day CAO NHAT cua bief")
    ap.add_argument("--q-init", type=float, default=10000.0)
    ap.add_argument("--warn-drop", type=float, default=1.0,
                    help="canh bao neu chenh Z tai 1 nut > nguong nay (m)")
    args = ap.parse_args()

    out = Path(args.outdir)
    print("=== SMART INIT v2 (Z theo topology) ===\n")

    nodes, free, nb = read_xcas_topology(out)
    profs = read_geometrie(out)
    print(f"Mang: {nb} bief | {len(nodes)} nut | {len(free)} bien tu do")

    # bief co bien Z = cua bien
    sea = sorted(set((e + 1) // 2 for e, v in free.items() if v["type"] == 2))
    qb = sorted(set((e + 1) // 2 for e, v in free.items() if v["type"] == 1))
    print(f"Bief CUA (bien Z): {sea}")
    print(f"Bief BIEN Q      : {qb}\n")
    if not sea:
        raise SystemExit("[LOI] khong co bien Z nao -> khong xac dinh duoc muc chuan")

    adj = bief_graph(nodes, nb)
    dist = dist_to_sea(adj, sea, nb)
    orphan = [b for b, d in dist.items() if d is None]
    if orphan:
        print(f"[!] {len(orphan)} bief khong noi toi cua: {orphan}")
        for b in orphan:
            dist[b] = max(d for d in dist.values() if d is not None) + 1

    # day cao nhat / thap nhat moi bief
    bed_hi, bed_lo = {}, {}
    for p in profs:
        if not p["zs"]:
            continue
        b, lo = p["bief"], min(p["zs"])
        bed_hi[b] = max(bed_hi.get(b, -1e9), lo)   # day CAO NHAT trong bief
        bed_lo[b] = min(bed_lo.get(b, 1e9), lo)

    # --- Z init theo topology ---
    zb = {}
    for b in range(1, nb + 1):
        z_topo = args.z_sea + args.slope * dist[b]
        z_floor = bed_hi.get(b, 0.0) + args.h_min
        zb[b] = max(z_topo, z_floor)

    print(f"{'bief':>5} {'d_cua':>6} {'day_lo':>8} {'day_hi':>8} "
          f"{'Z_topo':>7} {'Z_san':>7} {'Z_init':>7}  ghi chu")
    print("-" * 72)
    for b in range(1, nb + 1):
        z_topo = args.z_sea + args.slope * dist[b]
        z_floor = bed_hi.get(b, 0.0) + args.h_min
        tag = "CUA" if b in sea else ("BIEN_Q" if b in qb else "")
        note = tag + (" [san]" if z_floor > z_topo else "")
        print(f"{b:5d} {dist[b]:6d} {bed_lo.get(b,0):8.2f} {bed_hi.get(b,0):8.2f} "
              f"{z_topo:7.2f} {z_floor:7.2f} {zb[b]:7.2f}  {note}")

    # --- kiem chenh Z tai moi nut ---
    print(f"\n=== CHENH Z TAI NUT (nguong canh bao {args.warn_drop}m) ===")
    bad = 0
    for i, grp in enumerate(nodes):
        bs = sorted(set((e + 1) // 2 for e in grp))
        vals = {b: zb[b] for b in bs}
        d = max(vals.values()) - min(vals.values())
        flag = ""
        if d > args.warn_drop:
            flag = "  <<< CHENH LON"
            bad += 1
        pretty = ", ".join(f"B{b}={z:.2f}" for b, z in vals.items())
        print(f"  N{i+1}: {pretty}  chenh={d:.2f}m{flag}")
    print(f"\n  {bad}/{len(nodes)} nut chenh > {args.warn_drop}m")
    if bad:
        print("  -> giam --slope hoac tang --z-sea de lam phang hon")

    # --- ghi init.lig (format LIDO, doi chieu file mau da FIN CORRECTE) ---
    all_x, all_z, order, cnt = [], [], [], {}
    for p in profs:
        all_x.append(p["absc"])
        all_z.append(zb[p["bief"]])
        cnt[p["bief"]] = cnt.get(p["bief"], 0) + 1
        if p["bief"] not in order:
            order.append(p["bief"])
    imax = len(all_x)
    ranges, idx = [], 1
    for b in order:
        ranges.append((idx, idx + cnt[b] - 1))
        idx += cnt[b]

    def fmt(vals, per=5):
        return "\n".join("".join(f"{v:13.2f}" for v in vals[i:i + per])
                         for i in range(0, len(vals), per))

    i1i2 = []
    for a, b in ranges:
        i1i2 += [a, b]
    hdr = [" I1,I2 = " + "".join(f"{v:6d}" for v in i1i2[i:i + 10])
           for i in range(0, len(i1i2), 10)]
    lig = ["RESULTATS CALCUL,DATE : 16/07/26 00:00", "FICHIER RESULTAT MASCARET",
           "-" * 71, f" IMAX  = {imax:4d} NBBIEF= {len(order):4d}"]
    lig += hdr
    lig += [" X", fmt(all_x), " Z", fmt(all_z), " Q",
            fmt([args.q_init] * imax), " FIN"]
    (out / "init.lig").write_text("\n".join(lig) + "\n", encoding="ascii")

    print(f"\ninit.lig: {imax} diem, Z {min(all_z):.2f}..{max(all_z):.2f}m, "
          f"Q={args.q_init:.0f}")
    print(f"XONG. Chay: cd {out} && mascaret.py mascaret.xcas")


if __name__ == "__main__":
    main()
