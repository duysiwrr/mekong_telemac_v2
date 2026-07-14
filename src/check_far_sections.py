#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_far_sections.py — KIỂM CHỨNG mặt cắt survey map xa với TOÀN BỘ nhánh MIKE

Cho mỗi mặt cắt survey chiếu xa (>ngưỡng) khi chỉ map vào nhánh GIỮ, tìm xem
có nhánh MIKE nào (KỂ CẢ nhánh đã bị loại ở GĐ A) nằm gần nó hơn không.

Kết luận cho từng mặt cắt:
  - "co_nhanh_bi_loai_gan"  -> nhánh cù lao cần GIỮ LẠI (có mặt cắt thật)
  - "chi_co_nhanh_xa"       -> nằm ở kênh không mô hình hóa -> cân nhắc bỏ

DÙNG: ~/TELEMAC_1D_MEKONG/.venv/bin/python src/check_far_sections.py
"""
import re
import sys
import math
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import pandas as pd


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def load_polylines(nwk11):
    text = Path(nwk11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    poly = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        dm = re.search(r"definitions\s*=\s*'([^']*)'", block)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", block)
        if dm and pm:
            ids = [int(p) for p in pm.group(1).split(",") if p.strip()]
            v = [pts[i] for i in ids if i in pts]
            if len(v) >= 2:
                poly[dm.group(1)] = v
    return poly


def nearest_branch(px, py, poly, subset=None):
    best = (None, 0.0, 1e18)
    for name, pl in poly.items():
        if subset is not None and name not in subset:
            continue
        acc = 0.0
        for i in range(len(pl) - 1):
            (x0, y0), (x1, y1) = pl[i], pl[i + 1]
            seg = math.hypot(x1 - x0, y1 - y0)
            if seg == 0:
                continue
            t = ((px - x0) * (x1 - x0) + (py - y0) * (y1 - y0)) / (seg * seg)
            t = max(0.0, min(1.0, t))
            cx, cy = x0 + t * (x1 - x0), y0 + t * (y1 - y0)
            d = math.hypot(px - cx, py - cy)
            if d < best[2]:
                best = (name, acc + t * seg, d)
            acc += seg
    return best


def main():
    THRESHOLD = 500.0
    print("=== KIỂM CHỨNG MẶT CẮT MAP XA ===\n")

    idx = pd.read_csv(CFG.OUT.ROOT / "data_ref/cross_sections/sync_index.csv", sep=";")
    poly = load_polylines(CFG.DATA.NWK11)

    kept = None
    lj = CFG.OUT.LEDGER / "ledger.json"
    if lj.exists():
        kept = set(json.loads(lj.read_text(encoding="utf-8"))["kept"])
    print(f"Tổng nhánh MIKE: {len(poly)} | nhánh GIỮ (ledger): {len(kept) if kept else '?'}\n")

    # mặt cắt thật (co_z) map xa
    far = idx[(pd.to_numeric(idx["dist_proj_m"], errors="coerce") > THRESHOLD)
              & (idx["co_z"] == "yes")]
    print(f"Mặt cắt thật map xa >{THRESHOLD:.0f}m: {len(far)}\n")

    need_keep = set()
    print(f"{'mặt cắt':10s} {'nhánh GIỮ gần':14s} {'d_giữ':>7s}  "
          f"{'nhánh MỌI gần':16s} {'d_mọi':>7s}  kết luận")
    print("-" * 90)
    for _, r in far.iterrows():
        x, y = float(r["x_utm"]), float(r["y_utm"])
        # nhánh gần nhất trong GIỮ
        bk, chk, dk = nearest_branch(x, y, poly, kept)
        # nhánh gần nhất trong TẤT CẢ
        ba, cha, da = nearest_branch(x, y, poly, None)
        if da < 200 and ba not in (kept or set()):
            concl = f"GIỮ LẠI nhánh '{ba}' (cù lao có mặt cắt)"
            need_keep.add(ba)
        elif da < 200:
            concl = "ok (nhánh gần đã giữ)"
        else:
            concl = "kênh không mô hình -> cân nhắc bỏ"
        print(f"{r['shp_name']:10s} {str(bk)[:14]:14s} {dk:7.0f}  "
              f"{str(ba)[:16]:16s} {da:7.0f}  {concl}")

    print("\n=== KẾT LUẬN ===")
    if need_keep:
        print(f"{len(need_keep)} nhánh cù lao cần GIỮ LẠI (có mặt cắt thật, đang bị loại):")
        for b in sorted(need_keep):
            print(f"   + {b}")
        print("\n-> Nên chỉnh GĐ A: thêm luật 'giữ nhánh có mặt cắt survey chiếu <200m'")
    else:
        print("Không nhánh nào cần cứu — 7 mặt cắt nằm ở kênh không mô hình hóa.")


if __name__ == "__main__":
    main()
