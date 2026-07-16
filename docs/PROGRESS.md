# TRẠNG THÁI PIPELINE

## Xong
- [x] Khung repo + config (đường dẫn, tham số, trạm thủy văn)
- [x] **GĐ A — sổ cái mạng**: 1899 nhánh, liên thông 1899/1899, cắt TC/CĐ,
      lọc linkchannel. **Đã rà soát phiên 2: ĐÚNG, không cần dựng lại.**
- [x] Đồng bộ mặt cắt survey 2020 ↔ MIKE (tọa độ)
- [x] Kho dữ liệu data_ref (mặt cắt + biên Q/WL)
- [x] Rà soát toàn diện (audit) + sửa lỗi ghi đè nhánh chia mảnh
- [x] **Giải mã cách đặt tên MIKE** (phiên 2) — xem BAT_DAU_PHIEN_MOI_V2.md §3
- [x] **Bảng tra cứu** `build_catalog.py` → data_ref/catalog/
      229 điểm shp, 212 Excel z, khớp 201, 245 tuyến ADCP, 11098 mặt cắt MIKE
- [x] **Xác định 44 nhánh có survey 2020** (11 chính + 33 cù lao, 1077km, 197 mặt cắt)
- [x] Sửa B_build_grid: variablesStockees 41→42, planim nbZones 1→nb_bief
- [x] C_assign_boundaries.py — gán biên thực đo 2011
- [x] C_init_smart.py — Z init theo BFS topology
- [x] 3 script vẽ: B_plot_grid / B_plot_network / B_plot_proposed

## Đang làm
- [ ] **GĐ B — sinh lưới**: `get_cross_sections` đang TRỘN topo 2006+2021
      → bề rộng răng cưa 164↔3481m → lỗi 701 supercritical tại Q_ChauDoc
      → PHẢI SỬA: khớp tên chính xác + lọc topo + ưu tiên survey 2020

## Chưa làm
- [ ] Sửa vn_norm trong import_data / sync_sections / A_extract_ledger
- [ ] Sửa parse_name: CT/CĐ = cửa, không phải nhanh_phu
- [ ] Mở rộng BACKBONE 11 → 44 nhánh, thêm --subset tien/hau/truc
- [ ] Chạy tầng tien → hau → truc → full (mỗi tầng FIN CORRECTE mới lên)
- [ ] GĐ C — QC mặt cắt (A_wet≥90%, bờ/đáy ±1m)
- [ ] GĐ D — chạy MASCARET + NSE/KGE tại 5 trạm
- [ ] Mở rộng kênh trục toàn ĐBSCL

## Ghi chú
V2 CHƯA BAO GIỜ chạy thông. Baseline V1 (KGE MyThuan 0.84) chạy được là do
24f hạ đáy >10m — SAI VẬT LÝ. V1 chỉ để học format, không lấy thông số.
