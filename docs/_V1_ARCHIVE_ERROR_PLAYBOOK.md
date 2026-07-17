# SỔ TAY LỖI (ERROR PLAYBOOK) — TELEMAC-1D Mekong

> ⚠️ **ĐÂY LÀ PLAYBOOK CỦA V1 — ĐỌC ĐỂ THAM KHẢO, KHÔNG ÁP DỤNG MÙ CHO V2.**
> V2 dùng mặt cắt THỰC ĐO 2020, không được biến dạng hình học.
> **HAI MỤC SAU KHÔNG ÁP DỤNG CHO V2:**
> - **LỖI 6** (làm mượt bằng dịch đứng mặt cắt) — chính là `24f_smooth_geometry.py`,
>   nó hạ đáy lòng sông >10m để V1 chạy thông. SAI VẬT LÝ. V2 cấm.
> - **LỖI 9** (dùng `norm()` xóa mọi ký tự đặc biệt) — chính là BẪY #2 của V2:
>   `norm()` gộp `CO CHIEN`(topo 2006) + `COCHIEN`(topo 2021) thành một
>   → bề rộng răng cưa 164↔3481m → lỗi 701. V2 phải khớp tên CHÍNH XÁC.
> Xem `BAT_DAU_PHIEN_MOI_V2.md` §3 và §7.

> Tra cứu nhanh khi gặp lỗi. Mỗi mục: **triệu chứng → nguyên nhân gốc → giải pháp đã chứng minh → script liên quan**. Đọc kèm phần E của `00_README_PROJECT_HANDBOOK.md`.

---

## LỖI 1 — Bản đồ vẽ ra "chụm/tỏa hình quạt" về điểm (0,0)
- **Nguyên nhân:** File `.nwk11` chứa các điểm placeholder kỹ thuật có tọa độ ~(1.0, 0.0) — không phải điểm thật.
- **Giải pháp:** Khi parse, **loại bỏ mọi điểm có `x < 1000` và `y < 1000`**.
- **Script:** 09, 09b_diagnose_points_issue.py.

## LỖI 2 — Đứt gãy / sai lệch topology mạng lưới (node treo, 1147 đầu mút tự do)
- **Nguyên nhân:** MIKE cho nhánh con cắm vào **giữa** nhánh cha tại một chainage bất kỳ (khai báo một chiều); tọa độ 2 đầu KHÔNG trùng nhau, nên "snap theo tọa độ X,Y" bị sai. TELEMAC không cho node treo giữa nhánh.
- **Giải pháp:** Dùng **Union-Find trên connection gốc MIKE + chainage** (không snap mù). **Cắt (split) nhánh cha tại đúng chainage** mà nhánh con cắm vào (tolerance ~500 m) để tạo node liên thông.
- **Script:** 13_refine_and_snap_network.py, 14_split_branches_at_junctions.py.

## LỖI 3 — Bỏ sót nhánh quan trọng (Bassac, cửa Định An, Trần Đề)
- **Nguyên nhân:** Lọc nhánh **theo tên** — tên MIKE đặt tùy tiện, không đồng nhất.
- **Giải pháp:** Chuyển sang **lọc theo topology (BFS/DFS)**: giữ nhánh nằm trên đường dẫn nước nối biên thượng lưu ↔ hạ lưu; kết hợp chiều rộng mặt cắt + có cross-section thật. Bổ sung cửa biển bằng cách quét các biên H trong `.bnd11`.
- **Script:** 10, 11_extract_downstream_boundaries.py, 12_build_network_by_topology.py.

## LỖI 4 — Ô ngập lũ khổng lồ (Biển Hồ / Tonle Sap) làm 1D không giải nổi
- **Nguyên nhân:** MIKE khai cả ô trữ (storage cell) Campuchia — không phải lòng sông.
- **Giải pháp:** Loại nhánh có `width > max-width` (mặc định 3000 m), nằm ngoài vùng ĐBSCL theo tọa độ Y, và các sông ngoài vùng (Campuchia, Sài Gòn–Đồng Nai).
- **Script:** 13, 45_filter_dbscl.py.

## LỖI 5 — MASCARET báo "abscissa out of bounds" / nhầm mặt cắt giữa các bief
- **Nguyên nhân:** Nhiều bief có dải abscissa **chồng lấn** (đều bắt đầu từ 0); với `profilsAbscAbsolu=true`, MASCARET nội suy nhầm mặt cắt giữa các nhánh.
- **Giải pháp:** Cộng **OFFSET = (bief−1) × 1.000.000** vào abscissa mỗi bief → mỗi bief có dải tọa độ 1D riêng biệt. Khi đọc kết quả để map trạm, đảo lại: `chainage_gốc = absc − (bief−1)×OFFSET + chmin`.
- **Script:** 23, 24, 26 (học từ example Test23).

## LỖI 6 — "is dry" / "supercritical flow" ⚠️ GIẢI PHÁP NÀY V2 CẤM DÙNG
- **Nguyên nhân:** Mặt cắt bị **co thắt cục bộ** (phình/thắt đột ngột → tăng tốc dòng, Froude>1) hoặc **đáy nhảy bậc** giữa 2 mặt cắt kề.
- **Giải pháp (2 lớp):**
  - Loại/thay mặt cắt có `width > 3× width lân cận` (24f phát hiện, 26/31 loại co thắt).
  - **Làm mượt đáy:** nếu đáy mặt cắt i cao hơn nội suy tuyến tính từ đáy[i−1],[i+1] quá ngưỡng (`--threshold 2.0` m), **dịch đứng toàn bộ mặt cắt xuống** (giữ nguyên hình dạng, chỉ triệt gồ). Với survey 2020: `--max-bed-drop 6.0` m, `--width-factor 3.0`.
- **Script:** 24f_smooth_geometry.py, 31_apply_survey_2020.py. Kiểm chứng: 24g.

## LỖI 7 — Khô đáy ngay bước khởi tạo (init.lig)
- **Nguyên nhân:** Init mực nước **phẳng** (VD 3m) trong khi đáy sông Tiền sâu tới −25m, hoặc mặt cắt mới có đáy cao hơn mực nước cũ → điểm khô ở bước thời gian đầu.
- **Giải pháp (Smart Init, script 70):**
  - Sông chính: `z = max(init_high − frac×(init_high−init_low), bed + 5.0)` — dốc 9m→3m + **sàn đáy +5m**.
  - Cửa: `z = max(bed + 4.0, cua_floor)`, giới hạn `≤ cua_level`.
- **Script:** 70_run_model.py (hàm `smart_init`). ⚠ `rebuild_init_lig` trong 24d2 chỉ tạo Z/Q phẳng (dùng cho test biên).

## LỖI 8 — Mực nước Tân Châu cao bất thường (~18 m) ở mô hình 1 nhánh
- **Nguyên nhân:** Sông Tiền đơn nhánh nhận **toàn bộ** tải Kratie, không phân lưu sang Hậu qua Vàm Nào. (Triệu chứng liên quan: Vàm Nào chỉ ~330 m³/s vs thực đo ~11.000 m³/s.)
- **Giải pháp:** Dựng mạng **2 sông + Vàm Nào** (cắt Tien@32675 ↔ BASSAC@71252), buộc **chênh cột nước đúng** giữa 2 sông → chia tải tự nhiên.
- **Script:** 24_build_tien_vamnao_hau.py → 24b (backbone).

## LỖI 9 — Không tìm thấy nhánh trong `.xns11` ⚠️ norm() LÀ BẪY, V2 DÙNG vn_norm()
- **Nguyên nhân:** `location_id` (.xns11) và `topo_id` (.nwk11) lệch nhau (khoảng trắng, hoa/thường, gạch dưới).
- **Giải pháp:** Dùng `norm(s) = re.sub(r"[^A-Za-z0-9]", "", s).upper()` để chuẩn hóa trước khi so khớp.
- **Script:** 24b, 24b2, 27, 24e.

## LỖI 10 — Không đọc được `.xns11` bằng `mikeio`
- **Nguyên nhân:** `mikeio` không hỗ trợ định dạng cross-section `.xns11`.
- **Giải pháp:** Dùng **`mikeio1d`** (cần .NET runtime); lấy hình học ở `cross_section.raw`.
- **Script:** 03, 04, 02 (check env — phát hiện thiếu dotnet).

## LỖI 11 — Nhánh cù lao bị sót do topology
- **Nguyên nhân:** Nhận diện cù lao theo tên không đủ.
- **Giải pháp:** Trong 24b2 khai báo **tường minh** các cặp (sông, chainage tách) ↔ (sông, chainage nhập) qua bộ connector; cù lao = nhánh nội bộ, không gán biên.
- **Script:** 24b2_build_culao.py; kiểm liên thông bằng 49b_verify_connectivity.py.

## LỖI 12 — MASCARET không chạy / lỗi đọc file case (không có `FIN CORRECTE`)
- **Nguyên nhân:** Thiếu `dico.txt` hoặc `FichierCas.txt` trong thư mục chạy; hoặc file `.xcas`/`.loi`/`init.lig` bị lẫn **dấu tiếng Việt** (các file này ghi encoding `ascii`).
- **Giải pháp:** Đảm bảo thư mục có đủ `mascaret.xcas`, `FichierCas.txt` (1 dòng `'mascaret.xcas'`), `dico.txt`, `geometrie`, `init.lig`, `*.loi`. Không đưa ký tự tiếng Việt vào nội dung file ascii. Chạy `cd <dir> && mascaret.py mascaret.xcas`.
- **Script:** 20, 24b, 70 (đều sinh FichierCas.txt).

## LỖI 13 — Sai lệch khi tự động hóa bằng script 70
- **Nguyên nhân:** Engine của `70_run_model.py` gọi **script 26 (bộ sinh tổng quát) + 27**, KHÔNG phải backbone 24b/24d. Nếu tưởng 70 chạy backbone thì mạng/biên thực tế khác kỳ vọng.
- **Giải pháp:** Khi calibrate backbone 12 nhánh hoặc mạng cù lao, chạy thủ công 24b(2)→24d(2)→(smart_init)→mascaret→24e; hoặc sửa 70 trỏ sang 24b/24d.
- **Script:** 70, 26, 27.

---

## CHECKLIST KHI MÔ HÌNH KHÔNG CHẠY (thứ tự chẩn đoán)
1. Chạy `43_plot_full_check.py` — xem mạng, biên, trạm có đúng vị trí không.
2. Chạy `49b_verify_connectivity.py` — có nhánh xám (không liên thông) không?
3. Kiểm `init.lig` — đã qua `smart_init` chưa? Có điểm nào `z < bed` không?
4. Nếu "is dry" → chạy `24f_smooth_geometry.py --dry-run` xem mặt cắt nào gồ; rồi sửa thật + `24g` đối chiếu.
5. Kiểm `geometrie` — mọi bief có OFFSET đúng `(bief−1)×1e6`? abscissa tăng đơn điệu trong mỗi bief?
6. Kiểm `mascaret.xcas` — `profilsAbscAbsolu=true`, tempsMax khớp chuỗi biên, mọi extremité tự do đã có `.loi`?
7. Kiểm thư mục chạy có đủ `dico.txt` + `FichierCas.txt`; các file ascii không lẫn dấu tiếng Việt.
8. Đọc `listing.lis` tìm `FIN CORRECTE`; nếu có `is dry`/`supercritical` → quay lại LỖI 6/7.
