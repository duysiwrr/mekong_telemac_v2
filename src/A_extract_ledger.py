#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A_extract_ledger.py — GIAI ĐOẠN A: SỔ CÁI SẠCH

Mục tiêu: đọc TOÀN BỘ mạng MIKE (nwk11 + xns11 + bnd11), chuẩn hóa lại tên/nút
cho đồng nhất, phân loại nhánh GIỮ/BỎ theo topology (không theo tên), rồi xuất
một "sổ cái" con người đọc được làm nguồn chân lý cho Giai đoạn B.

Đây KHÔNG sinh geometrie. Chỉ hiểu + thiết lập lại thông tin. Sinh lưới là GĐ B.

RA (trong output/ledger/):
  branches.csv   — mỗi nhánh: id_moi, ten_mike, giu/bo, ly_do, width, n_xsec,
                   us_node, ds_node, ch_start, ch_end, co_survey2020
  nodes.csv      — mỗi nút: id_nut, cac_nhanh_noi_vao, toa_do_dai_dien
  boundaries.csv — mỗi biên: nhanh, chainage, loai(Q/Z), station_label, file_dfs0
  ledger.json    — toàn bộ, máy đọc (cho GĐ B)
  network_map.png — bản đồ kiểm mắt (nếu --plot)

CÁCH DÙNG:
  python3 src/A_extract_ledger.py --tier 0            # trục chính
  python3 src/A_extract_ledger.py --tier 0 --plot
  python3 src/A_extract_ledger.py --tier max --plot   # tối đa nhánh chạy được

Chạy từ gốc repo (để `from config...` hoạt động):
  cd ~/mekong_telemac_v2 && python3 src/A_extract_ledger.py ...
"""
import argparse
import json
import re
import sys
from collections import defaultdict, deque
from pathlib import Path

# cho phép import config khi chạy từ gốc repo
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config.config import CFG

try:
    import mikeio1d
except Exception:
    mikeio1d = None


# ============================================================================
# PARSE .nwk11  — kế thừa regex đã kiểm chứng từ script 13/14 cũ
# ============================================================================
def parse_nwk11(path):
    """Trả (points, branches). branch: name -> dict(pids, us, ds).
    connection: đầu US cắm (us_branch @ us_ch), đầu DS cắm (ds_branch @ ds_ch)."""
    text = Path(path).read_text(encoding="utf-8", errors="replace")

    points, point_ch = {}, {}
    for m in re.finditer(
        r"point\s*=\s*(\d+)\s*,\s*([\-\d.]+)\s*,\s*([\-\d.]+)\s*,\s*[\-\d.]+\s*,\s*([\-\d.]+)",
        text):
        pid, x, y, ch = m.groups()
        x, y = float(x), float(y)
        # loại điểm placeholder (0,0)/(1,0) và ngoài vùng ĐBSCL
        if CFG.NETF.X_MIN < x < CFG.NETF.X_MAX and abs(y) > 1000:
            points[int(pid)] = (x, y)
            point_ch[int(pid)] = float(ch)

    branches = {}
    for block in re.split(r"\[branch\]", text)[1:]:
        e = block.find("EndSect  // branch")
        bt = block[:e] if e != -1 else block
        dm = re.search(r"definitions\s*=\s*'([^']*)'", bt)
        cm = re.search(
            r"connections\s*=\s*'([^']*)'\s*,\s*([\-\d.]+)\s*,\s*'([^']*)'\s*,\s*([\-\d.]+)", bt)
        pm = re.search(r"points\s*=\s*([\d,\s]+)", bt)
        if not dm:
            continue
        name = dm.group(1)
        pids = [int(p) for p in pm.group(1).split(",") if p.strip()] if pm else []
        us = ds = None
        if cm:
            us = (cm.group(1), float(cm.group(2)))   # (branch cha TL, chainage)
            ds = (cm.group(3), float(cm.group(4)))   # (branch cha HL, chainage)
        is_link = ("[linkchannel]" in bt) or ("[storagearea]" in bt)
        # chainage đầu/cuối đoạn (từ definitions: name, topo, ch_start, ch_end, ...)
        dch = re.search(r"definitions\s*=\s*'[^']*'\s*,\s*'[^']*'\s*,\s*([\-\d.e]+)\s*,\s*([\-\d.e]+)", bt)
        try:
            cs, ce = (float(dch.group(1)), float(dch.group(2))) if dch else (0.0, 0.0)
        except ValueError:
            cs, ce = 0.0, 0.0
        seg = {"pids": pids, "us": us, "ds": ds, "is_link": is_link,
               "ch_start": cs, "ch_end": ce}
        # LƯU NHIỀU ĐOẠN: mỗi tên -> list các đoạn (nhánh chia mảnh giữ đủ)
        branches.setdefault(name, []).append(seg)
    return points, point_ch, branches


# ============================================================================
# PARSE .bnd11 — biên (branch, chainage, station, dfs0)
# ============================================================================
def parse_bnd11(path):
    if not Path(path).exists():
        return []
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    desc = re.compile(
        r"DescType\s*=\s*(\d+)\s*,\s*(\d+)\s*,\s*'([^']*)'\s*,\s*([\-\d.]+)\s*,\s*\d+\s*,\s*'[^']*'\s*,\s*'([^']*)'")
    inflow = re.compile(
        r"Inflow\s*=\s*\d+\s*,\s*[\-\d.]+\s*,\s*[\-\d.]+\s*,\s*\|([^|]*)\|")
    out = []
    for block in re.split(r"\[BndItem\]", text)[1:]:
        e = block.find("EndSect  // BndItem")
        bt = block[:e] if e != -1 else block
        d = desc.search(bt)
        if not d:
            continue
        f = inflow.search(bt)
        out.append({
            "type_code": d.group(1), "branch": d.group(3),
            "chainage": float(d.group(4)), "station": d.group(5),
            "dfs0": (f.group(1) if f else "") or "",
        })
    return out


# ============================================================================
# ĐỌC .xns11 — width trung bình + số mặt cắt mỗi nhánh (mikeio1d)
# ============================================================================
def read_xns_widths(path):
    """Trả {location_id_norm: (width_mean, n_xsec)}. Rỗng nếu thiếu mikeio1d."""
    if mikeio1d is None:
        print("  [!] Thiếu mikeio1d — bỏ qua width/xsec (cần .NET). Cài rồi chạy lại để lọc đúng.")
        return {}
    xns = mikeio1d.open(str(path))
    df = xns.to_dataframe().reset_index()
    agg = defaultdict(list)
    for _, row in df.iterrows():
        loc = norm(str(row["location_id"]))
        try:
            raw = row["cross_section"].raw
            if raw is None or len(raw) < 2:
                continue
            xs = [float(v) for v in raw["x"].values]
            width = max(xs) - min(xs)
            agg[loc].append(width)
        except Exception:
            continue
    return {k: (sum(v) / len(v), len(v)) for k, v in agg.items()}


def norm(s):
    return re.sub(r"[^A-Za-z0-9]", "", str(s)).upper()


# ============================================================================
# TOPOLOGY: BFS thành phần liên thông chứa nhánh thượng lưu
# ============================================================================
def build_adjacency(branches):
    """Đồ thị nhánh-nhánh qua connection MIKE. Trả adj: name -> set(name).
    branches[nm] = list các đoạn; duyệt connection của MỌI đoạn."""
    adj = defaultdict(set)
    names = set(branches)
    for nm, segs in branches.items():
        for seg in segs:
            for conn in (seg["us"], seg["ds"]):
                if conn and conn[0] in names:
                    adj[nm].add(conn[0])
                    adj[conn[0]].add(nm)
    return adj


def connected_component(adj, starts, all_names, blocked=None):
    """BFS từ NHIỀU gốc (starts). Không lan qua nhánh trong blocked (thượng lưu).
    Trả set nhánh liên thông với ít nhất 1 gốc, không đi qua vùng Campuchia."""
    if isinstance(starts, str):
        starts = [starts]
    blocked = set(blocked or [])
    # chuẩn hóa gốc về tên thật
    seeds = []
    for s in starts:
        if s in all_names:
            seeds.append(s)
        else:
            cand = [n for n in all_names if norm(n) == norm(s)]
            if cand:
                seeds.append(cand[0])
    seen = set(seeds)
    dq = deque(seeds)
    while dq:
        u = dq.popleft()
        for v in adj[u]:
            if v not in seen and v not in blocked:
                seen.add(v)
                dq.append(v)
    return seen


# ============================================================================
# CHUẨN HÓA NÚT: gom các đầu nhánh cắm vào cùng (branch cha @ chainage) thành nút
# ============================================================================
def build_nodes(branches, kept, tol):
    """Mỗi nút = một điểm kết nối. Key = (branch_cha, chainage gộp theo tol).
    Trả (node_of_end, nodes): node_of_end[(nhanh,'US'|'DS')] = node_id."""
    # gom tất cả điểm cắm trên mỗi branch cha (từ MỌI đoạn của nhánh giữ)
    cut_points = defaultdict(list)   # branch_cha -> list chainage
    ends = []                        # (nhanh_con, 'US:i'|'DS:i', branch_cha, chainage)
    for nm in kept:
        for i, seg in enumerate(branches[nm]):
            for end, conn in ((f"US:{i}", seg["us"]), (f"DS:{i}", seg["ds"])):
                if conn and conn[0]:
                    cut_points[conn[0]].append(conn[1])
                    ends.append((nm, end, conn[0], conn[1]))

    # gộp chainage gần nhau trên mỗi branch cha -> danh sách mốc nút
    merged = {}
    for cha, chs in cut_points.items():
        chs = sorted(set(chs))
        m = [chs[0]]
        for c in chs[1:]:
            if c - m[-1] > tol:
                m.append(c)
        merged[cha] = m

    def snap(cha, ch):
        for c in merged.get(cha, []):
            if abs(c - ch) <= tol:
                return round(c, 1)
        return round(ch, 1)

    node_key_of_end = {}
    node_members = defaultdict(list)
    for nm, end, cha, ch in ends:
        key = (cha, snap(cha, ch))
        node_key_of_end[(nm, end)] = key
        node_members[key].append((nm, end))

    # đánh số nút
    node_id = {k: i + 1 for i, k in enumerate(sorted(node_members))}
    node_of_end = {e: node_id[k] for e, k in node_key_of_end.items()}
    nodes = {node_id[k]: {"cha_branch": k[0], "chainage": k[1],
                          "members": v} for k, v in node_members.items()}
    return node_of_end, nodes


# ============================================================================
# PHÂN LOẠI GIỮ / BỎ  (topology + width + có mặt cắt), bỏ ô trữ
# ============================================================================
def classify(branches, comp, widths, bnd_branches, tier, survey_branches=None):
    """Trả dict name -> (keep: bool, reason: str).

    tier:
      0    = chỉ trục chính lớn (width>=300 hoặc có biên)
      max  = mọi nhánh có mặt cắt MIKE, width>=WIDTH_MIN
      full = GIỮ MỌI NHÁNH CÓ MẶT CẮT (MIKE 2011 hoặc survey 2020) — toàn mạng
    survey_branches: set nhánh MIKE (norm) có mặt cắt survey chiếu <200m.
    """
    res = {}
    bset = {norm(b) for b in bnd_branches}
    sset = survey_branches or set()
    for nm in branches:
        w, nx = widths.get(norm(nm), (None, 0))
        is_bnd = norm(nm) in bset
        has_survey = norm(nm) in sset
        is_link = all(seg.get("is_link", False) for seg in branches[nm])
        if nm not in comp:
            res[nm] = (False, "ngoai_lien_thong")
            continue
        # linkchannel/storagearea = kênh liên kết / ô trữ nội đồng (DTM/TGLX).
        # Đã kiểm chứng: 100% width<=20m, không có kênh trục. Loại — TRỪ khi có survey.
        if is_link and not has_survey:
            res[nm] = (False, "linkchannel_otru")
            continue
        # ô trữ width lớn (Biển Hồ...): bỏ, TRỪ KHI có survey thật
        if CFG.NETF.DROP_STORAGE and w is not None and w > CFG.NETF.MAX_WIDTH \
                and not has_survey:
            res[nm] = (False, f"o_tru_w={w:.0f}")
            continue

        if tier == "full":
            # GIỮ nếu có mặt cắt (MIKE hoặc survey) hoặc là biên
            if has_survey:
                res[nm] = (True, "co_survey2020")
            elif widths and nx > 0:
                res[nm] = (True, "co_mat_cat_mike")
            elif is_bnd:
                res[nm] = (True, "co_bien")
            elif not widths:  # chưa đọc được xns -> giữ tạm để không mất nhánh
                res[nm] = (True, "giu_tam_chua_co_xns")
            else:
                res[nm] = (False, "khong_co_mat_cat")
            continue

        # tier 0 / max: cần có mặt cắt MIKE (trừ biên)
        if widths and nx == 0 and not is_bnd and not has_survey:
            res[nm] = (False, "khong_co_mat_cat")
            continue
        if tier == 0:
            if is_bnd or has_survey or (w is not None and w >= 300):
                res[nm] = (True, "truc_chinh")
            else:
                res[nm] = (False, "tier0_bo_nhanh_nho")
        else:  # max
            if is_bnd or has_survey or w is None or w >= CFG.NETF.WIDTH_MIN:
                res[nm] = (True, "giu")
            else:
                res[nm] = (False, f"hep_w={w:.0f}")
    return res


# ============================================================================
# XUẤT SỔ CÁI
# ============================================================================
def write_ledger(outdir, branches, kept, keepmap, widths, nodes, node_of_end,
                 bnds, survey_set, points, point_ch):
    outdir.mkdir(parents=True, exist_ok=True)

    # branches.csv
    with open(outdir / "branches.csv", "w", encoding="utf-8") as f:
        f.write("id_moi;ten_mike;giu;ly_do;width_m;n_xsec;us_node;ds_node;"
                "ch_start;ch_end;co_survey2020;so_doan\n")
        for i, nm in enumerate(sorted(branches), 1):
            keep, reason = keepmap[nm]
            w, nx = widths.get(norm(nm), (None, 0))
            segs = branches[nm]
            # nút: lấy đoạn đầu (US của đoạn 0) và đoạn cuối (DS của đoạn cuối)
            usn = node_of_end.get((nm, "US:0"), "")
            dsn = node_of_end.get((nm, f"DS:{len(segs)-1}"), "")
            # chainage: gộp mọi điểm của mọi đoạn
            all_pids = [p for seg in segs for p in seg["pids"]]
            chs = [point_ch[p] for p in all_pids if p in point_ch]
            c0 = f"{min(chs):.0f}" if chs else ""
            c1 = f"{max(chs):.0f}" if chs else ""
            sv = "yes" if norm(nm) in survey_set else "no"
            wtxt = f"{w:.0f}" if w is not None else ""
            nseg = len(segs)
            f.write(f"{i};{nm};{'GIU' if keep else 'bo'};{reason};{wtxt};{nx};"
                    f"{usn};{dsn};{c0};{c1};{sv};{nseg}\n")

    # nodes.csv (chỉ nút của nhánh GIỮ)
    with open(outdir / "nodes.csv", "w", encoding="utf-8") as f:
        f.write("id_nut;cha_branch;chainage;nhanh_noi_vao\n")
        for nid, nd in sorted(nodes.items()):
            mem = [f"{m[0]}:{m[1]}" for m in nd["members"] if m[0] in kept]
            if len(mem) >= 1:
                f.write(f"{nid};{nd['cha_branch']};{nd['chainage']:.1f};"
                        f"{'|'.join(mem)}\n")

    # boundaries.csv
    with open(outdir / "boundaries.csv", "w", encoding="utf-8") as f:
        f.write("branch;chainage;type_code;station_label;dfs0\n")
        for b in bnds:
            f.write(f"{b['branch']};{b['chainage']:.1f};{b['type_code']};"
                    f"{b['station']};{b['dfs0']}\n")

    # ledger.json (cho GĐ B)
    ledger = {
        "machine": CFG.MACHINE,
        "n_branches_total": len(branches),
        "n_kept": len(kept),
        "kept": sorted(kept),
        "nodes": {str(k): {"cha_branch": v["cha_branch"],
                           "chainage": v["chainage"],
                           "members": [list(m) for m in v["members"] if m[0] in kept]}
                  for k, v in nodes.items()},
        "node_of_end": {f"{k[0]}|{k[1]}": v for k, v in node_of_end.items()
                        if k[0] in kept},
        "boundaries": bnds,
    }
    (outdir / "ledger.json").write_text(json.dumps(ledger, ensure_ascii=False,
                                                   indent=1), encoding="utf-8")


def plot_map(outdir, branches, kept, points, keepmap):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        print("  [!] Thiếu matplotlib — bỏ --plot.")
        return
    fig, ax = plt.subplots(figsize=(12, 14))
    for nm, segs in branches.items():
        keep = keepmap[nm][0]
        for seg in segs:
            pl = [points[p] for p in seg["pids"] if p in points]
            if len(pl) < 2:
                continue
            xs, ys = zip(*pl)
            ax.plot(xs, ys, "-", lw=1.1 if keep else 0.4,
                    color="#1f77b4" if keep else "#dddddd",
                    zorder=2 if keep else 1)
    ax.set_title(f"Mạng ĐBSCL — GIỮ={len(kept)} (xanh) / bỏ (xám). Máy={CFG.MACHINE}")
    ax.set_aspect("equal")
    ax.set_xlabel("UTM X"); ax.set_ylabel("UTM Y")
    fig.tight_layout()
    p = outdir / "network_map.png"
    fig.savefig(p, dpi=200)
    print(f"  Bản đồ -> {p}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tier", default="full",
                    help="0=trục chính | max=nhánh lớn có mặt cắt | "
                         "full=MỌI nhánh có mặt cắt MIKE/survey (toàn mạng)")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()
    tier = 0 if str(args.tier) == "0" else ("full" if str(args.tier) == "full" else "max")

    print(f"=== GIAI ĐOẠN A — SỔ CÁI SẠCH (tier={tier}, máy={CFG.MACHINE}) ===")
    print("Kiểm file nguồn:")
    from config.config import _check_paths
    _check_paths()

    print("\n1. Đọc mạng .nwk11...")
    points, point_ch, branches = parse_nwk11(CFG.DATA.NWK11)
    print(f"   {len(branches)} nhánh, {len(points)} điểm hợp lệ (đã loại placeholder/ngoài vùng)")

    print("2. Đọc biên .bnd11...")
    bnds = parse_bnd11(CFG.DATA.BND11)
    bnd_branches = {b["branch"] for b in bnds}
    print(f"   {len(bnds)} biên trên {len(bnd_branches)} nhánh")

    print("3. Đọc mặt cắt .xns11 (width + số mặt cắt)...")
    widths = read_xns_widths(CFG.DATA.XNS11)
    print(f"   {len(widths)} location_id có mặt cắt")

    print("4. Topology — liên thông từ Tân Châu (Tien) + Châu Đốc (BASSAC)...")
    adj = build_adjacency(branches)
    # chặn không lan lên thượng lưu (Kratie/Campuchia)
    blocked = set()
    for nm in branches:
        if any(norm(nm) == norm(b) for b in CFG.NETF.DROP_UPSTREAM):
            blocked.add(nm)
    comp = connected_component(adj, CFG.NETF.UPSTREAM_BRANCHES, set(branches), blocked)
    print(f"   Liên thông từ {CFG.NETF.UPSTREAM_BRANCHES} "
          f"(chặn {len(blocked)} nhánh thượng lưu): {len(comp)} nhánh")

    # nhánh MIKE có mặt cắt survey 2020 chiếu <200m (từ sync_index.csv nếu có)
    survey_branches = set()
    sync_csv = CFG.OUT.ROOT / "data_ref" / "cross_sections" / "sync_index.csv"
    if sync_csv.exists():
        import csv as _csv
        with open(sync_csv, encoding="utf-8") as f:
            for row in _csv.DictReader(f, delimiter=";"):
                try:
                    d = float(row.get("dist_proj_m") or 1e9)
                except ValueError:
                    d = 1e9
                mb = row.get("mike_branch", "")
                if mb and d < 200 and row.get("co_z") == "yes":
                    survey_branches.add(norm(mb))
        print(f"   Nhánh có mặt cắt survey 2020 (<200m): {len(survey_branches)}")
    else:
        print("   [i] chưa có sync_index.csv — chạy sync_sections.py trước để giữ nhánh cù lao có survey")

    print("5. Phân loại GIỮ / BỎ...")
    keepmap = classify(branches, comp, widths, bnd_branches, tier, survey_branches)
    kept = {nm for nm, (k, _) in keepmap.items() if k}
    print(f"   GIỮ {len(kept)} / {len(branches)} nhánh (trước lọc liên thông cuối)")

    # 5b. LỌC LIÊN THÔNG CUỐI: BFS trên tập GIỮ từ Tien/BASSAC.
    #     Nhánh giữ nào không nối tới trục chính (cô lập) -> loại.
    adj_kept = defaultdict(set)
    for nm in kept:
        for seg in branches[nm]:
            for conn in (seg["us"], seg["ds"]):
                if conn and conn[0] in kept:
                    adj_kept[nm].add(conn[0])
                    adj_kept[conn[0]].add(nm)
    seeds = [n for n in kept if norm(n) in (norm("Tien"), norm("BASSAC"))]
    seen = set(seeds)
    dq = deque(seeds)
    while dq:
        u = dq.popleft()
        for v in adj_kept[u]:
            if v not in seen:
                seen.add(v)
                dq.append(v)
    isolated = kept - seen
    for nm in isolated:
        keepmap[nm] = (False, "co_lap_khong_noi_truc")
    kept = seen
    if isolated:
        print(f"   5b. Loại {len(isolated)} nhánh cô lập: {sorted(isolated)[:10]}")
    print(f"   => GIỮ CUỐI: {len(kept)} nhánh")

    reasons = defaultdict(int)
    for nm, (k, r) in keepmap.items():
        if not k:
            reasons[r] += 1
    for r, c in sorted(reasons.items(), key=lambda x: -x[1]):
        print(f"     bỏ [{r}]: {c}")

    print("6. Chuẩn hóa nút...")
    node_of_end, nodes = build_nodes(branches, kept, CFG.NETF.NODE_MERGE_TOL)
    used_nodes = {n for e, n in node_of_end.items() if e[0] in kept}
    print(f"   {len(used_nodes)} nút (của nhánh giữ)")

    # nhánh survey 2020: dò theo tên file Excel nếu thư mục tồn tại
    survey_set = set()
    sdir = CFG.DATA.SURVEY_2020_DIR
    if sdir.exists():
        for xl in sdir.glob("*.xlsx"):
            survey_set.add(norm(xl.stem))
    print(f"7. Survey 2020: {len(survey_set)} file (nếu 0 -> kiểm SURVEY_2020_DIR trong config)")

    print("8. Xuất sổ cái...")
    outdir = CFG.OUT.LEDGER
    write_ledger(outdir, branches, kept, keepmap, widths, nodes, node_of_end,
                 bnds, survey_set, points, point_ch)
    print(f"   -> {outdir}/branches.csv, nodes.csv, boundaries.csv, ledger.json")

    if args.plot:
        print("9. Vẽ bản đồ kiểm mắt...")
        plot_map(outdir, branches, kept, points, keepmap)

    print("\nXONG GĐ A. Mở branches.csv + network_map.png để kiểm mắt.")
    print("Duyệt xong -> chạy GĐ B (B_build_grid.py) để sinh lưới TELEMAC.")


if __name__ == "__main__":
    main()
