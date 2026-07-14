#!/usr/bin/env bash
# ============================================================================
# run_all.sh — Chạy TOÀN BỘ pipeline v2 đúng thứ tự (khôi phục kết quả phiên trước)
# ============================================================================
# Xử lý vòng phụ thuộc: GĐ A (tier full) cần sync_index.csv, mà sync cần ledger.
# Giải: chạy A lần 1 (chưa sync) -> sync -> A lần 2 (có sync) -> import -> audit.
#
# DÙNG:  bash run_all.sh
# (tự dùng python của venv có mikeio1d)
# ============================================================================
set -e   # dừng ngay nếu có bước lỗi

cd ~/mekong_telemac_v2
PY=~/TELEMAC_1D_MEKONG/.venv/bin/python

echo "############################################################"
echo "# BƯỚC 0: Kiểm đường dẫn dữ liệu nguồn"
echo "############################################################"
$PY -m config.config

echo ""
echo "############################################################"
echo "# BƯỚC 1: GĐ A lần 1 — sổ cái theo mặt cắt MIKE (chưa có sync)"
echo "############################################################"
$PY src/A_extract_ledger.py --tier full

echo ""
echo "############################################################"
echo "# BƯỚC 2: Đồng bộ mặt cắt survey <-> MIKE (tạo sync_index.csv)"
echo "############################################################"
$PY src/sync_sections.py --use-ledger --plot

echo ""
echo "############################################################"
echo "# BƯỚC 3: GĐ A lần 2 — giờ có sync, giữ thêm nhánh cù lao có survey"
echo "############################################################"
$PY src/A_extract_ledger.py --tier full --plot

echo ""
echo "############################################################"
echo "# BƯỚC 4: Build kho dữ liệu (mặt cắt chuẩn hóa + biên Q/WL)"
echo "############################################################"
$PY src/import_data.py --plot

echo ""
echo "############################################################"
echo "# BƯỚC 5: Rà soát toàn diện mạng (kênh loại, chia mảnh, liên thông)"
echo "############################################################"
$PY src/audit_network.py

echo ""
echo "############################################################"
echo "# XONG TOÀN BỘ. Kết quả:"
echo "############################################################"
echo "  Sổ cái:    output/ledger/branches.csv, nodes.csv, boundaries.csv"
echo "  Bản đồ:    output/ledger/network_map.png"
echo "  Kho data:  data_ref/cross_sections/index.csv, sync_index.csv"
echo "  Rà soát:   output/audit/removed_map.png, connectivity_map.png, fragmented.csv"
echo ""
echo "  Tóm tắt nhanh:"
echo -n "    Nhánh GIỮ: "; grep -c ";GIU;" output/ledger/branches.csv
echo -n "    Nhánh bỏ:  "; grep -c ";bo;"  output/ledger/branches.csv
echo "    Lý do giữ:"
awk -F';' '$3=="GIU"{print "      "$4}' output/ledger/branches.csv | sort | uniq -c | sort -rn
