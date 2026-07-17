# TRẠNG THÁI PIPELINE

> Cập nhật: **17/07/2026** (phiên 3). Tag: `v2.0-baseline`
> **ĐỌC `docs/BAT_DAU_PHIEN_MOI_V2.md` TRƯỚC KHI LÀM BẤT CỨ GÌ.**

---

## BASELINE HIỆN TẠI — `truc_du` + K=30

**22 nhánh → 47 bief | 28 nút | 9 biên | 224 mặt cắt | 41s/30 ngày**
Mặt cắt: survey 2020 = MIKE topo `2021_SIWRP_QHPCTT` (đã kiểm: 36/36 đáy lệch 0.00m)

| Trạm | WL_NSE | WL_KGE | Q_NSE | Q_KGE |
|---|---|---|---|---|
| TanChau | −11.981 | **+0.319** | 0.893 | **0.917** |
| ChauDoc | −170.666 | −0.326 | 0.851 | **0.920** |
| VamNao | — | — | −114.491 | **0.481** |
| MyThuan | 0.141 | **0.653** | −0.667 | **0.671** |
| CanTho | −4.008 | 0.291 | 0.125 | 0.488 |

**Froude max 0.983** — tại `Hau_1` (rộng 197m). Là **hình học**, không đổi theo K
(đã thử K=20/25/30/38/40 → Fr y hệt 0.983). Fr<1 nên vẫn dưới tới hạn.

**Gói tái tạo:** `runs/RUN_baseline_truc_du_K30/` → `bash RUN.sh` (41s)
**Thư mục làm việc:** `output/grid/du_k30/`

---

## ⚠️ BA QUY TẮC SỐNG CÒN (quên là mất 1 phiên)

1. **`--eval-start 2011-10-08`** — bỏ 7 ngày warm-up → n=553.
   Quên → n=721, mọi chỉ số tụt (TanChau Q 0.917→0.527) và **trông y như hỏng**.
2. **Chạy đủ 30 ngày.** Đã thử 5d/12d cho nhanh → KGE méo hoàn toàn,
   không đơn điệu (VamNao: 5d −7.98 | 12d −15.50 | 30d −2.50). Không rút ngắn được.
3. **`--slope` của `C_init_smart` phụ thuộc số bief.**
   Quy tắc: `z_sea + slope × d_cua_max ≈ 9m`.
   15 bief → 2.0 | 47 bief → **0.55** | 82 bief → 0.55

---

## Xong

- [x] **GĐ A — sổ cái mạng**: 1899 nhánh, liên thông 1899/1899, 3166 nút.
      Đã rà soát 2 lần: ĐÚNG, không dựng lại.
- [x] Giải mã cách đặt tên MIKE (phiên 2) — xem `BAT_DAU_PHIEN_MOI_V2.md` §3
- [x] Bảng tra cứu `build_catalog.py` + `F_catalog_3nguon.py` (đối chiếu 3 nguồn)
- [x] **GĐ B — sinh lưới**: `--subset backbone(11) / truc_du(22) / truc(34) / full44(44)`
      Đóng bao phụ thuộc tự kiểm, cảnh báo bief lăng trụ
- [x] **GĐ D — NSE/KGE tại 5 trạm**
- [x] Chốt tọa độ 5 trạm — **ĐÃ DÒ CẠN, ĐỪNG TÌM LẠI** (`SESSION_LOG.md` phiên 2B §2)
- [x] **Chốt K=30** (`config.py:STRICKLER`). K=40 cũ SAI — xem §"Bài học" dưới.
- [x] Đóng gói 2 baseline trong `runs/`

## Đang làm

- [ ] **Thêm kênh trục theo vùng** — xem "Hướng tiếp theo" dưới

## Chưa làm

- [ ] Sửa `vn_norm` trong `import_data.py`, `sync_sections.py`, `A_extract_ledger.py`
      (KHÔNG chặn đường chạy — `B_build_grid` đọc thẳng `.xns11`)
- [ ] Sửa `parse_name` trong `sync_sections.py`: CT/CĐ = cửa, không phải nhanh_phu
- [ ] GĐ C — QC mặt cắt (A_wet≥90%, bờ/đáy ±1m)
- [ ] Tích hợp ML dự báo SSC (dùng đầu ra thủy lực làm feature)

---

## BÀI HỌC LỚN NHẤT PHIÊN 3 — bảng thí nghiệm 7 cấu hình

**VamNao Q_KGE** (30 ngày, n=553):

| Lưới | K=40 | K=30 | K=25 | K phân bố |
|---|---|---|---|---|
| `backbone` 15 bief | 0.301 | 0.523 | 0.533 | — |
| `truc_du` 47 bief | −0.618 | **0.481** | 0.615 | 0.423 |
| `truc` 82 bief | −2.503 | −0.218 | — | — |

**Đọc bảng:** hàng = ảnh hưởng lăng trụ (cùng K) | cột = ảnh hưởng K (cùng lưới)

### 1. K=40 SAI ở mọi lưới
Nước thoát quá dễ → WL thượng lưu thấp 2m → không đủ cột nước đẩy qua Vàm Nao
→ phân lưu thiếu 45%. **Một gốc, hai triệu chứng** ("tồn tại 1" + "tồn tại 2"
phiên 2 là cùng nguyên nhân). → Đã đổi `config.py` K=40 → **30**.

### 2. 10 nhánh LĂNG TRỤ phá phân lưu — độc lập với K
Nhánh 1 mặt cắt → `build_geometrie` nhân đôi → tiết diện không đổi 4–10km.
Cùng K=30: 47 bief **+0.481** vs 82 bief **−0.218**.
Danh sách: `Tien_1, Tien_5, Tien_6, Tien_8, Hau_2, Hau_3, Hau_5, Hau_6, Hau_9, CuaDai_3`

### 3. K phân bố theo BỀ RỘNG — THẤT BẠI
Giả thuyết "kênh hẹp cần K thấp" → thử (20/25/30/38 theo bề rộng) → **thua K=30
đồng nhất ở 5/7 chỉ số** (VamNao 0.423 vs 0.481). Và **Froude không đổi** (0.983).
→ Dữ liệu nói phải phân theo **vị trí dọc sông** (thượng lưu K25, cửa K38),
không phải bề rộng. Chưa thử.

### 4. Xu thế: thêm nhánh → WL tốt, Q xấu
Cù lao mở thêm đường thoát → dung tích trữ tăng → triều hạ lưu đúng hơn
(CanTho WL_NSE −2.29 → +0.31). Nhưng chia bớt nước khỏi Vàm Nao → phân lưu giảm.

---

## HƯỚNG TIẾP THEO — thêm kênh trục theo vùng

**Nguyên tắc:** mỗi vùng FIN CORRECTE mới thêm vùng sau. Bắt đầu từ `truc_du` K30.

| # | Vùng | Nối | Trạm kiểm định có sẵn trong `WL_OBS` |
|---|---|---|---|
| 1 | **Tứ giác Long Xuyên** | Hậu → biển Tây | H_XuanTo, H_TriTon, H_TanHiep, H_RachGia |
| 2 | **Đồng Tháp Mười** | Tiền → Vàm Cỏ | H_MocHoa, H_TuyenNhon, H_KienBinh, H_TruongXuan |
| 3 | **Tây Nam Sông Hậu** | Hậu → biển Tây | H_ViThanh, H_PhungHiep, H_XeoRo |
| 4 | **Nam Măng Thít** | Cổ Chiên ↔ Hậu | H_TraVinh |
| 5 | **Bán đảo Cà Mau** | — | H_CaMau, H_PhuocLong, H_GanhHao, H_SongDoc |

**Vì sao TGLX trước:** nối Hậu→biển Tây, ảnh hưởng trực tiếp phân lưu tại Châu Đốc
— nơi WL_KGE tệ nhất (−0.326).

**Lợi ích:** 34 cột `WL_OBS` hiện chỉ dùng 7 → thêm kênh trục mở ra **~20 trạm
kiểm định** nữa, đánh giá chặt hơn nhiều.

**Cách làm:** thêm `CL_TGLX = [...]` vào `SUBSETS` trong `B_build_grid.py`,
tra tên nhánh từ `output/ledger/branches.csv` (1899 nhánh, đã lọc linkchannel).
**Kiểm đóng bao trước khi chạy** — script tự báo liên kết ra ngoài subset.

**Tốc độ:** 41s/47 bief. Thêm 5 vùng → có thể 300–500 bief.
Nghẽn KHÔNG phải MASCARET mà là `D_run_eval` (đọc 1.09M dòng lấy 3605).
Khi đó mới tối ưu — cẩn thận: `D_run_eval` đọc `.opt` theo **chỉ số cột cố định**
(`C_Z=5`, `C_Q=13`), đổi `variablesStockees` là lệch hết.

---

## Ghi chú

Baseline V1 (`_archive_2026-07-14/`) chỉ để học FORMAT. Nó FIN CORRECTE được là do
`24f_smooth_geometry.py` **hạ đáy >10m — SAI VẬT LÝ**, và map MyThuan sai chỗ 26km.
KHÔNG lấy thông số.
