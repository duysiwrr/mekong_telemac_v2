# ĐỌC ĐẦU TIÊN MỖI PHIÊN — mồi cho Claude

## DỰ ÁN 1 CÂU
Chuyển MIKE11 ĐBSCL -> TELEMAC/MASCARET 1D. Mục tiêu: lưới toàn ĐBSCL
<=700 bief -> ML dự báo SSC. Repo private, Claude KHÔNG đọc được -> dán file.

## 3 NGUYÊN TẮC SỐNG CÒN (Claude hay quên)
1. --eval-start 2011-10-08 (bỏ 7 ngày warm-up, n=553)
2. Chạy đủ 30 ngày (5d/12d méo hoàn toàn)
3. KHÔNG dùng `| head` với script ghi file (SIGPIPE giết -> file dở)

## BASELINE (KHÔNG đổi) — truc_du K=30
22 nhánh / 47 bief / 224 PROFIL. KGE: TanChau Q0.917 VamNao0.481 MyThuan WL0.653.
Kiểm sau MỌI thay đổi: python3 src/B_build_grid.py --subset truc_du --outdir /tmp/kt
Gói chạy độc lập: runs/RUN_baseline_truc_du_K30/ -> bash RUN.sh (42s).

## GIỚI HẠN CỨNG
- MASCARET len=8192 -> ngân sách ~700 bief. KHÔNG sửa source TELEMAC.
- Kênh cụt Q=0 phải sửa CẢ typeCond VÀ <type> trong structureParametresLoi.

## TRẠNG THÁI HIỆN TẠI (cập nhật cuối mỗi phiên)
- Ledger 1791 nhánh (DROP_UPSTREAM 101). Ranh Vàm Cỏ Tây xong.
- Phân vùng 15 hệ thống xong (tools/phan_vung_thuyloi.py).
- paA (423 bief) CHƯA chạy thông: kênh trục đầu ra <100m bị cắt cụt.
- ĐANG LÀM: gán 9_KHAC vào vùng, rà soát TGLX/BĐCM/Nam Măng Thít.

## QUY TẮC LÀM VIỆC VỚI CLAUDE
- Claude phải KIỂM DỮ LIỆU trước khi đoán (nguyên tắc #1 của Duy).
- Script vá -> dán thẳng terminal (heredoc), KHÔNG tải file.
- Luôn kiểm liên thông (BFS từ Tien, 0 cô lập) sau khi bỏ nhánh.
- Đọc CUỐI docs/SESSION_LOG.md cho chi tiết phiên gần nhất.
