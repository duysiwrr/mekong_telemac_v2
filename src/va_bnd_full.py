#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
va_bnd_full.py — GAN BIEN TU bnd_map.csv (mo khoa toan DBSCL)

VI SAO:
  `--subset full` sinh 4584 bief / 126 BIEN TU DO.
  `MAP_SONG` go tay chi biet 10 -> 116 bien con lai KHONG gan duoc.
  NHUNG Boundary_2011.bnd11 co 1709 BndItem — MIKE DA GAN SAN:
     99/126 bien cua `full3` tra duoc cot OBS tu bnd_map.csv
  => Doc bnd_map.csv thay vi go tay -> gan duoc 99 bien.

VIEC 1 — loc them 12 nhanh Sai Gon (hinh 5b cho thay chung chay len Y=1.30M,
  ngoai DBSCL): East Vaico, R. BEN NGHE*, RachTra_*, R.NhanhCanGiuoc*,
  S.NhanhCanGiuoc1, S.BenCat, KENHTHAYCAI*, RACHTRAQUAN, ThayCaiRachTra
  LUU Y: KHONG loc Vam Co/Vam Co Dong/Vam Co Tay — da thu 17/07 -> bien
  124 -> 155 vi 30+ kenh DTM (Thu_Thua, kenhLA285..508, T3..T8) thanh cut.

VIEC 2 — C_assign_boundaries doc bnd_map.csv:
  1. TanChau/ChauDoc -> MAP_SONG (bien Q ta tu gan tai diem cat thuong luu;
     MIKE lay bien tu Kratie nen KHONG co entry trong bnd11 — DUNG thiet ke)
  2. Nhanh khac  -> tra bnd_map.csv theo ten -> cot OBS -> gan thuc do
  3. Khong tra duoc -> Q=0 (kenh cut / cong trinh: *_cau, Dap_Tha_La...)
     MIKE cung coi chung la tuong kin.

Co .bak + assert. Chay tu goc repo.
"""
import shutil
import sys
from pathlib import Path

# ============================================================ 1. config.py
P1 = Path("config/config.py")
t1 = P1.read_text(encoding="utf-8")
OLD1 = '''        # --- Sài Gòn – Đồng Nai (ngoài ĐBSCL) ---
        "Dong Nai", "Sai Gon", "Vinh Cuu", "K. LONG TAU", "R.PHUOC KIENG",
        "Can Giuoc", "Song Kinh",'''
NEW1 = '''        # --- Sài Gòn – Đồng Nai (ngoài ĐBSCL) ---
        # 17/07: hình 5b_network_clean cho thấy East Vaico chạy lên Y=1.30M
        # (bắc Tây Ninh) — ngoài ĐBSCL. Rà thêm 12 nhánh Sài Gòn.
        "Dong Nai", "Sai Gon", "Vinh Cuu", "K. LONG TAU", "R.PHUOC KIENG",
        "Can Giuoc", "Song Kinh",
        "East Vaico", "R. BEN NGHE", "R. BEN NGHE1", "S.BenCat",
        "R.NhanhCanGiuoc2", "R.NhanhCanGiuoc5", "R.NhanhCanGiuoc5_1",
        "R.NhanhCanGiuoc5_2", "R.NhanhCanGiuoc5_3", "S.NhanhCanGiuoc1",
        "RachTra_1", "RachTra_2", "RACHTRAQUAN", "ThayCaiRachTra",
        "KENHTHAYCAI", "KENHTHAYCAI1",'''
assert t1.count(OLD1) == 1, f"config CHO 1: {t1.count(OLD1)} lan"
shutil.copy2(P1, P1.with_suffix(".py.bak"))
P1.write_text(t1.replace(OLD1, NEW1), encoding="utf-8")
print(f"1. {P1}: them 14 nhanh Sai Gon vao DROP_UPSTREAM")

# ================================================= 2. C_assign_boundaries.py
P2 = Path("src/C_assign_boundaries.py")
t2 = P2.read_text(encoding="utf-8")
goc2 = t2

OLD2 = '''def doc_bien_tu_xcas(outdir):'''
NEW2 = '''def doc_bnd_map():
    """data_ref/catalog/bnd_map.csv -> {vn_norm(nhanh): (cot_obs, nguon)}.

    Sinh boi G_doc_bnd11.py tu Boundary_2011.bnd11 (1709 BndItem).
    MIKE da gan san bien cho moi nhanh cut:
      Ba Hon -> 'Rach Gia' -> H_RachGia | Bay Hap -> 'Song Doc' -> H_SongDoc
      Branch1016 -> 'Ganh hao' -> H_GanhHao | Cai Lon -> 'Xeo ro' -> H_XeoRo
    Chi lay type=0 (bien mo). type=1 la nhu cau nuoc (Waterdemand2.dfs0),
    khong phai bien thuy van.
    """
    p = CFG.OUT.ROOT / "data_ref" / "catalog" / "bnd_map.csv"
    if not p.exists():
        print(f"  [!] chua co {p} — chay: python3 src/G_doc_bnd11.py")
        return {}
    out = {}
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r.get("type") != "0" or r.get("co_so_lieu") != "yes":
                continue
            out[vn_norm(r["nhanh"])] = (r["cot_obs"], r["nguon"])
    return out


def vn_norm(s):
    """Bo dau tieng Viet + ky tu dac biet. 'Ham Luong' -> 'HAMLUONG'."""
    s = str(s).replace("\\u0110", "D").replace("\\u0111", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def doc_bien_tu_xcas(outdir):'''
assert t2.count(OLD2) == 1, f"C_assign CHO 2: {t2.count(OLD2)} lan"
t2 = t2.replace(OLD2, NEW2)

# import csv + unicodedata
OLD3 = '''import argparse
import re
import sys
from datetime import datetime
from pathlib import Path'''
NEW3 = '''import argparse
import csv
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path'''
assert t2.count(OLD3) == 1, f"C_assign CHO 3: {t2.count(OLD3)} lan"
t2 = t2.replace(OLD3, NEW3)

# tra MAP_SONG -> neu khong co thi tra bnd_map
OLD4 = '''    noms = re.findall(r"<string>([^<]*)</string>", m.group(1))
    out, thieu = [], []
    for nom in noms:
        # boc tien to Z_/Q_ va hau to _<so>
        s = re.sub(r"^[ZQ]_", "", nom)
        s = re.sub(r"_\\d+$", "", s)
        if s in MAP_SONG:
            src, col, typ = MAP_SONG[s]
            out.append((nom, src, col, typ))
        else:
            thieu.append(f"{nom} (-> '{s}')")
    if thieu:
        print(f"  [LOI] {len(thieu)} bien khong tra duoc trong MAP_SONG:")
        for t in thieu:
            print(f"        {t}")
        print(f"        MAP_SONG co: {sorted(MAP_SONG)}")
        raise SystemExit(1)
    return out'''
NEW4 = '''    noms = re.findall(r"<string>([^<]*)</string>", m.group(1))
    bnd = doc_bnd_map()
    out, n_tay, n_bnd, q0 = [], 0, 0, []
    for nom in noms:
        # boc tien to Z_/Q_ va hau to _<so>
        s = re.sub(r"^[ZQ]_", "", nom)
        s = re.sub(r"_\\d+$", "", s)
        if s in MAP_SONG:                       # 1. bang go tay (bien Q + 6 cua)
            src, col, typ = MAP_SONG[s]
            out.append((nom, src, col, typ))
            n_tay += 1
        elif vn_norm(s) in bnd:                 # 2. bnd_map.csv (MIKE gan san)
            col, src = bnd[vn_norm(s)]
            out.append((nom, src, col, 2 if src == "H" else 1))
            n_bnd += 1
        else:                                   # 3. kenh cut / cong trinh -> Q=0
            out.append((nom, "Q0", None, 1))
            q0.append(s)
    print(f"  {n_tay} bien tu MAP_SONG (go tay) | {n_bnd} tu bnd_map.csv "
          f"| {len(q0)} gan Q=0")
    if q0:
        print(f"  Q=0 (kenh cut/cong trinh — MIKE cung coi la tuong kin):")
        print(f"     {sorted(set(q0))[:20]}")
    return out'''
assert t2.count(OLD4) == 1, f"C_assign CHO 4: {t2.count(OLD4)} lan"
t2 = t2.replace(OLD4, NEW4)

# xu ly Q0 khi ghi .loi
OLD5 = '''    print(f"\\nGan {len(BND)} bien:")
    for name, src, srccol, typ in BND:
        cols, data = (qcols, qdata) if src == "Q" else (wcols, wdata)'''
NEW5 = '''    print(f"\\nGan {len(BND)} bien:")
    for name, src, srccol, typ in BND:
        if src == "Q0":            # kenh cut -> Q=0 hang so
            ser = [(0.0, 0.0), (dur, 0.0)]
            write_loi(out / f"{name}.loi", f"{name} (kenh cut - Q=0)",
                      "Temps(S) Debit", ser)
            continue
        cols, data = (qcols, qdata) if src == "Q" else (wcols, wdata)'''
assert t2.count(OLD5) == 1, f"C_assign CHO 5: {t2.count(OLD5)} lan"
t2 = t2.replace(OLD5, NEW5)

# kiem cuoi: bo qua Q0 khi check sin gia
OLD6 = '''    sin = []
    for n, *_r in BND:
        p = out / f"{n}.loi"'''
NEW6 = '''    sin = []
    for n, src, *_r in BND:
        if src == "Q0":
            continue
        p = out / f"{n}.loi"'''
assert t2.count(OLD6) == 1, f"C_assign CHO 6: {t2.count(OLD6)} lan"
t2 = t2.replace(OLD6, NEW6)

assert t2 != goc2
shutil.copy2(P2, P2.with_suffix(".py.bak"))
P2.write_text(t2, encoding="utf-8")
print(f"2. {P2}: doc bnd_map.csv + Q=0 cho kenh cut")

print("""
Kiem:
  python3 -m py_compile config/config.py src/C_assign_boundaries.py && echo "cu phap OK"
  python3 -c "from config.config import CFG; print(len(CFG.NETF.DROP_UPSTREAM),'nhanh loc')"

CHAY:
  # 1. Ledger lai (DROP_UPSTREAM doi)
  python3 src/A_extract_ledger.py --tier full 2>&1 | tail -2
  awk -F";" 'NR>1 && $3=="GIU"' output/ledger/branches.csv | wc -l

  # 2. KIEM BASELINE KHONG HONG (phai ra 22/47/224)
  python3 src/B_build_grid.py --subset truc_du --outdir /tmp/kt 2>&1 \\
      | grep -E "Tap con|SPLIT|Geometrie"

  # 3. Luoi full
  python3 src/B_build_grid.py --subset full --outdir output/grid/full4 2>&1 | tail -2
  python3 src/C_assign_boundaries.py --outdir output/grid/full4 \\
      --start 2011-10-01 --end 2011-10-31 2>&1 | head -20
""")
