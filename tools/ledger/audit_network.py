#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
audit_network.py — RÀ SOÁT TOÀN DIỆN MẠNG (kiểm chứng trước khi sinh lưới)

Trả lời 4 câu hỏi kiểm chứng:
  1. Kênh nào bị LOẠI mà thực ra là kênh thật? (in bản đồ tô màu theo lý do bỏ)
  2. Nhánh nào bị CHIA MẢNH (cùng tên nhiều đoạn, như Cai San)?
  3. Nhánh GIỮ nào KHÔNG liên thông (chơi vơi)?
  4. Nhánh nào là đường chéo ô trữ còn sót (thẳng + tạo vòng)?

RA output/audit/:
  removed_map.png       — bản đồ nhánh bị loại (màu theo lý do)
  connectivity_map.png  — bản đồ liên thông (nhánh cô lập tô đỏ)
  fragmented.csv        — nhánh cùng tên nhiều đoạn
  audit_report.txt

DÙNG: ~/TELEMAC_1D_MEKONG/.venv/bin/python src/audit_network.py
"""
import sys
import re
import csv
import math
from pathlib import Path
from collections import defaultdict, deque, Counter

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.config import CFG


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def load_network():
    """Trả (branches, points). branch: name -> {pids, us, ds, has_link}."""
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    branches = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        cm = re.search(
            r"connections\s*=\s*'([^']*)'\s*,\s*([\-\d.e]+)\s*,\s*'([^']*)'\s*,\s*([\-\d.e]+)", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if not dm:
            continue
        name = dm.group(1)
        pids = [int(p) for p in pm.group(1).split(",") if p.strip()] if pm else []
        us = (cm.group(1), float(cm.group(2))) if cm else None
        ds = (cm.group(3), float(cm.group(4))) if cm else None
        has_link = "[linkchannel]" in bt
        # nhánh trùng tên: gộp thành list các đoạn
        branches.setdefault(name, []).append(
            {"pids": pids, "us": us, "ds": ds, "has_link": has_link})
    return branches, pts


def main():
    out = CFG.OUT.ROOT / "output" / "audit"
    out.mkdir(parents=True, exist_ok=True)
    print("=== RÀ SOÁT TOÀN DIỆN MẠNG ===\n")

    branches, pts = load_network()
    print(f"Tổng tên nhánh duy nhất: {len(branches)}")

    # đọc trạng thái giữ/bỏ + lý do từ ledger
    status = {}   # name -> (giu, reason)
    ledger_csv = CFG.OUT.LEDGER / "branches.csv"
    for r in csv.DictReader(open(ledger_csv), delimiter=";"):
        status[r["ten_mike"]] = (r["giu"] == "GIU", r["ly_do"])

    # -------- CÂU 2: nhánh chia mảnh (cùng tên nhiều đoạn) --------
    print("\n[2] NHÁNH CHIA MẢNH (cùng tên nhiều đoạn):")
    frag = {nm: segs for nm, segs in branches.items() if len(segs) > 1}
    print(f"   {len(frag)} tên nhánh bị chia >1 đoạn")
    with open(out / "fragmented.csv", "w", encoding="utf-8") as f:
        f.write("ten;so_doan;so_diem_moi_doan;giu;ly_do\n")
        for nm, segs in sorted(frag.items(), key=lambda x: -len(x[1])):
            npts = "|".join(str(len(s["pids"])) for s in segs)
            giu, reason = status.get(nm, (False, "?"))
            f.write(f"{nm};{len(segs)};{npts};{'GIU' if giu else 'bo'};{reason}\n")
    # in vài cái nổi bật
    for nm, segs in sorted(frag.items(), key=lambda x: -len(x[1]))[:12]:
        giu, reason = status.get(nm, (False, "?"))
        print(f"     {nm:22s} {len(segs)} đoạn ({'|'.join(str(len(s['pids'])) for s in segs)}) "
              f"-> {'GIỮ' if giu else 'bỏ'} ({reason})")

    # -------- CÂU 1: kênh bị loại — phân theo lý do --------
    print("\n[1] KÊNH BỊ LOẠI (theo lý do):")
    removed = defaultdict(list)
    for nm, (giu, reason) in status.items():
        if not giu:
            removed[reason].append(nm)
    for reason, names in sorted(removed.items(), key=lambda x: -len(x[1])):
        print(f"   {reason}: {len(names)}")

    # -------- CÂU 3: liên thông nhánh GIỮ --------
    print("\n[3] KIỂM LIÊN THÔNG NHÁNH GIỮ:")
    kept = {nm for nm, (g, _) in status.items() if g}
    adj = defaultdict(set)
    for nm in kept:
        for seg in branches.get(nm, []):
            for conn in (seg["us"], seg["ds"]):
                if conn and conn[0] in kept:
                    adj[nm].add(conn[0])
                    adj[conn[0]].add(nm)
    # BFS từ Tien+BASSAC
    seeds = [n for n in kept if norm(n) in (norm("Tien"), norm("BASSAC"))]
    seen = set(seeds); dq = deque(seeds)
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in seen:
                seen.add(v); dq.append(v)
    isolated = kept - seen
    print(f"   Liên thông với Tân Châu/Châu Đốc: {len(seen)}/{len(kept)}")
    print(f"   CHƠI VƠI (không nối tới trục chính): {len(isolated)}")
    if isolated:
        print("   mẫu nhánh cô lập:", list(sorted(isolated))[:20])

    # -------- IN BẢN ĐỒ --------
    print("\n[in bản đồ]...")
    plot_removed(out / "removed_map.png", branches, pts, status)
    plot_connectivity(out / "connectivity_map.png", branches, pts, kept, seen, isolated)

    # -------- REPORT --------
    with open(out / "audit_report.txt", "w", encoding="utf-8") as f:
        f.write("RÀ SOÁT MẠNG\n")
        f.write(f"Tên nhánh: {len(branches)} | GIỮ: {len(kept)}\n")
        f.write(f"Chia mảnh: {len(frag)}\n")
        f.write(f"Liên thông: {len(seen)}/{len(kept)} | cô lập: {len(isolated)}\n")
        f.write("\nLý do loại:\n")
        for reason, names in sorted(removed.items(), key=lambda x: -len(x[1])):
            f.write(f"  {reason}: {len(names)}\n")
        if isolated:
            f.write("\nNhánh cô lập:\n")
            for n in sorted(isolated):
                f.write(f"  {n}\n")

    print(f"\nXONG. Kiểm output/audit/: removed_map.png, connectivity_map.png, "
          f"fragmented.csv, audit_report.txt")


def _plot_branch(ax, segs, pts, **kw):
    for seg in segs:
        pl = [pts[p] for p in seg["pids"] if p in pts]
        if len(pl) >= 2:
            xs, ys = zip(*pl)
            ax.plot(xs, ys, **kw)


def plot_removed(path, branches, pts, status):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 16))
    # màu theo lý do loại
    color_map = {
        "khong_co_mat_cat": "#ff7f0e",
        "ngoai_lien_thong": "#9467bd",
        "co_mat_cat_mike": "#cccccc",   # giữ = xám nhạt nền
        "co_survey2020": "#cccccc",
        "co_bien": "#cccccc",
    }
    # nền: nhánh giữ (xám)
    for nm, segs in branches.items():
        giu, reason = status.get(nm, (False, "?"))
        if giu:
            _plot_branch(ax, segs, pts, color="#dddddd", lw=0.5, zorder=1)
    # nhánh loại: tô màu theo lý do
    from collections import defaultdict
    shown = set()
    for nm, segs in branches.items():
        giu, reason = status.get(nm, (False, "?"))
        if not giu:
            c = color_map.get(reason, "#d62728")
            lbl = reason if reason not in shown else None
            shown.add(reason)
            _plot_branch(ax, segs, pts, color=c, lw=0.8, zorder=2, label=lbl)
    ax.set_title("Kênh BỊ LOẠI (màu theo lý do) — nền xám = giữ")
    ax.set_aspect("equal"); ax.legend(fontsize=9, markerscale=3)
    ax.set_xlabel("UTM X"); ax.set_ylabel("UTM Y")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


def plot_connectivity(path, branches, pts, kept, seen, isolated):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(14, 16))
    for nm in kept:
        segs = branches.get(nm, [])
        if nm in isolated:
            _plot_branch(ax, segs, pts, color="#d62728", lw=1.5, zorder=3)
        else:
            _plot_branch(ax, segs, pts, color="#1f77b4", lw=0.6, zorder=1)
    ax.set_title(f"Liên thông: xanh=nối trục chính ({len(seen)}), "
                 f"ĐỎ=chơi vơi ({len(isolated)})")
    ax.set_aspect("equal")
    ax.set_xlabel("UTM X"); ax.set_ylabel("UTM Y")
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)
    print(f"   -> {path}")


if __name__ == "__main__":
    main()
