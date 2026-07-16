#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
E_package_run.py — DONG GOI 1 LAN CHAY THANH MAU TAI SU DUNG

VI SAO CAN:
  1 lan chay sinh ResultatsOpthyca.opt 158MB — khong the commit, khong the luu
  nhieu kich ban. Nhung cac file DAU VAO chi ~2MB va TAI TAO duoc ket qua
  trong 35 giay. -> Luu dau vao + tom tat ket qua, bo .opt.

  Sau nay chay kich ban khac (doi Strickler, doi bien, mo rong luoi) chi can
  copy goi nay ra thu muc moi, sua tham so, chay lai 35s.

GOI GOM (RUN_<ten>/):
  input/          geometrie, mascaret.xcas, init.lig, *.loi, bief_map.txt,
                  FichierCas.txt, dico.txt  -> du de chay lai NGAY
  summary/        eval_report.txt, station_map.csv, *.png (nhe)
  extract/        timeseries_stations.csv  — Z,Q tai 5 tram (thay cho .opt 158MB)
  META.json       tham so + KGE/NSE + thoi gian chay + git commit
  RUN.sh          script chay lai 1 lenh

DUNG:
  # dong goi lan chay hien tai
  python3 src/E_package_run.py --outdir output/grid/backbone --name baseline_2020

  # chay lai tu goi
  cd runs/RUN_baseline_2020 && bash RUN.sh
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

import pandas as pd

# file DAU VAO — du de tai tao ket qua
INPUT_FILES = ["geometrie", "mascaret.xcas", "init.lig", "bief_map.txt",
               "FichierCas.txt", "dico.txt", "Abaques.txt", "Controle.txt",
               "dico_Courlis.txt"]


def git_info(root):
    try:
        h = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(root),
                           capture_output=True, text=True).stdout.strip()
        d = subprocess.run(["git", "status", "--porcelain"], cwd=str(root),
                           capture_output=True, text=True).stdout.strip()
        return {"commit": h, "clean": len(d) == 0}
    except Exception:
        return {"commit": "?", "clean": False}


def read_xcas_params(p):
    x = p.read_text(encoding="latin-1", errors="replace")
    out = {}
    for k in ("tempsMax", "pasTemps", "pasStock", "hauteurEauMini",
              "coefLitMin", "coefLitMaj", "code", "versionCode"):
        m = re.search(rf"<{k}>([^<]*)</{k}>", x)
        if m:
            out[k] = m.group(1).strip()
    m = re.search(r"<listeBranches>\s*<nb>(\d+)</nb>", x, re.S)
    if m:
        out["nb_bief"] = int(m.group(1))
    m = re.search(r"<listeNoeuds>\s*<nb>(\d+)</nb>", x, re.S)
    if m:
        out["nb_nut"] = int(m.group(1))
    return out


def extract_stations(optp, smap_csv, start, outp):
    """Trich Z,Q tai cac tram tu .opt -> CSV nhe (thay cho 158MB)."""
    if not smap_csv.exists():
        print("   [!] khong co station_map.csv -> bo qua extract")
        return 0
    sm = pd.read_csv(smap_csv, sep=";")
    want = {(int(r["bief"]), int(r["sec"])): r["tram"] for _, r in sm.iterrows()}
    rows = []
    with open(optp, encoding="latin-1", errors="replace") as f:
        started = False
        for line in f:
            if not started:
                if line.strip().startswith("[resultats]"):
                    started = True
                continue
            q = line.split(";")
            if len(q) < 14:
                continue
            try:
                key = (int(q[1].strip().strip('"')), int(q[2].strip().strip('"')))
            except ValueError:
                continue
            if key not in want:
                continue
            try:
                t = float(q[0])
                rows.append({
                    "tram": want[key],
                    "thoi_gian": (start + timedelta(seconds=t)).strftime(
                        "%Y-%m-%d %H:%M:%S"),
                    "t_s": t, "bief": key[0], "sec": key[1],
                    "ZREF": float(q[4]), "Z": float(q[5]), "QMIN": float(q[6]),
                    "FR": float(q[10]), "VMIN": float(q[11]),
                    "Y": float(q[12]), "Q": float(q[13])})
            except ValueError:
                continue
    d = pd.DataFrame(rows)
    d.to_csv(outp, sep=";", index=False)
    return len(d)


def parse_eval(p):
    """eval_report.txt -> {tram: {WL_KGE, Q_KGE, ...}} + thoi gian chay."""
    if not p.exists():
        return {}, None
    txt = p.read_text(encoding="utf-8", errors="replace")
    res, dt = {}, None
    m = re.search(r"THOI GIAN CHAY:\s*([\d.]+)s", txt)
    if m:
        dt = float(m.group(1))
    for l in txt.splitlines():
        q = l.split()
        if len(q) == 6 and q[0] in ("TanChau", "ChauDoc", "VamNao", "MyThuan",
                                    "CanTho"):
            def f(v):
                try:
                    return float(v)
                except ValueError:
                    return None
            res[q[0]] = {"WL_NSE": f(q[1]), "WL_KGE": f(q[2]),
                         "Q_NSE": f(q[3]), "Q_KGE": f(q[4]), "n": f(q[5])}
    m = re.search(r"Froude max toan mang:\s*([\d.]+)", txt)
    fr = float(m.group(1)) if m else None
    return res, (dt, fr)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--name", required=True, help="ten goi, vd baseline_2020")
    ap.add_argument("--dest", default=None, help="mac dinh <repo>/runs/")
    ap.add_argument("--start", default="2011-10-01")
    ap.add_argument("--note", default="", help="ghi chu ve lan chay nay")
    ap.add_argument("--keep-opt", action="store_true",
                    help="giu ca .opt (158MB) — mac dinh KHONG")
    args = ap.parse_args()

    src = Path(args.outdir)
    dest = Path(args.dest) if args.dest else CFG.OUT.ROOT / "runs"
    pkg = dest / f"RUN_{args.name}"
    start = datetime.strptime(args.start, "%Y-%m-%d")

    print(f"=== DONG GOI: {pkg} ===\n")
    for d in ("input", "summary", "extract"):
        (pkg / d).mkdir(parents=True, exist_ok=True)

    # ---- 1. dau vao ----
    print("1. Copy dau vao (du de chay lai):")
    n = 0
    for f in INPUT_FILES:
        p = src / f
        if p.exists():
            shutil.copy2(p, pkg / "input" / f)
            n += 1
    for p in src.glob("*.loi"):
        shutil.copy2(p, pkg / "input" / p.name)
        n += 1
    sz = sum(f.stat().st_size for f in (pkg / "input").iterdir()) / 1e6
    print(f"   {n} file, {sz:.2f} MB")

    # ---- 2. tom tat ----
    print("2. Copy tom tat + hinh:")
    ed = src / "eval"
    m = 0
    for p in list(ed.glob("*.png")) + list(ed.glob("*.txt")) + \
            list(ed.glob("*.csv")):
        shutil.copy2(p, pkg / "summary" / p.name)
        m += 1
    for p in (src / "plots").glob("*.png"):
        shutil.copy2(p, pkg / "summary" / p.name)
        m += 1
    print(f"   {m} file")

    # ---- 3. trich .opt -> CSV nhe ----
    optp = src / "ResultatsOpthyca.opt"
    nrow = 0
    if optp.exists():
        osz = optp.stat().st_size / 1e6
        print(f"3. Trich .opt ({osz:.0f} MB) -> CSV tram:")
        nrow = extract_stations(optp, ed / "station_map.csv", start,
                                pkg / "extract" / "timeseries_stations.csv")
        csz = (pkg / "extract" / "timeseries_stations.csv").stat().st_size / 1e6
        print(f"   {nrow} dong, {csz:.2f} MB (giam {osz/max(csz,0.01):.0f} lan)")
        if args.keep_opt:
            shutil.copy2(optp, pkg / "extract" / "ResultatsOpthyca.opt")
            print("   [+] giu ca .opt theo yeu cau")

    # ---- 4. META ----
    print("4. Ghi META.json:")
    par = read_xcas_params(src / "mascaret.xcas")
    ev, (dt, fr) = parse_eval(ed / "eval_report.txt")
    nprof = sum(1 for l in (src / "geometrie").read_text(
        encoding="latin-1", errors="replace").splitlines()
        if l.startswith("PROFIL"))
    meta = {
        "ten": args.name,
        "ngay_dong_goi": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ghi_chu": args.note,
        "git": git_info(CFG.OUT.ROOT),
        "luoi": {"n_bief": par.get("nb_bief"), "n_nut": par.get("nb_nut"),
                 "n_profil": nprof},
        "tham_so": par,
        "nguon_mat_cat": "survey 2020 / MIKE topo 2021_SIWRP_QHPCTT (BO 2006)",
        "thoi_gian_chay_s": dt,
        "froude_max": fr,
        "ket_qua": ev,
    }
    (pkg / "META.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"   nb_bief={par.get('nb_bief')} nprof={nprof} "
          f"t_chay={dt}s Fr_max={fr}")

    # ---- 5. RUN.sh ----
    (pkg / "RUN.sh").write_text(f"""#!/bin/bash
# Chay lai goi nay: {args.name}
# Dong goi: {meta['ngay_dong_goi']} | git {meta['git']['commit']}
set -e
D=$(cd "$(dirname "$0")" && pwd)
W=${{1:-$D/work}}
echo "Thu muc chay: $W"
mkdir -p "$W"
cp "$D"/input/* "$W"/
cd "$W"
echo "Chay mascaret (uoc {dt if dt else '~35'}s)..."
time mascaret.py mascaret.xcas
grep -c FIN listing.lis && echo ">>> XONG: $W/ResultatsOpthyca.opt"
""", encoding="utf-8")
    (pkg / "RUN.sh").chmod(0o755)

    # ---- 6. README ----
    kq = "\n".join(
        f"| {k} | {v['WL_KGE']} | {v['Q_KGE']} |" for k, v in ev.items())
    (pkg / "README.md").write_text(f"""# RUN_{args.name}

{args.note}

Đóng gói: {meta['ngay_dong_goi']} | git `{meta['git']['commit']}`

## Lưới
{par.get('nb_bief')} bief, {par.get('nb_nut')} nút, {nprof} PROFIL
Mặt cắt: survey 2020 / MIKE topo `2021_SIWRP_QHPCTT` (**bỏ 2006**)

## Tham số
`pasTemps={par.get('pasTemps')}` | `tempsMax={par.get('tempsMax')}` |
`Strickler={par.get('coefLitMin')}` | `hauteurEauMini={par.get('hauteurEauMini')}`

## Kết quả
Thời gian chạy: **{dt}s** | Froude max: **{fr}**

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
{kq}

## Chạy lại
```bash
bash RUN.sh              # chay vao ./work/
bash RUN.sh /tmp/thu     # hoac thu muc khac
```

## Cấu trúc
- `input/` — đủ để chạy lại ngay ({sz:.1f} MB)
- `summary/` — báo cáo + hình
- `extract/timeseries_stations.csv` — Z,Q tại 5 trạm ({nrow} dòng)
  (thay cho `.opt` 158MB — tái tạo bằng `RUN.sh` nếu cần đầy đủ)
- `META.json` — tham số + kết quả dạng máy đọc
""", encoding="utf-8")

    tot = sum(f.stat().st_size for f in pkg.rglob("*") if f.is_file()) / 1e6
    print(f"\nXONG -> {pkg}/  ({tot:.1f} MB)")
    print(f"   Chay lai: cd {pkg} && bash RUN.sh")


if __name__ == "__main__":
    main()
