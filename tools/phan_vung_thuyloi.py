#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
phan_vung_thuyloi.py — PHAN 15 HE THONG THUY LOI bang BFS tu KENH ME

CO SO (tai lieu Vien KHTL mien Nam 2022 + web):
  - Kenh Vinh Te = "kenh me" -> T3/T4/T5 -> TGLX -> bien Tay (Rach Gia-Ha Tien)
  - Nguyen Van Tiep/Hong Ngu: Tien(Cao Lanh/Hong Ngu) -> Vam Co Tay -> DTM
  - Quan Lo-Phung Hiep: Hau(Cai Con/Xang) -> BDCM
  - Cai Lon-Cai Be, O Mon-Xa No: Hau -> bien Tay
  - MIKE11 cung vung: bien Q Long Xuyen + Z tai My Thanh/Ganh Hao/Rach Gia

PHUONG PHAP:
  1. Kenh TRUC (da chay thong: Tien/Hau/VamNao/CoChien/HamLuong + cua) = vung 0
  2. Moi vung co KENH ME (hat giong) — tra tu ten trong ledger
  3. BFS dong thoi tu MOI hat giong qua nodes.csv:
     kenh noi dong thuoc vung cua hat giong DEN duoc no TRUOC (BFS ngan nhat)
  4. Kenh TRUC khong bi chiem (gan cung vung 0)

RA: output/vung_thuyloi/
  - phan_vung.csv    (nhanh;vung;cap_bfs)
  - vve 8 vung PNG

DUNG: python3 tools/phan_vung_thuyloi.py
"""
import csv
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------- KENH ME moi vung (tu khoa, tra trong ledger) -------
HAT_GIONG = {
    "1_TGLX": ["vinh te", "kenh t3", "kenh t4", "kenh t5", "kenh t6",
               "tri ton", "ba the", "rach gia", "tam ngan", "tha la",
               "tra su", "giang thanh", "nang gu"],
    "2_DTM": ["nguyen van tiep", "van tiep", "hong ngu", "dong tien",
              "duong van duong", "phuoc xuyen", "k28", "kenh 28",
              "tan thanh", "lo gach", "la285", "la286", "la287", "la288",
              "la289", "la479", "la508", "la509", "la578", "la579", "la580",
              "thu thua", "bao dinh"],
    "3_CuLaoTien": ["nhat tao", "vam co", "go cong", "ba lai",
                    "bao dinh", "go cong"],
    "4_NamMangThit": ["mang thit", "nicolai", "travinh", "tv_", "cai von",
                      "vunglien", "mcc01", "c14", "c15", "c16", "c17", "c18",
                      "c19", "c20", "c21", "c22", "c23", "c24", "c25"],
    "5_OMonXaNo": ["o mon", "omon", "xa no", "xano", "xeo mon"],
    "6_QLPH_LongPhu": ["quan lo", "qlph", "u-qlph", "u_qlph", "cai con",
                       "phung hiep", "long phu", "tiep nhat", "saintenoy",
                       "st29", "st56", "moiqlph"],
    "7_CaiLon_BCM": ["cai lon", "cai be", "cailon", "cai beo",
                     "tac van", "ong doc", "tac thu", "ganh hao", "cai tau",
                     "cm03", "cm11", "cm16", "cm18", "cm20", "cm42", "cm59",
                     "cm60", "cm61", "cm64", "cm65", "cm67", "cm68", "cm71",
                     "cm73", "cm74", "cm75", "cm76", "cm77", "cm78", "cm80",
                     "cm81", "cm82", "cm84", "cm85", "cm87", "cm88", "cm89",
                     "cm90", "cm91", "cm93", "cm95", "cm97", "cm98", "cm99",
                     "cm101", "cm102", "cm103", "umh", "chemz", "branch",
                     "go04", "go12", "go13", "go14", "go27", "go29", "go69",
                     "go73", "go162", "go163", "go168", "go170", "ntl",
                     "u-ql", "vp", "s. cua lon", "cua lon", "bo de", "bay hap",
                     "dam doi", "nam can", "rach goc"],
}

TRUC = {"Tien", "BASSAC", "VamNao", "CoChien", "Ham Luong", "Ham_Luong",
        "CuaTieu", "CuaDai", "CuaCoChien", "CuaCungHau", "CuaDinhAn",
        "CuaTranDe"}


def norm(s):
    return s.lower()


def main():
    # 1. mang lien ket
    noi = defaultdict(set)
    for row in csv.reader(open("output/ledger/nodes.csv", encoding="utf-8"),
                          delimiter=";"):
        if len(row) < 4:
            continue
        for it in row[3].split("|"):
            p = it.split(":")
            if p[0]:
                noi[row[1]].add(p[0])
                noi[p[0]].add(row[1])

    giu = {}
    poly_need = set()
    for r in csv.DictReader(open("output/ledger/branches.csv", encoding="utf-8"),
                            delimiter=";"):
        if r["giu"] == "GIU":
            giu[r["ten_mike"]] = float(r["width_m"] or 0)

    # 2. gan hat giong
    vung = {}          # nhanh -> vung
    cap = {}           # nhanh -> khoang cach BFS
    # TRUC truoc (cung)
    for n in giu:
        # TRUC + moi nhanh ten Tien_*/Hau_*/CoChien_*/HamLuong_* -> vung 0
        base = re.sub(r"_?\d+$", "", n)
        if n in TRUC or base in TRUC or n.startswith(("Tien_", "Hau_",
                "CoChien", "HamLuong", "CuaDai", "CuaTieu")):
            vung[n] = "0_TRUC"
            cap[n] = 0

    # hat giong cac vung -> BFS dong thoi
    dq = deque()
    for vg, kws in HAT_GIONG.items():
        for n in giu:
            if n in vung:
                continue
            if any(k in norm(n) for k in kws):
                vung[n] = vg
                cap[n] = 0
                dq.append(n)

    # 3. BFS lan
    while dq:
        u = dq.popleft()
        for v in noi[u]:
            if v in giu and v not in vung:
                vung[v] = vung[u]
                cap[v] = cap[u] + 1
                dq.append(v)

    # nhanh chua gan (co lap khoi hat giong) -> "9_KHAC"
    for n in giu:
        vung.setdefault(n, "9_KHAC")
        cap.setdefault(n, -1)

    # thong ke
    from collections import Counter
    print("=== PHAN VUNG (BFS tu kenh me) ===\n")
    c = Counter(vung.values())
    for vg in sorted(c):
        print(f"  {vg:16s} {c[vg]:4d} nhanh")

    # ghi csv
    out = Path("output/vung_thuyloi")
    out.mkdir(exist_ok=True)
    with open(out / "phan_vung.csv", "w", encoding="utf-8") as f:
        f.write("nhanh;vung;cap_bfs\n")
        for n in sorted(giu):
            f.write(f"{n};{vung[n]};{cap[n]}\n")
    print(f"\n-> {out}/phan_vung.csv")

    # 4. ve — doc polyline
    text = Path(CFG.DATA.NWK11).read_text(encoding="utf-8", errors="replace")
    pts = {}
    for m in re.finditer(r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)", text):
        x, y = float(m.group(2)), float(m.group(3))
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            pts[int(m.group(1))] = (x, y)
    # luu TUNG DOAN rieng (nhanh cung ten co the co nhieu doan ROI NHAU,
    # cach nhau 10km — noi lai se ve duong thang xuyen qua. Ba Ke 18 doan.)
    poly = defaultdict(list)   # ten -> list cac doan (moi doan 1 polyline)
    for blk in re.split(r"\[branch\]", text)[1:]:
        e = blk.find("EndSect  // branch")
        bt = blk[:e] if e > 0 else blk
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if dm and pm:
            v = [pts[int(p)] for p in pm.group(1).split(",")
                 if p.strip() and int(p) in pts]
            if v:
                poly[dm.group(1)].append(v)

    vgs = sorted(set(vung.values()))
    cmap = plt.get_cmap("tab10")
    col = {vg: cmap(i % 10) for i, vg in enumerate(vgs)}

    # ban do TONG — moi vung 1 mau
    fig, ax = plt.subplots(figsize=(20, 20))
    for n, w in giu.items():
        segs = poly.get(n)
        if not segs:
            continue
        lw = 0.4 + min(w, 2000) / 2000 * 3.5
        for v in segs:   # ve TUNG DOAN rieng, khong noi
            ax.plot([p[0] for p in v], [p[1] for p in v], "-",
                    color=col[vung[n]], lw=lw, alpha=.75,
                    solid_capstyle="round")
    from matplotlib.lines import Line2D
    h = [Line2D([0], [0], color=col[vg], lw=3, label=f"{vg} ({c[vg]})")
         for vg in vgs]
    ax.legend(handles=h, fontsize=13, loc="best")
    ax.set_title(f"PHAN VUNG THUY LOI — {len(vgs)} vung "
                 f"(BFS tu kenh me trong mang that)", fontsize=16)
    ax.set_xlabel("UTM X (m)")
    ax.set_ylabel("UTM Y (m)")
    ax.set_aspect("equal")
    ax.grid(alpha=.2)
    p = out / "tong_the.png"
    fig.savefig(p, dpi=130, bbox_inches="tight")
    plt.close(fig)
    print(f"-> {p}")


if __name__ == "__main__":
    main()
