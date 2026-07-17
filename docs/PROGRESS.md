# TRẠNG THÁI PIPELINE

> Cập nhật: **17/07/2026**. V2 **ĐÃ CHẠY THÔNG** (16/07/2026).
> Baseline đã tái lập và xác minh lại ngày 17/07 — trùng khít từng số.

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
- [x] **GĐ B — sinh lưới: XONG.** `get_cross_sections` khớp tên CHÍNH XÁC +
      lọc topo (2021_SIWRP_QHPCTT, bỏ 2006) → hết răng cưa → hết lỗi 701.
- [x] **GĐ D — chạy MASCARET + NSE/KGE tại 5 trạm: XONG.**
- [x] **Chốt tọa độ 5 trạm** — xem SESSION_LOG.md phiên 2B §2. Đã dò cạn.
- [x] Đóng gói `runs/RUN_baseline_2020_15bief/` — chạy lại 35s bằng `bash RUN.sh`

## Baseline hiện tại — `output/grid/backbone`

**15 bief | 176 PROFIL | 7 nút | 9 biên | 34.9s/30 ngày | Froude max 0.525**
Mặt cắt: survey 2020 / MIKE topo `2021_SIWRP_QHPCTT` — **không hạ đáy**.

| Trạm | WL_NSE | WL_KGE | Q_NSE | Q_KGE |
|---|---|---|---|---|
| TanChau | −103.610 | −0.647 | +0.564 | **0.706** |
| ChauDoc | −34.014 | −1.499 | +0.566 | **0.737** |
| VamNao | — | — | −169.784 | 0.301 |
| MyThuan | **+0.630** | **0.580** | −0.825 | 0.432 |
| CanTho | −2.287 | 0.433 | −0.136 | 0.607 |

> ⚠️ **BẮT BUỘC `--eval-start 2011-10-08`** (bỏ 7 ngày warm-up) → n=553.
> Quên cờ này → n=721, mọi chỉ số tụt mạnh (TanChau Q_KGE 0.706→0.527,
> WL_NSE −103.6→−115.8) và **trông như mô hình hỏng**. Không phải. Đó là
> warm-up. Đã mất 1 phiên vì chuyện này.

## Tồn tại (ưu tiên phiên sau)

1. **Vàm Nao thiếu 45% lưu lượng** — sim ~6000 vs thực đo ~11000 m³/s,
   Q_NSE=−170 nhưng Q_KGE=+0.30 → **dạng đúng, mức sai**. Phân lưu Tiền→Hậu
   quá ít. Chỉ 6 mặt cắt/23km (KC 3.9km). → Thêm mặt cắt survey 2020 (có 5),
   hoặc kiểm hình học Vàm Nao.
2. **WL thấp hệ thống ~1.7m** tại TanChau/ChauDoc — WL_NSE −103.6/−34.0 nhưng
   WL_KGE −0.65/−1.50 → dạng đúng, lệch mức. Nghi datum hoặc Strickler=40.
3. **Bief_1 (BASSAC) trắc dọc dốc 7m/30km** — quá lớn, liên quan mặt cắt hẹp
   164–560m đoạn đầu. Có thể là gốc của tồn tại 2 (Châu Đốc WL_KGE tệ nhất).
4. **Mở rộng BACKBONE 11 → 44 nhánh** (33 cù lao có survey 2020).
   Phân tầng: tien(~17) → hau(~12) → truc(~24) → full(44).
   Mỗi tầng phải FIN CORRECTE mới lên tầng sau.

## Chưa làm

- [ ] Sửa `vn_norm` trong `import_data.py`, `sync_sections.py`, `A_extract_ledger.py`
      (không chặn đường chạy — `B_build_grid` đọc thẳng `.xns11`, không qua chúng)
- [ ] Sửa `parse_name` trong `sync_sections.py`: CT/CĐ = cửa, không phải nhanh_phu
- [ ] Thêm `--subset tien/hau/truc` vào `B_build_grid.py`
- [ ] GĐ C — QC mặt cắt (A_wet≥90%, bờ/đáy ±1m)
- [ ] Mở rộng kênh trục toàn ĐBSCL
- [ ] Tích hợp ML dự báo SSC (dùng đầu ra thủy lực làm feature)

## Ghi chú

Baseline V1 (KGE MyThuan 0.84) chạy được là do `24f_smooth_geometry.py`
hạ đáy >10m — **SAI VẬT LÝ**. V1 chỉ để học FORMAT, không lấy thông số.
V1 còn map MyThuan sai chỗ (cách cầu thật 26km) → 0.84 là con số sai chỗ.
