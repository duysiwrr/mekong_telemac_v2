#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_gaps.py — KIỂM NHÁNH MẢNH CÓ HỞ CHAINAGE

Từ audit: 162 nhánh chia mảnh, 131 nối liền qua nút giao (OK), 31 có hở >200m.
Kiểm 31 cái này: hở là do ĐỨT THẬT hay do đoạn giữa BỊ LOẠI (linkchannel/no-xns)?

Với mỗi nhánh hở:
  - liệt kê tất cả đoạn (chainage, có mặt cắt?, linkchannel?, giữ/bỏ)
  - nếu đoạn giữa bị loại -> hở là "giả" (do lọc), nhánh vẫn liền trong MIKE
  - nếu thật sự thiếu đoạn -> đứt thật

DÙNG: ~/TELEMAC_1D_MEKONG/.venv/bin/python src/check_gaps.py
"""
import sys
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from config.config import CFG

import mikeio1d


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


def main():
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")

    # mặt cắt MIKE
    xns = mikeio1d.open(str(CFG.DATA.XNS11))
    dfx = xns.to_dataframe().reset_index()
    has_xns = set(norm(r["location_id"]) for _, r in dfx.iterrows())

    # gom đoạn theo tên nhánh
    segs_by_name = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        end = block.find("EndSect  // branch")
        bt = block[:end] if end != -1 else block
        dm = re.search(
            r"definitions\s*=\s*'([^']*)'\s*,\s*'[^']*'\s*,\s*([\-\d.e]+)\s*,\s*([\-\d.e]+)", bt)
        if not dm:
            continue
        name = dm.group(1)
        is_link = ("[linkchannel]" in bt) or ("[storagearea]" in bt)
        try:
            cs, ce = float(dm.group(2)), float(dm.group(3))
        except ValueError:
            continue
        segs_by_name.setdefault(name, []).append(
            {"cs": cs, "ce": ce, "link": is_link})

    frag = {n: s for n, s in segs_by_name.items() if len(s) > 1}

    # tìm nhánh có hở >200m
    print("=== KIỂM 31 NHÁNH MẢNH CÓ HỞ CHAINAGE ===\n")
    gap_branches = []
    for nm, segs in frag.items():
        segs.sort(key=lambda s: s["cs"])
        has_gap = any(abs(segs[i]["ce"] - segs[i+1]["cs"]) > 200
                      for i in range(len(segs)-1))
        if has_gap:
            gap_branches.append((nm, segs))

    print(f"Số nhánh có hở >200m: {len(gap_branches)}\n")

    dut_that = 0
    ho_gia = 0     # hở do đoạn giữa bị loại (linkchannel/no-xns)
    for nm, segs in gap_branches:
        # nhánh này có mặt cắt tổng thể không?
        has_c = norm(nm) in has_xns
        any_link = any(s["link"] for s in segs)
        print(f"● {nm}  ({len(segs)} đoạn, mặt cắt={'có' if has_c else 'KHÔNG'}, "
              f"linkchannel={'CÓ' if any_link else 'không'})")
        for s in segs:
            print(f"    ch[{s['cs']:.0f} -> {s['ce']:.0f}]"
                  f"{'  [LINK]' if s['link'] else ''}")
        # phán đoán
        if any_link:
            print("    => hở do đoạn LINKCHANNEL (ô trữ) xen giữa -> loại link là ĐÚNG, "
                  "phần kênh thật vẫn liền qua nút giao")
            ho_gia += 1
        elif not has_c:
            print("    => nhánh KHÔNG mặt cắt -> sẽ bị loại toàn bộ, không ảnh hưởng")
            ho_gia += 1
        else:
            print("    => NGHI đứt thật (có mặt cắt, không link) -> cần xem kỹ")
            dut_that += 1
        print()

    print("=== TỔNG KẾT ===")
    print(f"  Hở 'giả' (do linkchannel/no-xns xen giữa): {ho_gia}")
    print(f"  Nghi ĐỨT THẬT (có mặt cắt, không link): {dut_that}")
    if dut_that == 0:
        print("  => TẤT CẢ hở đều do lọc ô trữ/không mặt cắt. "
              "Mạng kênh thật KHÔNG đứt. An toàn.")
    else:
        print("  => Có nhánh nghi đứt thật — xem danh sách trên để xử lý riêng.")


if __name__ == "__main__":
    main()
