#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
config.py — Nguồn chân lý DUY NHẤT cho mọi đường dẫn và tham số của dự án.

Triết lý: repo cũ hardcode đường dẫn rải rác trong ~50 script -> khó sửa, dễ
lệch giữa máy nhà/cơ quan. Bản v2 gom TẤT CẢ vào đây. Mọi script chỉ
`from config.config import CFG` rồi dùng, không tự viết path.

Chỉ cần sửa 1 chỗ (biến MACHINE hoặc BASE) khi đổi máy.
"""
from pathlib import Path
import os

# ============================================================================
# 1. MÁY ĐANG DÙNG — đổi 1 dòng này khi chuyển máy nhà <-> cơ quan
# ============================================================================
# "office" = /mnt/d/OneDrive ; "home" = /mnt/c/Users/win/OneDrive
MACHINE = os.environ.get("MEKONG_MACHINE", "office")

_BASE_BY_MACHINE = {
    "office": "/mnt/d/OneDrive/De Tai/De Tai TELEMAC/MIKE11-DBSCL",
    "home":   "/mnt/c/Users/win/OneDrive/De Tai/De Tai TELEMAC/MIKE11-DBSCL",
}
BASE = Path(_BASE_BY_MACHINE[MACHINE])

# ============================================================================
# 2. FILE DỮ LIỆU NGUỒN MIKE 11  (đọc-chỉ, không bao giờ ghi đè)
# ============================================================================
class _Data:
    # Mạng sông (branch + connection + tọa độ + chainage)
    NWK11 = BASE / "Networks" / "Net_2024.nwk11.nwk11"
    # Mặt cắt 2011 (đọc bằng mikeio1d -> cross_section.raw)
    XNS11 = BASE / "Networks" / "XSecF_2011-update2023.xns11"
    # Biên MIKE (branch + chainage + station_label + đường dẫn .dfs0)
    BND11 = BASE / "Boundary" / "Boundary_2011.bnd11"

    # Survey 2020 thực đo (Excel, format 3 dòng) + shapefile vị trí
    SURVEY_2020_DIR = BASE / "Survey2020"          # thư mục chứa các file Excel *.xlsx
    SURVEY_2020_SHP = BASE / "Survey2020" / "Vi tri MCN.shp"

    # Số liệu thực đo hiệu chỉnh 2011 (Q và mực nước theo giờ)
    Q_OBS  = BASE / "OBS" / "Q" / "Q_theo Gio" / "Q-Observed-for-Calibration-2011.txt"
    WL_OBS = BASE / "OBS" / "Q" / "Q_theo Gio" / "WL-Observed-for-Calibration-2011.txt"

DATA = _Data()

# ============================================================================
# 3. THAM SỐ MASCARET "SỐNG CÒN"  (đã kiểm chứng từ repo cũ — KHÔNG đổi tùy tiện)
# ============================================================================
class _Mascaret:
    OFFSET        = 200_000.0    # 17/07: 1e6 -> 2e5. 423 bief x 1e6 = 422 trieu -> TRAN dinh dang .opt ("**" va "***"). Bief dai nhat 96.7km (paA) / 86.5km (du_k30) < 200km nen KHONG chong lan dai absc (LOI 5 playbook).
    VERSION_CODE  = 3
    CODE          = 2             # REZO (unsteady)
    ABSC_ABSOLU   = True          # profilsAbscAbsolu
    H_EAU_MINI    = 0.005         # hauteurEauMini
    # encoding: geometrie & .opt = latin-1 ; xcas/.loi/init.lig = ascii
    ENC_GEO       = "latin-1"
    ENC_ASCII     = "ascii"
    # thời gian mặc định (giây) — pas 300s như baseline chạy được
    PAS_TEMPS     = 300.0
    PAS_STOCK     = 12
    STRICKLER     = 30.0          # 17/07: K=40 SAI, thi nghiem 7 cau hinh -> 30 tot nhat

MASC = _Mascaret()

# ============================================================================
# 3b. TRẠM THỦY VĂN QUỐC GIA (từ .nwk11: Tân Châu=đầu Tien, Châu Đốc=đầu BASSAC)
#     Dùng làm BIÊN Q thượng lưu + điểm KIỂM ĐỊNH. Tọa độ UTM 48N.
# ============================================================================
class _Stations:
    # (x, y, nhánh MIKE, vai trò)  — role: 'bien_Q' | 'kiem_dinh'
    TanChau = (520477, 1206257, "Tien",   "bien_Q")     # đầu Tien, ch=0
    ChauDoc = (509000, 1211161, "BASSAC", "bien_Q")     # đầu BASSAC, ch=0
    VamNao  = (537000, 1175000, "VamNao", "kiem_dinh")
    MyThuan = (580000, 1148000, "Tien",   "kiem_dinh")
    CanTho  = (585000, 1105000, "BASSAC", "kiem_dinh")
    # cột số liệu tương ứng trong Q_OBS / WL_OBS
    Q_COLS  = {"TanChau": "Q_TanChau", "ChauDoc": "Q_ChauDoc"}
STA = _Stations()

# ============================================================================
# 4. THAM SỐ LỌC MẠNG (topology — không lọc theo tên)
# ============================================================================
class _NetFilter:
    # Gốc BFS = 2 nhánh bắt đầu tại trạm Tân Châu (đầu Tien) + Châu Đốc (đầu BASSAC).
    # Cắt bỏ toàn bộ phía thượng lưu (Kratie/Campuchia) vì gán biên Q tại đây.
    UPSTREAM_BRANCHES = ["Tien", "BASSAC"]
    UPSTREAM_BRANCH = "Tien"        # tương thích ngược (dùng phần tử đầu)
    # Nhánh NGOÀI VÙNG NGHIÊN CỨU — loại thẳng.
    # 17/07: đối chiếu 124 biên của `--subset full` với Boundary_2011.bnd11
    # (1709 BndItem) → 24 biên không có số liệu. Rà ra: 15 nhánh Cam*
    # (Campuchia — bản cũ chỉ bắt MekongCam/BassacCam, SÓT Cam6..Cam49)
    # + 11 nhánh Sài Gòn/Đồng Nai/Vàm Cỏ (ngoài ĐBSCL).
    #
    # ⚠ VÀM CỎ: `Vam Co`, `Vam Co Dong`, `Vam Co Tay` NHẬN NƯỚC TỪ ĐỒNG THÁP
    #   MƯỜI. Bỏ hẳn → mất đường thoát của ĐTM. Nhưng WL_OBS CÓ `H_TanAn`,
    #   `H_BenLuc` (trên Vàm Cỏ) → vẫn gán biên được nếu muốn giữ.
    #   → Tạm bỏ để tập trung vùng nghiên cứu. KHI LÀM ĐTM PHẢI CÂN NHẮC LẠI.
    DROP_UPSTREAM = [
        # --- Campuchia / thượng lưu Tân Châu–Châu Đốc ---
        "MekongCam", "BassacCam", "BASSACCam", "Tonle_Sap",
        "GREATLAKE", "Mkampoul_s", "Stung-Takaev",
        "Cam6", "Cam7", "Cam8", "Cam30", "Cam31", "Cam32", "Cam33", "Cam34",
        "Cam35", "Cam36", "Cam37", "Cam38", "Cam39", "Cam42", "Cam49",
        # --- Sài Gòn – Đồng Nai (ngoài ĐBSCL) ---
        # 17/07: hình 5b_network_clean cho thấy East Vaico chạy lên Y=1.30M
        # (bắc Tây Ninh) — ngoài ĐBSCL. Rà thêm 12 nhánh Sài Gòn.
        "Dong Nai", "Sai Gon", "Vinh Cuu", "K. LONG TAU", "R.PHUOC KIENG",
        "Can Giuoc", "Song Kinh",
        "East Vaico", "R. BEN NGHE", "R. BEN NGHE1", "S.BenCat",
        "R.NhanhCanGiuoc2", "R.NhanhCanGiuoc5", "R.NhanhCanGiuoc5_1",
        "R.NhanhCanGiuoc5_2", "R.NhanhCanGiuoc5_3", "S.NhanhCanGiuoc1",
        "RachTra_1", "RachTra_2", "RACHTRAQUAN", "ThayCaiRachTra",
        "KENHTHAYCAI", "KENHTHAYCAI1",
        # --- Vàm Cỏ: GIỮ LẠI (thử bỏ 17/07 → biên 124→155 vì 30+ kênh ĐTM
        #     (Thu_Thua, kenhLA285..508, T3..T8, KENHTG1) thành cụt).
        #     WL_OBS có H_TanAn, H_BenLuc trên Vàm Cỏ → gán biên được. ---
        # "Vam Co", "Vam Co Dong", "Vam Co Tay", "East Vaico",
        # --- khác ---
        "SongBinhDi",
        # --- RANH DONG BAC: Vam Co Tay lam ranh (18/07) ---
        # dong/bac Vam Co Tay = Long An/HCM/Campuchia/Soai Rap. Giu Vam Co
        # Dong/Tay + Cho Gao (Tien) + champeaix (CuaTieu). 0 co lap.
        "Ba Hong Minh", "Binh Trung", "Ca Dua", "Cau An Ha", "Cay Kho Lon",
        "Cay Kho Nho", "K. Dong Tranh", "K. SO 1", "K. SO 2", "K.AnHa",
        "K.Baty", "K.CongXang1", "K.CongXang2", "K.CongXang3",
        "K.CongXang4", "K.DamLay2_2", "K.NamDong", "K.ThamLuong",
        "K.XangBinhChanh", "K.XangLVM", "Kenh19T5", "Kenh3", "KenhA",
        "KenhB", "KenhC", "KenhDoi", "KenhNgang", "KenhNgang1", "MocKeo",
        "MocKeoLon", "Nam Hang", "R. DONG TRANH 1", "R.BaGoc",
        "R.HungNhon", "R.Ngua", "Rach Coc", "Rach Goc", "RachLa",
        "S. BL K DOI", "S. DM BKY", "S.Dua 2", "S.NGA BAY",
        "S.NhanhBenLuc1", "S.NhanhChoDem", "SONGTHI VAI", "T2", "T4", "T6",
        "T8", "TacOngNghia", "TayDen", "Truc Chinh", "VamThuat",
        "kenhLA579", "kenhLA580",
    ]
    WIDTH_MIN       = 50.0          # m — kênh hẹp hơn bị loại (trừ nhánh có biên)
    MAX_WIDTH       = 3000.0        # m — rộng hơn = ô trữ (Biển Hồ) -> loại
    SPLIT_TOL       = 500.0         # m — dung sai cắt nhánh cha tại junction
    NODE_MERGE_TOL  = 60.0          # m — gộp 2 điểm cắt gần nhau thành 1 nút
    # vùng ĐBSCL (lọc điểm placeholder + ngoài vùng): UTM zone 48N
    X_MIN, X_MAX    = 430000, 720000
    # bỏ ô trữ hoàn toàn (quyết định dự án)
    DROP_STORAGE    = True

NETF = _NetFilter()

# ============================================================================
# 5. QC HÌNH HỌC — ngưỡng so mặt cắt mô hình vs thực đo
# ============================================================================
class _QC:
    AWET_MIN_RATIO  = 0.90    # diện tích ướt mô hình >= 90% thực đo
    BANK_TOL_M      = 1.0     # sai lệch cao độ bờ trái/phải cho phép (m)
    BED_TOL_M       = 1.0     # sai lệch cao độ đáy cho phép (m)
    # mực nước tham chiếu để tính A_wet khi QC (m, theo hệ cao độ thực đo)
    QC_WATER_LEVEL  = 1.5

QC = _QC()

# ============================================================================
# 6. THƯ MỤC OUTPUT (trong repo, không đụng data nguồn)
# ============================================================================
class _Out:
    ROOT       = Path(__file__).resolve().parent.parent   # gốc repo
    OUTPUT     = ROOT / "output"
    LEDGER     = OUTPUT / "ledger"        # Giai đoạn A: sổ cái sạch
    GRID       = OUTPUT / "grid"          # Giai đoạn B: lưới TELEMAC
    GEOM_QC    = OUTPUT / "geom_qc"       # Giai đoạn C: mặt cắt + QC
    RUN        = OUTPUT / "run"           # Giai đoạn D: chạy + eval
    DOCS       = ROOT / "docs"

OUT = _Out()


class CFG:
    """Gom tất cả để import 1 dòng: from config.config import CFG"""
    MACHINE = MACHINE
    BASE = BASE
    DATA = DATA
    MASC = MASC
    NETF = NETF
    STA = STA
    QC = QC
    OUT = OUT


def _check_paths(verbose=True):
    """Kiểm nhanh file nguồn có tồn tại không (chạy đầu mỗi phiên)."""
    items = [("NWK11", DATA.NWK11), ("XNS11", DATA.XNS11), ("BND11", DATA.BND11),
             ("Q_OBS", DATA.Q_OBS), ("WL_OBS", DATA.WL_OBS)]
    ok = True
    for name, p in items:
        exists = p.exists()
        ok = ok and exists
        if verbose:
            mark = "OK " if exists else "!! THIEU"
            print(f"  [{mark}] {name:8s} {p}")
    return ok


if __name__ == "__main__":
    print(f"MÁY: {MACHINE}  |  BASE: {BASE}")
    print("Kiểm tra file nguồn:")
    ok = _check_paths()
    print("=> " + ("Đủ file nguồn." if ok else "THIẾU file — sửa config.py hoặc MEKONG_MACHINE."))
