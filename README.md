# mekong_telemac_v2 — Mô hình thủy lực 1D TELEMAC/MASCARET cho ĐBSCL

Bản làm lại **sạch** từ đầu. Repo cũ (`mekong-telemac-1d`) đã chứng minh chạy
thông mô hình, nhưng tích tụ ~50 script gây nhiễu và mạng lưới chưa đúng. Repo
này giữ lại **logic và bài học** (đặc biệt error playbook), bỏ phần nhiễu, đi
thẳng vào mục tiêu: **một mạng lưới sông–kênh ĐBSCL đúng, chạy thông suốt, số
liệu hợp lý so với thực đo.**

## Nguyên tắc thiết kế
1. **Một nguồn chân lý cho đường dẫn/tham số**: tất cả trong `config/config.py`.
   Đổi máy = sửa 1 dòng `MACHINE`.
2. **Không lọc mạng theo tên** (tên MIKE lộn xộn). Lọc theo *topology + kích
   thước + có mặt cắt*. Bỏ ô trữ.
3. **Sổ cái sạch trước, sinh lưới sau**: chuẩn hóa toàn bộ MIKE thành một bảng
   con người đọc được, kiểm mắt bằng PNG, rồi mới sinh geometrie.
4. **Mở rộng theo tầng**: mỗi tầng mạng phải `FIN CORRECTE` trước khi thêm nhánh.
5. **QC hình học có kiểm soát** thay cho làm mượt mù: so A_wet, cao độ bờ/đáy
   với thực đo, gắn cờ khi lệch > ngưỡng (A_wet ≥ 90%, bờ/đáy ±1 m).

## Cấu trúc thư mục
```
mekong_telemac_v2/
├── config/config.py     # đường dẫn + tham số (nguồn chân lý duy nhất)
├── src/                 # script pipeline (A -> B -> C -> D)
├── output/
│   ├── ledger/          # A: sổ cái mạng chuẩn hóa (CSV/JSON) + PNG
│   ├── grid/            # B: geometrie + xcas + bief_map
│   ├── geom_qc/         # C: mặt cắt trộn 2020/2011 + báo cáo QC
│   └── run/             # D: kết quả chạy + NSE/KGE
├── docs/                # sổ tay + nhật ký phiên
└── data_ref/            # (rỗng — data MIKE nằm ngoài repo, chỉ tham chiếu qua config)
```

## Pipeline 4 giai đoạn
| GĐ | Script | Việc | Ra |
|----|--------|------|-----|
| A | `A_extract_ledger.py` | Đọc nwk11+xns11+bnd11 → chuẩn hóa nút/nhánh/biên, phân loại giữ/bỏ theo topology | `output/ledger/*.csv,*.json,*.png` |
| B | `B_build_grid.py` | Từ sổ cái → geometrie + xcas + bief_map (OFFSET, split junction, confluent) | `output/grid/` |
| C | `C_assign_geometry_qc.py` | Gán mặt cắt (2020 nơi có, 2011 bù) + QC so thực đo | `output/geom_qc/` |
| D | `D_run_eval.py` | Biên thực đo + smart init + chạy MASCARET + NSE/KGE | `output/run/` |

## Cách chạy
```bash
# 0. kiểm đường dẫn data (đầu mỗi phiên)
python3 -m config.config

# A. sổ cái sạch
python3 src/A_extract_ledger.py --tier 0        # tier 0 = trục chính chạy được
python3 src/A_extract_ledger.py --tier 0 --plot # + bản đồ PNG kiểm mắt

# B-C-D: sẽ bổ sung sau khi A được duyệt
```

## Tham số MASCARET sống còn (từ config)
`OFFSET=(bief-1)×1e6`, `versionCode=3`, `code=2`, `profilsAbscAbsolu=true`,
`hauteurEauMini=0.005`. Encoding: `geometrie`/`.opt`=latin-1; `xcas`/`.loi`/
`init.lig`=ascii. Đọc `.xns11` bằng **mikeio1d** (không phải mikeio).

## Trạng thái
- [x] Khung repo + config
- [ ] Giai đoạn A — sổ cái sạch  ← đang làm
- [ ] Giai đoạn B — sinh lưới
- [ ] Giai đoạn C — mặt cắt + QC
- [ ] Giai đoạn D — chạy + eval
