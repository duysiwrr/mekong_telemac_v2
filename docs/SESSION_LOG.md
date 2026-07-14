# Nhật ký phiên — mekong_telemac_v2

## Phiên 2026-07-14 — Khởi tạo repo sạch + Giai đoạn A

### Quyết định đã chốt
- Làm lại từ đầu, repo `mekong_telemac_v2`. Repo cũ chỉ dùng tham khảo cách
  coding + error playbook, KHÔNG kế thừa cấu trúc.
- Phạm vi: **toàn mạng liên thông ĐBSCL** (tối đa nhánh chạy được), mở rộng
  theo tầng (tier 0 trục chính -> tier max).
- Mặt cắt: **trộn** survey 2020 (nơi có) + 2011 (bù chỗ thiếu).
- **Bỏ ô trữ** (storage cell) — chỉ giữ kênh giải.
- Máy làm việc: cơ quan `/mnt/d/OneDrive/...`.
- QC hình học: A_wet ≥ 90% thực đo, cao độ bờ/đáy ±1 m.

### Đã làm
- Khung repo: `config/config.py` (nguồn chân lý path + tham số), `.gitignore`,
  `README.md`, copy error playbook -> `docs/ERROR_PLAYBOOK_ref.md`.
- **Giai đoạn A** `src/A_extract_ledger.py`: đọc nwk11+xns11+bnd11 -> chuẩn hóa
  nút/nhánh, phân loại GIỮ/BỎ theo topology, xuất sổ cái (branches.csv,
  nodes.csv, boundaries.csv, ledger.json) + network_map.png.
- Đã test syntax + logic parse/topology/nút với mạng giả 3 nhánh: ĐÚNG.

### Chưa làm được (cần chạy trên máy có data + mikeio1d)
- A chưa chạy trên data thật (Claude không có file MIKE + không cài mikeio1d).
- Cần Duy chạy `python3 src/A_extract_ledger.py --tier 0 --plot` rồi kiểm
  branches.csv + network_map.png, dán kết quả về.

### Bước tiếp (chờ duyệt sổ cái A)
- GĐ B `B_build_grid.py`: từ ledger.json -> geometrie + xcas + bief_map.
- GĐ C `C_assign_geometry_qc.py`: mặt cắt trộn + QC.
- GĐ D `D_run_eval.py`: biên + init + chạy + NSE/KGE.

### Việc cần Duy xác nhận ở phiên sau
- Đường dẫn `SURVEY_2020_DIR` và tên file Excel survey 2020 thật (config đang
  đoán `BASE/Survey2020/*.xlsx`).
- Tên nhánh thượng lưu gốc BFS: config đặt `MekongCam` (Kratie) — đúng không?
