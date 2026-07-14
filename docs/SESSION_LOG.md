# NHẬT KÝ PHIÊN — 14/07/2026

Xây dựng lại từ đầu pipeline TELEMAC-1D ĐBSCL trong repo sạch `mekong_telemac_v2`.
Trọng tâm phiên: **hoàn thành Giai đoạn A — sổ cái mạng lưới sạch**.

---

## KẾT QUẢ CUỐI PHIÊN

Mạng lưới GĐ A: **1899 nhánh GIỮ**, liên thông **1899/1899** (0 cô lập), 3166 nút.
- Bắt đầu từ Tân Châu (đầu Tien) + Châu Đốc (đầu BASSAC), cắt bỏ thượng lưu Campuchia.
- Loại ô trữ/linkchannel nội đồng (1043), nhánh không mặt cắt, ngoài liên thông.
- Giữ nhánh có mặt cắt MIKE 2011 hoặc survey 2020, gồm cả nhánh cù lao.
- Mặt cắt survey 2020: 176 mặt cắt đồng bộ tọa độ với MIKE (median 46m).

---

## KIẾN TRÚC REPO

```
mekong_telemac_v2/
├── config/config.py          # nguồn chân lý: đường dẫn + tham số + trạm
├── src/
│   ├── A_extract_ledger.py   # GĐ A: sổ cái mạng (nút/nhánh/biên)
│   ├── sync_sections.py      # đồng bộ survey 2020 <-> MIKE bằng tọa độ
│   ├── import_data.py        # build kho data_ref (mặt cắt + biên Q/WL)
│   ├── audit_network.py      # rà soát: kênh loại, chia mảnh, liên thông
│   └── check_gaps.py         # kiểm nhánh mảnh có hở chainage
├── data_ref/cross_sections/  # kho mặt cắt chuẩn hóa + sync_index.csv
├── output/ledger/            # branches.csv, nodes.csv, boundaries.csv, ledger.json
└── output/audit/             # removed_map.png, connectivity_map.png
```

Chạy bằng python của venv có mikeio1d:
`~/TELEMAC_1D_MEKONG/.venv/bin/python src/A_extract_ledger.py --tier full --plot`

---

## QUYẾT ĐỊNH THIẾT KẾ QUAN TRỌNG

1. **Cắt thượng lưu tại Tân Châu/Châu Đốc**: MIKE lấy biên từ Kratie (Campuchia),
   nhưng số liệu thực đo ở Tân Châu (=đầu nhánh Tien, x=520477) + Châu Đốc
   (=đầu BASSAC, x=509000). BFS từ 2 nhánh này, chặn MekongCam/BassacCam.
   Biên Q gán tại đây (cột Q_TanChau, Q_ChauDoc trong Q_OBS).

2. **Lọc mạng theo dữ liệu, KHÔNG theo tên**:
   - Loại [linkchannel]/[storagearea] (khai báo MIKE trực tiếp) — đã kiểm
     chứng 100% là kênh nội đồng DTM/TGLX width<=20m, KHÔNG có kênh trục.
   - Loại nhánh không có mặt cắt, ô trữ width>3000m (Biển Hồ).
   - Loại nhánh cô lập không nối trục chính (BFS cuối).

3. **Nguồn mặt cắt trộn**: survey 2020 (ADCP, mới) nơi có, MIKE 2011 bù chỗ thiếu.
   Nhánh trục quan trọng không có 2020 vẫn lấy mặt cắt từ MIKE.

4. **Đồng bộ survey<->MIKE bằng TỌA ĐỘ**, không bằng tên (tên Excel CC10P khác
   shapefile CC10P1/P2, hoa/thường lẫn lộn). Hậu tố P/P1/P2/CT/CD = nhánh
   trái/phải khi sông chia ôm cù lao.

---

## LỖI ĐÃ PHÁT HIỆN & SỬA (quan trọng — tránh lặp)

### LỖI NGHIÊM TRỌNG: ghi đè nhánh chia mảnh
- Triệu chứng: Cái Sắn (kênh 59km) không hiện trên bản đồ, chỉ còn 1km.
- Nguyên nhân: MIKE chia 162 nhánh thành nhiều đoạn cùng tên (tại mỗi nút
  giao có kênh cắt ngang). Code branches[name]={...} GHI ĐÈ, chỉ giữ đoạn
  cuối -> mất 301 đoạn toàn mạng.
- Sửa: branches[name] thành LIST các đoạn (setdefault.append). Sửa mọi hàm
  dùng nó: build_adjacency, build_nodes, classify, write_ledger, plot_map.
  Xác minh: Cái Sắn giữ đủ 2 đoạn 29 điểm.
- Bài học: nhánh cùng tên nhiều đoạn = cách MIKE tạo nút giao. KHÔNG gộp lại
  (sẽ phá nút giao), giữ nguyên đoạn, chúng liên thông qua nút.

### Các hướng SAI đã tránh được nhờ kiểm chứng
- "Thẳng + ít điểm" để bắt ô trữ -> SAI, bắt nhầm cầu/đập/kênh đào. Bỏ, dùng
  [linkchannel] trực tiếp.
- Định "gộp nhánh chia mảnh thành 1" -> SAI, sẽ xóa nút giao. Kiểm chứng cho
  thấy các đoạn nối qua nút giao, không cần gộp.

---

## CÔNG THỨC ĐỌC MẶT CẮT SURVEY 2020 (đã kiểm chứng bằng hình)
- File Excel format 3 hàng/mặt cắt: [tên TÊN(km+m)] / [khoảng cách] / [cao độ].
- y = cumsum(hàng khoảng cách), z = hàng cao độ. Mỗi mặt cắt 3 hàng.
- Điểm bờ (ADCP không đo sát bờ) = z cao ở 2 mép, đánh dấu "bo" vs "do".
- Vị trí từ Vi tri MCN.shp (EPSG 32648), chiếu lên polyline MIKE gần nhất.

---

## THAM SỐ SỐNG CÒN (config.py)
- OFFSET=(bief-1)x1e6, versionCode=3, code=2, profilsAbscAbsolu=true, hauteurEauMini=0.005
- Encoding: geometrie/.opt=latin-1; xcas/.loi/init.lig=ascii
- Đọc .xns11 bằng mikeio1d (cần venv ~/TELEMAC_1D_MEKONG/.venv, có .NET)
- Data nguồn: /mnt/d/OneDrive/.../MIKE11-DBSCL (máy cơ quan)
- Survey 2020: /mnt/d/OneDrive/.../TELEMAC_1D_MEKONG/01_data/processed/cross_sections/clean

---

## BƯỚC TIẾP THEO
- [ ] GĐ B B_build_grid.py: từ ledger.json -> geometrie + xcas + bief_map
      (OFFSET, split junction, encoding). Nên chạy thử tập con trước khi full.
- [ ] GĐ C: gán mặt cắt trộn 2020/2011 + QC (A_wet>=90%, bờ/đáy +-1m).
- [ ] GĐ D: biên + smart init + chạy MASCARET + NSE/KGE tại 5 trạm.

## GHI CHÚ VẬN HÀNH
- Có thể có script lạ (Qwen...) đè lên ledger. Nếu số nhánh sai, chạy lại đúng
  thứ tự: A (lần 1) -> sync_sections -> A (lần 2) -> import_data -> audit.
- Luôn chạy bằng venv, không python hệ thống (thiếu mikeio1d).
