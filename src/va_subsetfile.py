#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
va_subsetfile.py — THEM --subset-file: doc danh sach nhanh tu FILE

VI SAO:
  `SUBSETS` go tay (backbone/truc_du/truc/full44) khong the liet ke 208-288
  nhanh kenh truc. Can doc tu file sinh boi thuat toan loc.

THUAT TOAN LOC (chot 17/07 sau khi do 6 phuong an):
  GIU CUNG:
    - 11 nhanh TRUC: Tien, BASSAC, VamNao, CoChien, Ham Luong + 6 cua
    - 95 nhanh CO BIEN trong bnd_map.csv (cua ra bien — bo la mang khong thoat)
  LOC phan con lai:
    - cap <= K (khoang cach BFS toi TRUC)
    - rong >= W met

  Do 6 phuong an (ngan sach ~700 bief do gioi han len=8192 cua abscDebut):
    K=1 W=100m -> 173 nhanh ~415 bief    K=2 W=60m  -> 374 ~898  VUOT
    K=1 W=80m  -> 196 ~470               K=2 W=80m  -> 288 ~691  sat tran
    K=1 W=60m  -> 233 ~559               K=3 W=100m -> 234 ~562
    K=2 W=100m -> 208 ~499  <<< PA A     K=3 W=80m  -> 354 ~850  VUOT

GIOI HAN MASCARET (phat hien 17/07):
  `lec_reseau.f90:107  character(len=8192) :: line`
  -> the <abscDebut> voi 4513 bief = 57555 ky tu -> bi cat -> "Bad integer"
  -> NGAN SACH ~700 bief. KHONG sua source TELEMAC (da chay thong 4 lan).
  -> Don gian hoa LUOI, khong sua CONG CU.

DUNG:
  python3 src/B_build_grid.py --subset-file /tmp/pa_A.txt --outdir output/grid/paA

Co .bak + assert. Chay tu goc repo.
"""
import shutil
import sys
from pathlib import Path

P = Path("src/B_build_grid.py")
if not P.exists():
    sys.exit("[LOI] khong thay src/B_build_grid.py — chay tu goc repo")

txt = P.read_text(encoding="utf-8")
goc = txt

OLD1 = '''    ap.add_argument("--subset", default="backbone",
                    choices=["backbone", "truc", "truc_du", "full44",
                             "culao", "full"])'''
NEW1 = '''    ap.add_argument("--subset", default="backbone",
                    choices=["backbone", "truc", "truc_du", "full44",
                             "culao", "full"])
    ap.add_argument("--subset-file", default=None,
                    help="file .txt moi dong 1 ten nhanh (uu tien hon --subset). "
                         "Sinh boi thuat toan loc: TRUC + nhanh co bien + "
                         "cap<=K + rong>=W")'''
assert txt.count(OLD1) == 1, f"CHO 1: {txt.count(OLD1)} lan"
txt = txt.replace(OLD1, NEW1)

OLD2 = '''    if args.subset == "full":
        sel = kept'''
NEW2 = '''    if args.subset_file:
        want = [l.strip() for l in
                Path(args.subset_file).read_text(encoding="utf-8").splitlines()
                if l.strip()]
        sel = {n for n in kept if any(vn_norm(n) == vn_norm(b) for b in want)}
        thieu = [b for b in want
                 if not any(vn_norm(n) == vn_norm(b) for n in sel)]
        print(f"Doc {args.subset_file}: {len(want)} ten -> {len(sel)} nhanh khop")
        if thieu:
            print(f"   [!] {len(thieu)} ten KHONG co trong ledger: {thieu[:8]}")
    elif args.subset == "full":
        sel = kept'''
assert txt.count(OLD2) == 1, f"CHO 2: {txt.count(OLD2)} lan"
txt = txt.replace(OLD2, NEW2)

assert txt != goc
shutil.copy2(P, P.with_suffix(".py.bak"))
P.write_text(txt, encoding="utf-8")
print(f"XONG -> {P}")
print("""
Kiem:
  grep -c "subset_file" src/B_build_grid.py    # >= 3
  python3 -m py_compile src/B_build_grid.py && echo "cu phap OK"

CHAY PA A (208 nhanh, uoc ~499 bief):
  python3 src/B_build_grid.py --subset-file /tmp/pa_A.txt \\
      --outdir output/grid/paA 2>&1 | tail -6

  # SO BIEF THAT — quyet dinh PA A co vua ngan sach 700 khong
  python3 - <<'PY'
import re
from pathlib import Path
x = Path("output/grid/paA/mascaret.xcas").read_text(encoding="latin-1", errors="replace")
for t in ("listeBranches","listeNoeuds","extrLibres"):
    m = re.search(rf"<{t}>.*?<nb>(\\d+)</nb>", x, re.S)
    print(f"{t:15s} = {m.group(1) if m else '?'}")
# the dai nhat — phai < 8192
mx = max(((len(m.group(2)), m.group(1)) for m in
          re.finditer(r"<([a-zA-Z0-9_]+)>([^<]{200,})</\\1>", x)), default=(0,""))
print(f"\\nThe DAI NHAT: <{mx[1]}> = {mx[0]} ky tu  (gioi han 8192)")
print("  -> " + ("OK, chay duoc" if mx[0] < 8192 else "VUOT! phai giam nhanh"))
PY
""")
