#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
G_doc_bnd11.py — DOC Boundary_2011.bnd11 -> BANG BIEN CHO MOI NHANH

VI SAO CAN (phat hien 17/07):
  `--subset full` sinh 4660 bief / 124 BIEN TU DO. `MAP_SONG` go tay trong
  C_assign_boundaries chi biet 9 bien -> 115 bien con lai KHONG co so lieu
  -> tuong chung phai bia Q=0.
  NHUNG `.bnd11` co 1709 BndItem — MIKE DA GAN SAN bien cho MOI nhanh cut:
    AMAB7      -> H_boudary_DBNN2024.dfs0 item '10.Xeo Ro'
    Ba Hon     -> H_boudary_2011.dfs0     item 'Rach Gia'
    Bay Hap    -> H_boudary_2011.dfs0     item 'Song Doc'
    Branch1016 -> H_boudary_2011.dfs0     item 'Ganh hao'
  => Bai toan "124 bien khong co so lieu" KHONG TON TAI. Chi can doc .bnd11.

CAU TRUC (da giai ma bang cach tra nhanh DA BIET chainage):
  DescType = <type>, <sub>, '<nhanh>', <CHAINAGE>, 0, '', '<nhan/tram>'
     type=0 -> BIEN MO (cua bien)     vd: 0,5,'CuaCoChien',30881,..,'Ben Trai '
     type=1 -> NHAP LUU noi dong      vd: 1,0,'BASSAC',74310,..,'W16 '
     type=5 -> bien vung              vd: 5,0,'AMAB7',0,..,'Rach Gia'
  Inflow = 2,0,0, |<file.dfs0>|, 0, <idx>, '<ten item>', 0, 1

KIEM CHUNG: type=0 khop 3/3 voi MAP_SONG go tay ->
  CuaCoChien->Ben Trai | CuaTieu->Vam Kenh | Ham Luong->An Thuan
  => cach map bien->tram cua ta DUNG, chi thieu do phu (9/124).

RA data_ref/catalog/:
  bnd_map.csv      — nhanh;chainage;type;loai;nhan;file_dfs0;item;cot_obs;co_so_lieu
  bnd_report.txt

DUNG:
  python3 src/G_doc_bnd11.py
  python3 src/G_doc_bnd11.py --chi-bien-mo     # chi type=0 (bo qua nhap luu)
"""
import argparse
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import pandas as pd

LOAI = {0: "bien_mo", 1: "nhap_luu", 2: "type2", 3: "type3", 4: "type4",
        5: "bien_vung"}


def vn_norm(s):
    """Bo dau tieng Viet + ky tu dac biet. 'Xeo ro' -> 'XEORO'."""
    s = str(s).replace("\u0110", "D").replace("\u0111", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def doc_cot_obs():
    """-> ({vn_norm(cot): cot} cua WL, cua Q)"""
    def cot(p):
        L = Path(p).read_text(encoding="utf-8", errors="replace").splitlines()
        return re.split(r"\s+", L[1].strip())[1:]
    wl = {vn_norm(c.replace("H_", "")): c for c in cot(CFG.DATA.WL_OBS)}
    q = {vn_norm(c.replace("Q_", "")): c for c in cot(CFG.DATA.Q_OBS)}
    return wl, q


def doc_bnd(path):
    """-> list dict: nhanh, ch, type, nhan, file_dfs0, item"""
    t = Path(path).read_text(encoding="utf-8", errors="replace")
    out = []
    for blk in re.split(r"\[BndItem\]", t)[1:]:
        e = blk.find("EndSect  // BndItem")
        b = blk[:e] if e > 0 else blk
        m = re.search(
            r"DescType\s*=\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']*)'\s*,"
            r"\s*([\-\d.]+)\s*,\s*[\-\d.]+\s*,\s*'[^']*'\s*,\s*'([^']*)'", b)
        if not m:
            continue
        typ, sub, nhanh, ch, nhan = (int(m.group(1)), int(m.group(2)),
                                     m.group(3), float(m.group(4)),
                                     m.group(5).strip())
        f = it = ""
        mi = re.search(r"Inflow\s*=\s*[\d\s,]*\|([^|]*)\|\s*,\s*[\d]+\s*,"
                       r"\s*[\d]+\s*,\s*'([^']*)'", b)
        if mi:
            f = Path(mi.group(1).replace("\\", "/")).name
            it = mi.group(2).strip()
        out.append({"nhanh": nhanh, "chainage": ch, "type": typ, "sub": sub,
                    "loai": LOAI.get(typ, f"type{typ}"), "nhan": nhan,
                    "file_dfs0": f, "item": it})
    return out


def tra_cot(nhan, item, wl, q):
    """Tra nhan/item -> cot trong WL_OBS hoac Q_OBS. -> (cot, nguon)"""
    for s in (item, nhan):
        if not s:
            continue
        # bo tien to so: '10.Xeo Ro' -> 'Xeo Ro'
        s2 = re.sub(r"^\s*\d+\s*\.\s*", "", s)
        k = vn_norm(s2)
        if k in wl:
            return wl[k], "H"
        if k in q:
            return q[k], "Q"
    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--chi-bien-mo", action="store_true",
                    help="chi lay type=0 (bien mo), bo qua nhap luu")
    args = ap.parse_args()

    out = CFG.OUT.ROOT / "data_ref" / "catalog"
    out.mkdir(parents=True, exist_ok=True)
    print("=== DOC Boundary_2011.bnd11 ===\n")

    wl, q = doc_cot_obs()
    print(f"WL_OBS: {len(wl)} cot | Q_OBS: {len(q)} cot")

    rec = doc_bnd(CFG.DATA.BND11)
    print(f"bnd11 : {len(rec)} BndItem doc duoc\n")

    print("=== PHAN LOAI theo `type` ===")
    for t, n in sorted(Counter(r["type"] for r in rec).items()):
        vd = [r["nhanh"] for r in rec if r["type"] == t][:3]
        print(f"   type={t} ({LOAI.get(t,'?'):10s}) {n:5d}  vd: {vd}")

    # tra cot OBS
    for r in rec:
        c, src = tra_cot(r["nhan"], r["item"], wl, q)
        r["cot_obs"] = c or ""
        r["nguon"] = src or ""
        r["co_so_lieu"] = "yes" if c else "no"

    d = pd.DataFrame(rec)
    if args.chi_bien_mo:
        d = d[d["type"] == 0]
    d = d.sort_values(["type", "nhanh", "chainage"])
    d.to_csv(out / "bnd_map.csv", sep=";", index=False)

    print(f"\n=== TRA COT OBS ===")
    ok = (d["co_so_lieu"] == "yes").sum()
    print(f"   {ok}/{len(d)} BndItem tra duoc cot OBS")

    bm = d[d["type"] == 0]
    ok_bm = (bm["co_so_lieu"] == "yes").sum()
    print(f"   BIEN MO (type=0): {ok_bm}/{len(bm)} tra duoc")

    print(f"\n=== BIEN MO — nhan -> cot OBS ===")
    print(f"{'nhanh':22s} {'ch':>8s} {'nhan':16s} {'item':16s} {'-> cot OBS':14s}")
    print("-" * 82)
    for _, r in bm.head(30).iterrows():
        mark = "" if r["co_so_lieu"] == "yes" else "  <<< KHONG TRA DUOC"
        print(f"{str(r['nhanh'])[:22]:22s} {r['chainage']:8.0f} "
              f"{str(r['nhan'])[:16]:16s} {str(r['item'])[:16]:16s} "
              f"{str(r['cot_obs']):14s}{mark}")

    thieu = bm[bm["co_so_lieu"] == "no"]
    if len(thieu):
        print(f"\n=== {len(thieu)} BIEN MO KHONG TRA DUOC COT ===")
        for nhan, n in Counter(thieu["nhan"]).most_common(15):
            nh = list(thieu[thieu["nhan"] == nhan]["nhanh"])[:3]
            print(f"   '{nhan}' x{n}  vd: {nh}")

    print(f"\n=== FILE dfs0 ===")
    for f, n in Counter(x for x in d["file_dfs0"] if x).most_common():
        print(f"   {n:5d} x {f}")

    # bao cao
    L = []
    A = L.append
    A("BANG BIEN TU Boundary_2011.bnd11")
    A("=" * 70)
    A(f"\n{len(rec)} BndItem | {ok} tra duoc cot OBS")
    A(f"\n--- THEO type ---")
    for t, n in sorted(Counter(r["type"] for r in rec).items()):
        A(f"  type={t} ({LOAI.get(t,'?')}) : {n}")
    A(f"\n--- BIEN MO (type=0): {len(bm)} ---")
    for _, r in bm.iterrows():
        A(f"  {str(r['nhanh']):22s} ch={r['chainage']:8.0f} "
          f"'{r['nhan']}' -> {r['cot_obs'] or 'KHONG TRA DUOC'}")
    (out / "bnd_report.txt").write_text("\n".join(L), encoding="utf-8")

    print(f"\nXONG -> {out}/bnd_map.csv + bnd_report.txt")


if __name__ == "__main__":
    main()
