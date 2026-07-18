#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
F_catalog_3nguon.py — BANG DOI CHIEU 3 NGUON: survey 2020 / MIKE / TELEMAC

VI SAO CAN:
  `proposed_report.txt` bao `mike=0` cho 33 nhanh cu lao -> SAI. Kiem tay cho
  thay Tien_1 co 1, NamThon co 12 mat cat MIKE. Nguyen nhan: catalog tra ten
  nwk11 ('Tien_1') thang vao location_id ('TIEN_1') — khong khop hoa/thuong.
  Cung loi do khien 'Tien' bi dem mike=2 trong khi that ra co 42.
  -> Bang nay khop bang vn_norm + kiem chung bang TOA DO.

QUY LUAT TEN SURVEY 2020 (§3.1 + Duy xac nhan phien 3):
  <tien to><so><hau to>   vd: ST 33 P
  CUNG SO = CUNG VI TRI DOC SONG, KHAC NHANH -> tao cu lao.
  Vd cum ST33: ST33->Tien | ST33P->Tien_9 | ST33P2->Tien_8  (3 nhanh)

  NHUNG hau to co HAI LOAI (khong dem mu):
    - NHANH   : P, P1, P2, P3, CT, CD, CDP, CDP1, CDP2  -> nhanh RIENG
    - BO SUNG : A, B                                     -> CUNG nhanh, mat cat them
    - TO HOP  : AP1 = bo sung A + nhanh P1
  Bang chung: ST33 va ST33A DEU chieu vao 'Tien' (d=46m/5.2m) nhung cach nhau
  4.8km doc song -> 'A' khong phai nhanh khac.

KIEM TRA (logic Duy nêu):
  1. Cum (pre,num) co k hau to loai NHANH -> phai chieu vao k nhanh MIKE khac
     nhau. Lech -> canh bao (toa do hoac topology sai).
  2. Moi nhanh MIKE: so mat cat MIKE (khop chinh xac + loc topo) vs survey.
  3. So be rong/day survey vs MIKE tung cap -> phat hien nguon khac nhau.
  4. Nhanh trong luoi TELEMAC -> bief nao, absc bao nhieu.

RA data_ref/catalog/:
  cat3_mat_cat.csv   — moi mat cat survey: ten,num,suf,loai_suf,x,y,
                       nhanh_MIKE,ch,d, rong_sv,rong_mike,lech_rong,
                       day_sv,day_mike,lech_day, bief_telemac,absc
  cat3_nhanh.csv     — moi nhanh: n_survey,n_mike,topo,dai_km,KC_TB,
                       trong_luoi,bief, canh_bao
  cat3_cum.csv       — moi cum (pre,num): hau to, so nhanh, kiem chung
  cat3_report.txt

DUNG:
  python3 src/F_catalog_3nguon.py
  python3 src/F_catalog_3nguon.py --outdir output/grid/backbone   # them cot TELEMAC
"""
import argparse
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import numpy as np
import pandas as pd

try:
    import mikeio1d
except Exception:
    mikeio1d = None

# ---- phan loai hau to (§3.1) ----
SUF_NHANH = {"P", "P1", "P2", "P3", "CT", "CD", "CDP", "CDP1", "CDP2"}
SUF_BOSUNG = {"A", "B"}

TOPO_UU_TIEN = ["2021_SIWRP_QHPCTT", "SIWRR2020", "DH2020", "2020_KHCN",
                "2018", "2014", "2011_KHCN"]
TOPO_CAM = ["2006", "2000", "2001", "TOPO?", "TGLX2010"]


def vn_norm(s):
    """Bo dau tieng Viet + ky tu dac biet. 'ST37CĐ'->'ST37CD', 'Tien_1'->'TIEN1'."""
    s = str(s).replace("\u0110", "D").replace("\u0111", "d")
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()


def loai_suf(suf):
    """-> 'chinh' | 'nhanh' | 'bosung' | 'to_hop'"""
    if pd.isna(suf) or str(suf).strip() == "":
        return "chinh"
    s = str(suf).strip().upper()
    if s in SUF_NHANH:
        return "nhanh"
    if s in SUF_BOSUNG:
        return "bosung"
    # to hop: bat dau bang A/B roi den P... -> vd AP1
    m = re.match(r"^([AB])(P\d*)$", s)
    if m:
        return "to_hop"
    return "khac"


def la_nhanh_rieng(suf):
    """Hau to nay co tao NHANH RIENG khong?"""
    return loai_suf(suf) in ("nhanh", "to_hop")


def doc_mike(path):
    """-> {vn_norm(location_id): [(loc_goc, topo, ch, rong, day)]}"""
    if mikeio1d is None:
        sys.exit("[LOI] thieu mikeio1d — chay bang venv")
    xns = mikeio1d.open(str(path))
    df = xns.to_dataframe().reset_index()
    out = defaultdict(list)
    for _, r in df.iterrows():
        try:
            raw = r["cross_section"].raw
            if raw is None or len(raw) < 2:
                continue
            x = [float(v) for v in raw["x"].values]
            z = [float(v) for v in raw["z"].values]
            loc, topo = str(r["location_id"]), str(r["topo_id"])
            out[vn_norm(loc)].append(
                (loc, topo, float(r["chainage"]), max(x) - min(x), min(z)))
        except Exception:
            continue
    return out


def chon_topo(lst):
    """lst=[(loc,topo,ch,rong,day)] -> (topo_chon, [rec cua topo do], {topo bo: n})"""
    by = defaultdict(list)
    for rec in lst:
        by[rec[1]].append(rec)
    pick = None
    for t in TOPO_UU_TIEN:
        if t in by:
            pick = t
            break
    if pick is None:
        ok = {t: v for t, v in by.items() if t not in TOPO_CAM}
        pick = max(ok, key=lambda t: len(ok[t])) if ok else \
            max(by, key=lambda t: len(by[t]))
    bo = {t: len(v) for t, v in by.items() if t != pick}
    return pick, sorted(by[pick], key=lambda r: r[2]), bo


def doc_bief_map(outdir):
    """bief_map.txt -> {vn_norm(ten): [(bief, ch0, ch1, absc0, absc1)]}"""
    p = Path(outdir) / "bief_map.txt" if outdir else None
    out = defaultdict(list)
    if not p or not p.exists():
        return out
    for l in p.read_text(encoding="utf-8", errors="replace").splitlines():
        if l.startswith("#") or not l.strip():
            continue
        q = l.split("\t")
        if len(q) < 7:
            continue
        try:
            out[vn_norm(q[1])].append((int(q[0]), float(q[2]), float(q[3]),
                                       float(q[5]), float(q[6])))
        except ValueError:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=None,
                    help="thu muc luoi TELEMAC (co bief_map.txt) -> them cot bief")
    ap.add_argument("--max-d", type=float, default=200.0,
                    help="survey chieu xa hon nguong -> khong tinh")
    ap.add_argument("--dch-max", type=float, default=500.0,
                    help="ghep survey<->MIKE neu lech chainage < nguong")
    args = ap.parse_args()

    out = CFG.OUT.ROOT / "data_ref" / "catalog"
    out.mkdir(parents=True, exist_ok=True)
    print("=== BANG DOI CHIEU 3 NGUON: survey 2020 / MIKE / TELEMAC ===\n")

    # ---------------------------------------------------------- 1. doc nguon
    cat_p = out / "catalog_survey.csv"
    if not cat_p.exists():
        sys.exit(f"[LOI] chua co {cat_p} — chay build_catalog.py truoc")
    sv = pd.read_csv(cat_p, sep=";")
    print(f"catalog_survey : {len(sv)} diem")

    mk = doc_mike(CFG.DATA.XNS11)
    print(f"xns11          : {len(mk)} location_id (sau vn_norm)")

    bm = doc_bief_map(args.outdir)
    if bm:
        print(f"bief_map       : {len(bm)} nhanh trong luoi TELEMAC")
    else:
        print("bief_map       : (khong co — bo qua cot TELEMAC)")

    # ---------------------------------------------- 2. phan loai hau to
    sv["loai_suf"] = sv["suf"].apply(loai_suf)
    sv["la_nhanh"] = sv["suf"].apply(la_nhanh_rieng)
    for c in ("num", "x_utm", "y_utm", "mike1_ch", "mike1_d",
              "rong_excel", "rong_tuyen", "z_day"):
        sv[c] = pd.to_numeric(sv[c], errors="coerce")

    print("\nHau to survey 2020 — phan loai:")
    for k, n in sv["loai_suf"].value_counts().items():
        vd = sorted(set(sv[sv["loai_suf"] == k]["suf"].dropna().astype(str)))[:6]
        print(f"   {k:8s} {n:4d}  {vd}")

    # ------------------------------------- 3. KIEM CUM: k hau to -> k nhanh?
    print(f"\n=== KIEM CUM (cung so = cung vi tri, khac nhanh) ===")
    cum_rows = []
    g = sv[(sv["co_z"] == "yes") & sv["num"].notna() & sv["pre"].notna()]
    for (pre, num), grp in g.groupby(["pre", "num"]):
        nhanh_mike = sorted(set(grp["mike1"].dropna().astype(str)))
        sufs = [("" if pd.isna(s) else str(s)) for s in grp["suf"]]
        n_nhanh_suf = sum(1 for _, r in grp.iterrows()
                          if r["loai_suf"] in ("chinh", "nhanh", "to_hop"))
        khop = len(nhanh_mike) == n_nhanh_suf
        cum_rows.append({
            "pre": pre, "num": int(num), "n_mat_cat": len(grp),
            "hau_to": ",".join(sufs), "n_suf_nhanh": n_nhanh_suf,
            "nhanh_mike": ",".join(nhanh_mike), "n_nhanh_mike": len(nhanh_mike),
            "khop": "OK" if khop else "LECH",
            "d_max": round(grp["mike1_d"].max(), 1),
        })
    cum = pd.DataFrame(cum_rows).sort_values(["pre", "num"])
    cum.to_csv(out / "cat3_cum.csv", sep=";", index=False)
    n_lech = (cum["khop"] == "LECH").sum()
    n_chia = (cum["n_nhanh_mike"] > 1).sum()
    print(f"   {len(cum)} cum | {n_chia} cum chia nhanh (>1 nhanh MIKE) | "
          f"{n_lech} cum LECH")
    if n_lech:
        print(f"\n   {'cum':8s} {'hau_to':22s} {'n_suf':>5s} {'n_mike':>6s}  nhanh_MIKE")
        for _, r in cum[cum["khop"] == "LECH"].head(12).iterrows():
            print(f"   {r['pre']}{r['num']:<6d} {r['hau_to'][:22]:22s} "
                  f"{r['n_suf_nhanh']:5d} {r['n_nhanh_mike']:6d}  {r['nhanh_mike'][:40]}")

    # -------------------------------- 4. GHEP survey <-> MIKE tung mat cat
    print(f"\n=== GHEP survey <-> MIKE (nguong chainage {args.dch_max:.0f}m) ===")
    rows = []
    for _, r in sv.iterrows():
        nh = r["mike1"]
        rec = {
            "ten": r["ten"], "pre": r["pre"], "num": r["num"], "suf": r["suf"],
            "loai_suf": r["loai_suf"], "x_utm": r["x_utm"], "y_utm": r["y_utm"],
            "co_z": r["co_z"], "nhanh_mike": nh, "ch_mike": r["mike1_ch"],
            "d_chieu": r["mike1_d"], "rong_sv": r["rong_excel"],
            "rong_tuyen": r["rong_tuyen"], "day_sv": r["z_day"],
            "rong_mike": np.nan, "day_mike": np.nan, "topo": None,
            "lech_rong": np.nan, "lech_day": np.nan,
            "bief": None, "absc": np.nan,
        }
        if pd.notna(nh) and vn_norm(nh) in mk:
            topo, lst, _bo = chon_topo(mk[vn_norm(nh)])
            rec["topo"] = topo
            if pd.notna(r["mike1_ch"]) and lst:
                i = min(range(len(lst)), key=lambda k: abs(lst[k][2] - r["mike1_ch"]))
                if abs(lst[i][2] - r["mike1_ch"]) <= args.dch_max:
                    rec["rong_mike"] = round(lst[i][3], 1)
                    rec["day_mike"] = round(lst[i][4], 2)
                    if pd.notna(r["rong_excel"]):
                        rec["lech_rong"] = round(r["rong_excel"] - lst[i][3], 1)
                    if pd.notna(r["z_day"]):
                        rec["lech_day"] = round(r["z_day"] - lst[i][4], 2)
        # TELEMAC
        if pd.notna(nh) and vn_norm(nh) in bm and pd.notna(r["mike1_ch"]):
            for (b, ch0, ch1, a0, a1) in bm[vn_norm(nh)]:
                if ch0 - 1 <= r["mike1_ch"] <= ch1 + 1:
                    rec["bief"] = b
                    rec["absc"] = round(a0 + (r["mike1_ch"] - ch0), 1)
                    break
        rows.append(rec)
    d3 = pd.DataFrame(rows)
    d3.to_csv(out / "cat3_mat_cat.csv", sep=";", index=False)

    ok = d3[d3["lech_rong"].notna()]
    if len(ok):
        lr = ok["lech_rong"].abs()
        ld = ok["lech_day"].abs().dropna()
        print(f"   {len(ok)} cap ghep duoc")
        print(f"   |lech| BE RONG: TB {lr.mean():6.1f}m  max {lr.max():7.1f}m")
        if len(ld):
            print(f"   |lech| DAY    : TB {ld.mean():6.2f}m  max {ld.max():7.2f}m")
        n_giong = int((lr < 20).sum())
        print(f"   -> {n_giong}/{len(ok)} cap GIONG NHAU (|lech rong| < 20m)")
        xau = ok[lr > 100].sort_values("lech_rong", key=abs, ascending=False)
        if len(xau):
            print(f"\n   {len(xau)} cap LECH > 100m:")
            for _, r in xau.head(8).iterrows():
                print(f"      {str(r['ten'])[:10]:10s} {str(r['nhanh_mike']):12s} "
                      f"ch={r['ch_mike']:8.0f}  sv={r['rong_sv']:7.1f} "
                      f"mk={r['rong_mike']:7.1f}  lech={r['lech_rong']:+8.1f}")

    # ------------------------------------------------- 5. BANG THEO NHANH
    print(f"\n=== BANG THEO NHANH ===")
    nrows = []
    nhanh_sv = sv[sv["co_z"] == "yes"].groupby("mike1").size().to_dict()
    tat_ca = set(nhanh_sv) | {n for n in sv["mike1"].dropna().astype(str)}
    for nh in sorted(tat_ca):
        k = vn_norm(nh)
        n_mk, topo, bo, dai = 0, None, {}, np.nan
        if k in mk:
            topo, lst, bo = chon_topo(mk[k])
            n_mk = len(lst)
            if n_mk >= 2:
                dai = (lst[-1][2] - lst[0][2]) / 1000.0
        n_sv = int(nhanh_sv.get(nh, 0))
        biefs = [b for (b, *_r) in bm.get(k, [])]
        cb = []
        if n_mk == 1:
            cb.append("CHI_1_MAT_CAT->lang_tru")
        if n_mk >= 2 and dai == dai and dai > 0 and dai / max(n_mk - 1, 1) > 5:
            cb.append(f"THUA_KC={dai/(n_mk-1):.1f}km")
        if bo:
            cb.append(f"BO_TOPO={bo}")
        nrows.append({
            "nhanh": nh, "n_survey": n_sv, "n_mike": n_mk, "topo": topo,
            "dai_km": round(dai, 1) if dai == dai else None,
            "kc_tb_km": round(dai / (n_mk - 1), 2) if n_mk >= 2 and dai == dai else None,
            "trong_luoi": "yes" if biefs else "no",
            "bief": ",".join(str(b) for b in biefs) if biefs else "",
            "canh_bao": " | ".join(cb),
        })
    dn = pd.DataFrame(nrows).sort_values(["trong_luoi", "n_survey"],
                                         ascending=[False, False])
    dn.to_csv(out / "cat3_nhanh.csv", sep=";", index=False)

    trong = dn[dn["trong_luoi"] == "yes"]
    ngoai = dn[(dn["trong_luoi"] == "no") & (dn["n_survey"] > 0)]
    print(f"   {len(trong)} nhanh TRONG luoi | {len(ngoai)} nhanh co survey NGOAI luoi")
    print(f"\n   {'nhanh':14s} {'sv':>3s} {'mike':>4s} {'km':>6s} {'KC':>5s} "
          f"{'bief':>6s}  canh_bao")
    for _, r in dn[(dn["n_survey"] > 0) | (dn["trong_luoi"] == "yes")].iterrows():
        print(f"   {str(r['nhanh'])[:14]:14s} {r['n_survey']:3d} {r['n_mike']:4d} "
              f"{(r['dai_km'] if r['dai_km'] else 0):6.1f} "
              f"{(r['kc_tb_km'] if r['kc_tb_km'] else 0):5.1f} "
              f"{str(r['bief'])[:6]:>6s}  {r['canh_bao'][:44]}")

    # ------------------------------------------------------- 6. bao cao
    L = []
    A = L.append
    A("BANG DOI CHIEU 3 NGUON: survey 2020 / MIKE / TELEMAC")
    A("=" * 72)
    A(f"\nsurvey 2020 : {len(sv)} diem ({int((sv['co_z']=='yes').sum())} co z)")
    A(f"MIKE xns11  : {len(mk)} location_id")
    A(f"TELEMAC     : {len(bm)} nhanh trong luoi" if bm else "TELEMAC     : —")
    A(f"\n--- HAU TO ---")
    for k, n in sv["loai_suf"].value_counts().items():
        A(f"  {k:8s} {n:4d}")
    A(f"\n--- CUM (cung so = cung vi tri doc song) ---")
    A(f"  Tong cum        : {len(cum)}")
    A(f"  Cum chia nhanh  : {n_chia}")
    A(f"  Cum LECH        : {n_lech}  (so hau to != so nhanh MIKE)")
    if len(ok):
        A(f"\n--- GHEP survey <-> MIKE ({len(ok)} cap) ---")
        A(f"  |lech| be rong TB : {lr.mean():.1f} m")
        if len(ld):
            A(f"  |lech| day TB     : {ld.mean():.2f} m")
        A(f"  Cap giong nhau    : {n_giong}/{len(ok)}")
    A(f"\n--- NHANH CANH BAO ---")
    for _, r in dn[dn["canh_bao"] != ""].iterrows():
        A(f"  {str(r['nhanh']):14s} sv={r['n_survey']:2d} mike={r['n_mike']:2d}  "
          f"{r['canh_bao']}")
    (out / "cat3_report.txt").write_text("\n".join(L), encoding="utf-8")

    print(f"\nXONG -> {out}/")
    for f in ("cat3_mat_cat.csv", "cat3_nhanh.csv", "cat3_cum.csv",
              "cat3_report.txt"):
        print(f"   {f}")


if __name__ == "__main__":
    main()
