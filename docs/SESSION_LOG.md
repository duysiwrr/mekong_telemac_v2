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

---

# NHẬT KÝ PHIÊN 2A — 16/07/2026 (giải mã cách đặt tên MIKE)

Trọng tâm: **giải mã cách đặt tên MIKE 11** + tìm gốc rễ lỗi 701.

## THÀNH TỰU

### 1. Gỡ 2 lỗi format MASCARET (đối chiếu file mẫu baseline)
- `variablesStockees` = **42** (không phải 41 như tài liệu cũ ghi)
  → thiếu 1 logical → crash `lec_sorties_`
- `planim/maillage`: `nbZones` phải = **nb_bief**, không phải 1
  → cấp mảng 1 phần tử nhưng lặp nb_bief → segfault `chainage_rezo_`

### 2. GIẢI MÃ CÁCH ĐẶT TÊN (quan trọng nhất)
Mô hình MIKE làm thủ công qua nhiều năm, nhiều người → tên rối. Nhưng
**MIKE đã chạy thông → nó KHÔNG thiếu gì**, chỉ là ta chưa hiểu cách khai báo.

Phương pháp: **logic → tọa độ → hợp lý mặt cắt → vị trí thực tế**

Quy luật: `<tiền tố><số><hậu tố>`, **cùng số = cùng vị trí dọc sông, khác nhánh**
- ST=Tiền, SH=Hậu, VN=Vàm Nao, CC=Cổ Chiên, HL=Hàm Luông
- Số = thứ tự từ thượng lưu ra biển
- Hậu tố: rỗng=chính, P/P1/P2=cù lao, CT=Cửa Tiểu, CĐ=Cửa Đại

### 3. HAI BẪY CHÍ TỬ
- **Chữ `Đ` tiếng Việt**: Excel `ST37CĐ` vs shapefile `ST37CD`. Regex
  `[A-Za-z]+` không bắt `Đ` → mất 11 mặt cắt cửa Đại → kết luận sai
  "cửa Đại chưa khảo sát". Sửa bằng `vn_norm()` → khớp 188→201.
- **`norm()` xóa dấu cách**: gộp `CO CHIEN`(2006, rộng TB 1359m) +
  `COCHIEN`(2021, rộng TB 829m) → **bề rộng răng cưa 164↔3481m** →
  MASCARET nội suy phi vật lý → lỗi 701. Đây là GỐC RỄ.
  ⚠️ Lời khuyên dùng `norm()` nằm trong ERROR_PLAYBOOK_ref LỖI 9 — đã đánh dấu.

### 4. Sửa SESSION_LOG phiên 1
Phiên 1 ghi: *"Hậu tố P/P1/P2/CT/CD = nhánh trái/phải khi sông chia ôm cù lao"*
→ **SAI**. `CT` = Cửa Tiểu, `CĐ` = Cửa Đại — hai cửa riêng biệt của sông Tiền,
không phải nhánh trái/phải. `CĐP/CĐP1/CĐP2` mới là cù lao trong cửa Đại.
Xác minh bằng tuyến ADCP: CĐP rộng 446–473m vs CT 726–879m, CĐ 1021–1620m.

### 5. Phát hiện Tuyen_do.shp
245 LineString = tuyến đo ADCP thật. `geometry.length` = **bề rộng sông THẬT**
→ dùng kiểm chứng mặt cắt Excel.

### 6. Rà soát GĐ A → ĐÚNG
Catalog xác nhận: `NHANH CO SURVEY 2020 nhung ledger BO: (khong co)`.
GĐ A đọc nwk11 (topology), không đụng mặt cắt → không dính lỗi tên.
Chỉ cần sửa `read_xns_widths`: `norm()` → `vn_norm()`.

### 7. Chốt nguyên tắc mặt cắt
- **Survey 2020 (ADCP) là chuẩn cao nhất** — áp toàn mô hình nơi có
- **Bù bằng topo `2021_SIWRP_QHPCTT`** nơi hở
- **BỎ HẲN topo 2006** — lòng sông xói lở bồi lắng qua 15 năm, không trộn
- Kết nối nhánh: theo MIKE, kiểm bằng survey. Mặt cắt: survey trước, MIKE sau.

### 8. Xác định 44 nhánh cho backbone mở rộng
11 chính + 33 cù lao, 1077 km, 197 mặt cắt survey 2020.
Phân tầng: tien(~17) → hau(~12) → truc(~24) → full(44).

## CÔNG CỤ MỚI
- `build_catalog.py` — bảng tra cứu (dùng ĐẦU TIÊN khi cần tra tên/tọa độ)
- `B_plot_grid.py` — vẽ lưới đang tính (trắc dọc/nút/mặt cắt/bảng)
- `B_plot_network.py` — bản đồ không gian lưới đang tính
- `B_plot_proposed.py` — bản đồ 44 nhánh đề xuất + phân tầng
- `C_assign_boundaries.py` — gán biên thực đo
- `C_init_smart.py` — Z init theo BFS topology (không theo số bief)

## PHÁT HIỆN NGƯỢC VỚI GIẢ THIẾT
- **Chênh Z tại nút KHÔNG gây lỗi** — baseline V1 chênh 5.6m ở 15/44 nút vẫn
  FIN CORRECTE. Cái gây lỗi là h quá nhỏ + hình học răng cưa.
- **Z init `bief/bmax` (V1) SAI với v2** — v2 đánh số bief theo `sorted(mike)`
  = ALPHABET (BASSAC→Bief_1, VamNao→Bief_15). Phải BFS topology tới cửa.


# NHẬT KÝ PHIÊN 2B — 16/07/2026 (v2 CHẠY THÔNG, máy OFFICE)

**MỐC: v2 CHẠY THÔNG LẦN ĐẦU với mặt cắt thực đo — 34.9s/30 ngày, Froude max 0.525**

## 1. KẾT QUẢ CUỐI PHIÊN

| Trạm | WL_NSE | WL_KGE | Q_NSE | Q_KGE | V1 (hạ đáy 10m) |
|---|---|---|---|---|---|
| TanChau | −103.6 | −0.647 | **+0.564** | **0.706** | Q_KGE 0.531 |
| ChauDoc | −34.0 | −1.499 | **+0.566** | **0.737** | Q_KGE −2.435 |
| VamNao | — | — | −169.8 | 0.301 | Q_KGE −1.409 |
| MyThuan | **+0.630** | 0.580 | −0.825 | 0.432 | Q_KGE 0.837* |
| CanTho | −2.287 | 0.433 | −0.136 | 0.607 | WL_KGE 0.530 |

\* V1 map MyThuan vào ch=95347 (cách cầu Mỹ Thuận thật 26km) → 0.837 là **con số sai chỗ**, không so được.

**v2 vượt V1:** ChauDoc Q_KGE −2.44 → **+0.74**; VamNao −1.41 → **+0.30**; TanChau 0.53 → **0.71**.

## 2. TỌA ĐỘ 5 TRẠM — ĐÃ CHỐT

**MIKE KHÔNG lưu tọa độ trạm.** Đã dò cạn (đừng tìm lại):

| Nguồn | Kết quả |
|---|---|
| `Boundary_2011.bnd11` | 10 khóa: ADRR, AutoCalQh, BndTS, Comment, Component, Dam, DescType, Inflow, OpenDesc, QhADM12 — **không x/y/coord/UTM** |
| `H-2011.dfs0` (1.4MB) | 34 tên trạm (H_TanChau, H_ChauDoc...), **không tọa độ** |
| `H_boudary_2011.dfs0` (16.9MB) | 10 trạm triều biển, **không tọa độ** |
| `H-2020.dfs0`, `H_2016.dfs0` | tên trạm, **không tọa độ** |
| `Net_2024.nwk11` | không section `[gauge]`/`[station]` |
| OBS `.txt` | header chỉ tên cột + `Unit 100001 1800 0` |
| Toàn OneDrive | 2 shapefile: `Vi tri MCN` (mặt cắt), `Tuyen do` (tuyến ADCP) |

Kiến trúc MIKE: gán theo `branch@chainage`, trạm nằm **ngoài** mô hình.

### BẪY TÊN (nguy hiểm — đừng hiểu nhầm lần nữa)
- **`'ChauDoc-Channel'` = KÊNH** nối `Tien@12704 → BASSAC@31537`, **KHÔNG phải trạm Châu Đốc**
- **`'Can Tho HH'` = KÊNH** ch=12090, **KHÔNG phải trạm Cần Thơ**
- 23 BndItem `INFLOW(Q)` trên backbone = **nhập lưu nội đồng**, không phải biên trạm

### `6-TVtrieu.xls` — DS trạm thủy văn vùng triều toàn quốc
Sheet `DSTV (T) (X)`, cột `KinhDo`/`ViDo` dạng **DDMMSS**.

⚠️ **Ô Tân Châu SAI:** `KinhDo=1055100` (105°51') trong khi hàng xóm An Giang:
Chợ Mới 105°24', Long Xuyên 105°27', Vàm Nao 105°21'. Tân Châu ở thượng nguồn
phải **nhỏ hơn** (~105°14'). Lỗi nhập liệu → chiếu lệch **66km**.

### TỌA ĐỘ CHỐT (đã chiếu lên mạng MIKE kiểm chứng)

| Trạm | X_UTM48N | Y_UTM48N | Nhánh | ch | d | Nguồn |
|---|---|---|---|---|---|---|
| TanChau | 526543 | 1194295 | Tien | 14050 | **59m** | bảng Duy cấp |
| ChauDoc | 514545 | 1183537 | BASSAC | 38988 | **19m** | bảng Duy cấp |
| VamNao | 539045 | 1168470 | VamNao | 18662 | 590m | bảng Duy cấp |
| MyThuan | 598558 | 1135034 | Tien | 121672 | 848m | 6-TVtrieu.xls |
| CanTho | 586757 | 1109202 | BASSAC | **149753 (ÉP)** | 1767m | 6-TVtrieu.xls |

**CanTho ép chainage:** Excel ghi sông = "Hậu (K. Xáng)". Cả 3 tọa độ đều chiếu vào
nhánh `Can_Tho` (d=90–161m) chứ không phải `BASSAC` (d=1767–5226m). Nhưng
Q_CanTho=14400 m³/s là Q **sông Hậu**, không thể là kênh nhỏ → nhà trạm ở bờ
Kênh Xáng (P. Cái Khế), tuyến đo Q vắt ngang sông Hậu. Ép map vào BASSAC.

**Bỏ hết ước lượng V1/AI** — MyThuan cũ (580000,1148000) cho d=2m nhưng cách cầu
Mỹ Thuận thật 26km. Trùng hợp, không phải cơ sở.

**Phân biệt 3 loại điểm trên `station_map.png`:**
- Sao đỏ/xanh = **BIÊN** (MIKE tính từ đầu/cuối nhánh nwk11)
- Kim cương = **NÚT** (MIKE tính từ connections)
- Dấu cộng = **TRẠM** (ghi tay trong `STATIONS` của `D_run_eval.py`)

Q_TanChau (biên, 520477/1206257) cách trạm TanChau **13km** — biên gán ở biên giới
Campuchia, trạm đo ở thị xã. Đúng, MIKE làm vậy.

## 3. SỬA GÌ TRONG PHIÊN

| Lỗi | Crash tại | Nguyên nhân | Sửa |
|---|---|---|---|
| 4 | `lec_sorties_` | `variablesStockees` 41 ≠ **42** | B_build_grid VAR_STOCK |
| 5 | `chainage_rezo_` | `nbZones=1` ≠ nb_bief | planim/maillage theo từng bief |
| 6 | Erreur 701 | biên `.loi` triều sin giả | C_assign_boundaries gán thực đo |
| 7 | Erreur 1 dry | Z init `bief/bmax` (V1) sai | C_init_smart BFS topology |
| 8 | Erreur 701 | **trộn topo 2006+2021** → răng cưa 164↔3481m | get_cross_sections lọc topo |

**Lỗi 8 là gốc rễ.** Sau khi lọc: răng cưa hàng chục chỗ → còn 2 chỗ x3.3/x3.4.

## 4. KIỂM CHỨNG NGƯỢC VỚI GIẢ THIẾT

- **MIKE topo `2021_SIWRP_QHPCTT` = survey 2020 ADCP** (giống từng số) → sông Hậu
  Châu Đốc **thật sự rộng 120–270m**, không phải 1500m như tôi đoán
- **Chênh Z tại nút KHÔNG gây lỗi** — baseline V1 chênh 5.6m ở 15/44 nút vẫn chạy
- **GĐ A đúng** — catalog xác nhận ledger giữ đủ mọi nhánh có survey

## 5. TỒN TẠI (ưu tiên phiên sau)

1. **Vàm Nao thiếu 45% lưu lượng** — Q mô phỏng ~6000 vs thực đo ~11000 m³/s,
   Q_NSE=−170. Phân lưu Tiền→Hậu quá ít. Chỉ 6 mặt cắt/23km (KC 3.9km).
   → Thêm mặt cắt survey 2020 (có 5), hoặc kiểm hình học Vàm Nao
2. **WL thấp hệ thống ~1.7m** tại TanChau/ChauDoc — WL_NSE −104/−34 nhưng
   WL_KGE −0.65/−1.50 → **dạng đúng, lệch mức**. Nghi datum hoặc Strickler=40
3. **Bief_1 (BASSAC) trắc dọc dốc 7m/30km** — quá lớn, liên quan mặt cắt hẹp
   164–560m đoạn đầu
4. Mở rộng BACKBONE 11 → 44 nhánh (33 cù lao có survey 2020)

## 6. ĐÓNG GÓI — `runs/RUN_<ten>/`

`.opt` 158MB không commit được. Nhưng **đầu vào chỉ 1MB, tái tạo 35s**.

```
runs/RUN_baseline_2020_15bief/   (4.6 MB)
├── input/      geometrie, xcas, init.lig, *.loi, dico.txt — chạy lại NGAY
├── summary/    eval_report.txt + 11 PNG
├── extract/    timeseries_stations.csv (Z,Q tại 5 trạm — giảm 446 lần)
├── META.json   tham số + KGE/NSE + thời gian chạy + git commit
├── README.md   bảng kết quả
└── RUN.sh      bash RUN.sh → FIN CORRECTE trong 35s  ✅ đã kiểm chứng
```

Kịch bản mới: copy gói → sửa tham số → chạy → `E_package_run.py --name <mới>`.
So sánh nhiều gói qua `META.json`.

## 7. GHI CHÚ KỸ THUẬT

- MASCARET v8p4r0 in **`FIN CORRECTE DU CALCUL`** trong `listing.lis` (không phải
  `FIN CORRECTE`) + `My work is done` ra stdout
- `.opt` format: `temps; bief; section; absc; ZREF; Z; QMIN; QMAJ; KMIN; KMAJ; FR; VMIN; Y; Q`
- Warm-up: `--eval-start 2011-10-08` bỏ 7 ngày đầu → eval 553 điểm
- Repo **private** → AI không đọc được, phải upload/dán vào chat
- Tải file AI gửi **thẳng vào `src/`**, không qua Downloads
# NHẬT KÝ PHIÊN 3 — 17/07/2026 (mở rộng lưới + phát hiện K=40 SAI)

**MỐC: xác định được 2 nguyên nhân gốc bằng thí nghiệm có kiểm chứng —
K=40 quá trơn, và 10 nhánh lăng trụ phá phân lưu.**

---

## 1. BA CẤU HÌNH TỐT NHẤT (30 ngày, `--eval-start 2011-10-08`, n=553)

### 🥇 HẠNG 1 — `truc_du` + K=30 (47 bief, 22 nhánh)
**Cân bằng nhất. Dùng làm baseline mới.**

| Trạm | WL_NSE | WL_KGE | Q_NSE | Q_KGE |
|---|---|---|---|---|
| TanChau | −11.981 | **+0.319** | 0.893 | **0.917** |
| ChauDoc | −170.666 | −0.326 | 0.851 | **0.920** |
| VamNao | — | — | −114.491 | **0.481** |
| MyThuan | 0.141 | **0.653** | −0.667 | **0.671** |
| CanTho | −4.008 | 0.291 | 0.125 | 0.488 |

Q đạt 0.48–0.92 ở **cả 5 trạm**. TanChau WL lần đầu dương.

### 🥈 HẠNG 2 — `truc_du` + K=25
**VamNao cao nhất từng đạt (0.615).** Đổi lại hạ lưu xấu.

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
| TanChau | **+0.393** | **0.980** |
| ChauDoc | −0.556 | **0.957** |
| VamNao | — | **0.615** ← kỷ lục |
| MyThuan | 0.342 | 0.533 |
| CanTho | −0.129 | 0.324 |

### 🥉 HẠNG 3 — `backbone` + K=30 (15 bief, 11 nhánh)
**Lưới đơn giản nhất mà vẫn tốt.** Dùng khi cần thử nhanh.

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
| TanChau | +0.281 | 0.944 |
| ChauDoc | −0.384 | 0.938 |
| VamNao | — | 0.523 |
| MyThuan | 0.522 | 0.675 |
| CanTho | −0.200 | 0.334 |

**Tái tạo:** `cp -r output/grid/truc_du output/grid/thu` → sửa `coefLitMin`/`coefLitMaj`
trong `mascaret.xcas` (chuỗi **n giá trị**, không phải 1!) → `mascaret.py mascaret.xcas`

---

## 2. BẢNG THÍ NGHIỆM ĐẦY ĐỦ — VamNao Q_KGE

| Lưới | K=40 | K=30 | K=25 |
|---|---|---|---|
| `backbone` 15 bief | 0.301 | 0.523 | 0.533 |
| `truc_du` 47 bief | **−0.618** | **+0.481** | **+0.615** |
| `truc` 82 bief | −2.503 | −0.218 | — |

**Đọc bảng:**
- **Hàng** = ảnh hưởng của lăng trụ (cùng K, chỉ khác 12 nhánh)
- **Cột** = ảnh hưởng của K (cùng lưới)

---

## 3. HAI PHÁT HIỆN GỐC

### 3.1. K=40 QUÁ TRƠN — sai ở MỌI lưới

K=40 → nước thoát quá dễ → WL thượng lưu thấp 2m → không đủ cột nước
đẩy qua Vàm Nao → phân lưu Tiền→Hậu thiếu 45%.

**Một gốc, nhiều triệu chứng.** "Tồn tại 1" (VamNao thiếu 45%) và "tồn tại 2"
(WL thấp ~1.7m) trong phiên 2 là **cùng một nguyên nhân**.

Bằng chứng: K=40→25 làm TanChau Q_KGE 0.706→**0.984**, VamNao 0.301→0.533
(15 bief); 47 bief thì −0.618→**+0.615**.

**MIKE dùng `G_resistance = 49`** (`Parameters/HD Coeff_2011.hd11`) — trơn hơn
cả ta. Nhưng MIKE có `ResisZone = 0, 30, 25, 20` (nhám phân vùng) và **bật lòng
tràn** (`G_flood_plan_res = -99`), còn xcas ta đặt `<litMajeur>false`.
→ Nghi: ta thiếu lòng tràn nên phải bù bằng K thấp.

### 3.2. 10 NHÁNH LĂNG TRỤ phá phân lưu — ĐỘC LẬP với K

Nhánh chỉ có **1 mặt cắt MIKE** → `build_geometrie` (dòng 342–343) nhân đôi
ra 2 đầu bief → tiết diện không đổi suốt 4–10 km.

**Danh sách:** `Tien_1, Tien_5, Tien_6, Tien_8, Hau_2, Hau_3, Hau_5, Hau_6,
Hau_9, CuaDai_3`

Bằng chứng độc lập với K — **cùng K=30**:
- 47 bief (bỏ lăng trụ): VamNao **+0.481**
- 82 bief (có lăng trụ): VamNao **−0.218**

K không che được lỗi hình học.

**Nhưng lăng trụ lại giúp HẠ LƯU** (thêm đường thoát dù dẫn sai):
CanTho WL 0.291→**0.534**, MyThuan Q 0.671→**0.727**.

---

## 4. XU THẾ: thêm nhánh → WL tốt, Q xấu

| | 15 bief | 47 bief | 82 bief |
|---|---|---|---|
| CanTho WL_KGE (K40) | 0.433 | **0.566** | 0.385 |
| CanTho Q_KGE (K40) | 0.607 | **0.684** | 0.544 |
| MyThuan WL_KGE (K40) | 0.580 | 0.535 | **0.672** |
| VamNao Q_KGE (K40) | **0.301** | −0.618 | −2.503 |
| Froude max (K40) | 0.525 | ? | 0.810 |

Cù lao mở thêm đường thoát → dung tích trữ tăng → **dạng triều hạ lưu đúng hơn**.
Nhưng cũng **chia bớt nước khỏi Vàm Nao** → phân lưu giảm.

---

## 5. BẪY ĐÃ GẶP (đừng lặp)

### 5.1. `sed` không sửa được Strickler
`<coefLitMin>` là **chuỗi n giá trị** (1/bief). `sed 's|40.0|30.0|'` chỉ đổi
số đầu → 14/15 bief vẫn K=40 → thí nghiệm vô hiệu. **Phải thay cả chuỗi bằng Python.**

### 5.2. Biên `.loi` hardcode số extremité
`BND` cũ ghi cứng `Z_CuaTieu_16`. Lưới 34 nhánh đánh số lại → xcas cần `_68`
→ file `.loi` thực đo ghi sai tên → **7 biên Z vẫn là TRIỀU SIN GIẢ** → lỗi 701.
**Đã sửa:** `doc_bien_tu_xcas()` đọc `<string>` từ xcas, bóc số, tra theo tên sông.
Có chặn cứng `SystemExit(1)` nếu còn `"trieu sin"`.

### 5.3. `--slope` của C_init_smart phụ thuộc số bief
`Z = z_sea + slope × d_cua`. Lưới 15 bief `d_cua_max=3` → slope 2.0 → Z≤9m.
Lưới 82 bief `d_cua_max=11` → slope 2.0 → **Z=25m (vô lý!)**.
**Quy tắc:** chọn slope sao cho `z_sea + slope×d_cua_max ≈ 9m`.
15 bief→2.0 | 47 bief→0.55 | 82 bief→0.55

### 5.4. KHÔNG rút ngắn được chuỗi mô phỏng
Thử 5 ngày (10.2s) và 12 ngày (21.4s) để chạy nhanh → **KGE méo hoàn toàn**:

| | 5d (n=97) | 12d (n=121) | 30d (n=553) |
|---|---|---|---|
| VamNao Q_KGE | −7.98 | **−15.50** | −2.50 |
| TanChau WL_NSE | −2985 | **−5912** | −385 |

Không đơn điệu → không phải warm-up. Vùng thượng lưu cần rất lâu để ổn định.
**Mọi thí nghiệm phải chạy đủ 30 ngày.**

### 5.5. `listing.lis` chứa cả nội dung init.lig
`tail listing.lis` ra khối số + ` FIN` → **tưởng nhầm là init.lig**.
Cách kiểm chạy xong đúng: `tail -2 ResultatsOpthyca.opt | cut -c1-70`
→ cột đầu `temps` phải đạt **2592000.0** (30 ngày).

### 5.6. KHÔNG cần `dico.txt` trong thư mục chạy
Playbook LỖI 12 và `E_package_run.py:INPUT_FILES` ghi cần — **SAI**.
`backbone` chạy thông mà không có file này. MASCARET tự tìm ở `~/telemac`.

### 5.7. `catalog_survey.csv` báo `mike=0` cho cù lao — SAI
`build_catalog` tra tên nwk11 (`Tien_1`) thẳng vào `location_id` (`TIEN_1`)
không qua alias → đếm 0. Thực tế `Tien_1` có 1, `NamThon` có 12 mặt cắt.
**Đã sửa** bằng `sinh_alias()` (vn_norm) trong B_build_grid + `F_catalog_3nguon.py`.

---

## 6. KIỂM CHỨNG NGƯỢC VỚI GIẢ THIẾT

- **Số liệu thực đo WL KHÔNG sai.** Nghi ngờ `H_TanChau` phẳng 4.7m là lỗi đọc
  → **SAI**. Tháng 10/2011 đỉnh lũ, Tân Châu 4.7m, lũ lấn át triều hoàn toàn.
  Tháng 7 cùng trạm có triều biên độ 1.77m. `read_obs` đọc đúng.
  → **Mô hình thiếu 2m WL mới là lỗi thật.**
- **Tọa độ 5 trạm ĐÚNG.** Kiểm lại bằng pyproj (VN2000→WGS84) + chiếu lên
  polyline: TanChau d=116m tới nhánh `Tien`. Bảng phiên 2B chốt là chuẩn.
  **Đừng dò lại lần nữa.**
- **topo 2021 = survey 2020 ADCP.** So từng mặt cắt trên BASSAC: **36/36 đáy
  lệch 0.00m**, 34/36 bề rộng lệch 0.0m. Toàn mạng: 181/185 cặp giống nhau,
  lệch đáy TB **0.04m**. → `get_cross_sections` đọc topo 2021 = đọc survey 2020.
  Nguyên tắc §4.4 KHÔNG bị vi phạm.
- **3 mặt cắt lệch >900m** (SH36, SH36A ở BASSAC; SH35 ở Hau_7): Excel 3300–3450m
  vs MIKE 2100–2400m. Đều ở cửa sông — MIKE cắt bãi bồi, giữ lòng dẫn. **Hợp lý.**
- **5 cụm survey "LỆCH"** (ST12/16/28/33, VN1): kiểm `mike2/mike3` → **topology
  MIKE đúng cả 5**. Nguyên nhân: VN1 trùng bản ghi; ST12 có hai `P` (đáng lẽ P/P1);
  ST16P, ST28P2 trỏ vào sông mẹ. Lỗi đặt tên survey, không phải MIKE thiếu nhánh.

---

## 7. HƯỚNG TIẾP THEO

### 7.1. [NGAY] K PHÂN BỐ theo vùng
Đánh đổi đã đo rõ: **K thấp → thượng lưu tốt, hạ lưu xấu**.
Không K đồng nhất nào thắng cả mạng.

| Vùng | K đề xuất | Căn cứ |
|---|---|---|
| Tien/BASSAC thượng lưu, VamNao | 25 | VamNao 0.615, TanChau Q 0.980 |
| Tien/BASSAC hạ lưu, CoChien, HamLuong | 30 | cân bằng |
| 6 cửa biển | 40 | CanTho WL 0.566 ở K40 |

`write_xcas` đã sẵn sàng: `fr_k` là chuỗi n giá trị. Chỉ cần đổi cách sinh —
gán K theo `bief → tên sông → vùng`.

### 7.2. Xử lý 10 nhánh lăng trụ
Không nội suy từ sông mẹ được (cù lao 190–600m vs sông mẹ 1000–2400m — co giãn
là **bịa hình học**). Ba lựa chọn:
1. **Bỏ hẳn** (dùng `truc_du` 22 nhánh) — mất 10 nhánh thật
2. **Bổ sung mặt cắt** từ survey 2020 nếu có (`Tien_8` có sv=2 nhưng mike=1!)
3. **Chấp nhận** — MIKE cũng chỉ có 1 mặt cắt và nó chạy được

→ Ưu tiên (2) cho `Tien_8`: survey có 2 mặt cắt mà MIKE chỉ 1.

### 7.3. Lòng tràn (`litMajeur`)
MIKE bật (`G_flood_plan_res = -99`), ta tắt (`<litMajeur>false`).
Tháng 10/2011 đỉnh lũ, nước tràn bờ mạnh. **Nghi đây là gốc của WL thấp 2m** —
và lý do ta phải hạ K để bù. Thử bật.

### 7.4. Thêm kênh nội đồng theo vùng
**Chỉ làm sau khi K phân bố + lăng trụ xong.** Thêm kênh vào lưới đang sai
= nhân thêm lỗi.

Thứ tự đề xuất (theo mức ảnh hưởng tới phân lưu Tiền↔Hậu):
1. **Tứ giác Long Xuyên (TGLX)** — nối Hậu→biển Tây, ảnh hưởng trực tiếp
   phân lưu tại Châu Đốc. Kênh Vĩnh Tế, Tri Tôn, Ba Thê, Rạch Giá–Long Xuyên.
   Trạm kiểm: H_XuanTo, H_TriTon, H_TanHiep, H_RachGia (đã có trong WL_OBS)
2. **Đồng Tháp Mười (ĐTM)** — nối Tiền→Vàm Cỏ. Kênh Hồng Ngự, Đồng Tiến,
   Nguyễn Văn Tiếp. Trạm: H_MocHoa, H_TuyenNhon, H_KienBinh, H_TruongXuan
3. **Tây Nam Sông Hậu (TNSH)** — Hậu→biển Tây. Kênh Ô Môn, Xà No, Quản Lộ.
   Trạm: H_ViThanh, H_PhungHiep, H_XeoRo
4. **Nam Măng Thít** — Cổ Chiên↔Hậu. Trạm: H_TraVinh
5. **Bán đảo Cà Mau (BĐCM)** — Trạm: H_CaMau, H_PhuocLong, H_GanhHao, H_SongDoc

**Lợi ích:** 34 cột WL_OBS hiện chỉ dùng 7 → thêm kênh trục sẽ dùng được
**~20 trạm kiểm định** nữa, đánh giá mô hình chặt hơn nhiều.

**Rủi ro:** ledger có 1899 nhánh. `--subset full` = quá lớn. Cần subset theo
vùng, mỗi vùng FIN CORRECTE mới thêm vùng sau (đúng nguyên tắc phân tầng).

**Tốc độ:** hiện 46s/82 bief. Thêm 5 vùng → có thể 300–500 bief, `.opt` cỡ GB.
Nút cổ chai KHÔNG phải MASCARET mà là `D_run_eval` (đọc 1.17M dòng lấy 3605).
Khi đó mới cần tối ưu: `grep` lọc trước, hoặc giảm `variablesStockees`
(cẩn thận: `D_run_eval` đọc theo chỉ số cột cố định `C_Z=5`, `C_Q=13`).

---

## 8. LỆNH TÁI TẠO 3 CẤU HÌNH TỐT NHẤT

```bash
cd ~/mekong_telemac_v2

# ---- HANG 1: truc_du K=30 (baseline moi) ----
python3 src/B_build_grid.py --subset truc_du --outdir output/grid/truc_du
python3 src/C_assign_boundaries.py --outdir output/grid/truc_du \
    --start 2011-10-01 --end 2011-10-31
python3 src/C_init_smart.py --outdir output/grid/truc_du \
    --z-sea 3.0 --slope 0.55 --h-min 8.0
python3 - <<'PYEOF'
import re; from pathlib import Path
p = Path("output/grid/truc_du/mascaret.xcas")
x = p.read_text(encoding="latin-1")
for tag in ("coefLitMin","coefLitMaj"):
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", x)
    n = len(m.group(1).split())          # CHUOI n gia tri — khong sed 1 so!
    x = x.replace(m.group(0), f"<{tag}>{' '.join(['30.0']*n)}</{tag}>")
p.write_text(x, encoding="latin-1")
PYEOF
cp output/grid/truc/{Abaques.txt,Controle.txt,dico_Courlis.txt} output/grid/truc_du/
cd output/grid/truc_du && mascaret.py mascaret.xcas   # ~41s
cd ~/mekong_telemac_v2
python3 src/D_run_eval.py --outdir output/grid/truc_du --eval-start 2011-10-08

# ---- HANG 2: doi 30.0 -> 25.0 o tren ----
# ---- HANG 3: --subset backbone, --slope 2.0, K=30 ----
```

⚠️ **BẮT BUỘC `--eval-start 2011-10-08`** (bỏ 7 ngày warm-up) → n=553.
# NHẬT KÝ PHIÊN 3 — 17/07/2026 (mở rộng lưới + phát hiện K=40 SAI)

**MỐC: xác định được 2 nguyên nhân gốc bằng thí nghiệm có kiểm chứng —
K=40 quá trơn, và 10 nhánh lăng trụ phá phân lưu.**

---

## 1. BA CẤU HÌNH TỐT NHẤT (30 ngày, `--eval-start 2011-10-08`, n=553)

### 🥇 HẠNG 1 — `truc_du` + K=30 (47 bief, 22 nhánh)
**Cân bằng nhất. Dùng làm baseline mới.**

| Trạm | WL_NSE | WL_KGE | Q_NSE | Q_KGE |
|---|---|---|---|---|
| TanChau | −11.981 | **+0.319** | 0.893 | **0.917** |
| ChauDoc | −170.666 | −0.326 | 0.851 | **0.920** |
| VamNao | — | — | −114.491 | **0.481** |
| MyThuan | 0.141 | **0.653** | −0.667 | **0.671** |
| CanTho | −4.008 | 0.291 | 0.125 | 0.488 |

Q đạt 0.48–0.92 ở **cả 5 trạm**. TanChau WL lần đầu dương.

### 🥈 HẠNG 2 — `truc_du` + K=25
**VamNao cao nhất từng đạt (0.615).** Đổi lại hạ lưu xấu.

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
| TanChau | **+0.393** | **0.980** |
| ChauDoc | −0.556 | **0.957** |
| VamNao | — | **0.615** ← kỷ lục |
| MyThuan | 0.342 | 0.533 |
| CanTho | −0.129 | 0.324 |

### 🥉 HẠNG 3 — `backbone` + K=30 (15 bief, 11 nhánh)
**Lưới đơn giản nhất mà vẫn tốt.** Dùng khi cần thử nhanh.

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
| TanChau | +0.281 | 0.944 |
| ChauDoc | −0.384 | 0.938 |
| VamNao | — | 0.523 |
| MyThuan | 0.522 | 0.675 |
| CanTho | −0.200 | 0.334 |

**Tái tạo:** `cp -r output/grid/truc_du output/grid/thu` → sửa `coefLitMin`/`coefLitMaj`
trong `mascaret.xcas` (chuỗi **n giá trị**, không phải 1!) → `mascaret.py mascaret.xcas`

---

## 2. BẢNG THÍ NGHIỆM ĐẦY ĐỦ — VamNao Q_KGE

| Lưới | K=40 | K=30 | K=25 |
|---|---|---|---|
| `backbone` 15 bief | 0.301 | 0.523 | 0.533 |
| `truc_du` 47 bief | **−0.618** | **+0.481** | **+0.615** |
| `truc` 82 bief | −2.503 | −0.218 | — |

**Đọc bảng:**
- **Hàng** = ảnh hưởng của lăng trụ (cùng K, chỉ khác 12 nhánh)
- **Cột** = ảnh hưởng của K (cùng lưới)

---

## 3. HAI PHÁT HIỆN GỐC

### 3.1. K=40 QUÁ TRƠN — sai ở MỌI lưới

K=40 → nước thoát quá dễ → WL thượng lưu thấp 2m → không đủ cột nước
đẩy qua Vàm Nao → phân lưu Tiền→Hậu thiếu 45%.

**Một gốc, nhiều triệu chứng.** "Tồn tại 1" (VamNao thiếu 45%) và "tồn tại 2"
(WL thấp ~1.7m) trong phiên 2 là **cùng một nguyên nhân**.

Bằng chứng: K=40→25 làm TanChau Q_KGE 0.706→**0.984**, VamNao 0.301→0.533
(15 bief); 47 bief thì −0.618→**+0.615**.

**MIKE dùng `G_resistance = 49`** (`Parameters/HD Coeff_2011.hd11`) — trơn hơn
cả ta. Nhưng MIKE có `ResisZone = 0, 30, 25, 20` (nhám phân vùng) và **bật lòng
tràn** (`G_flood_plan_res = -99`), còn xcas ta đặt `<litMajeur>false`.
→ Nghi: ta thiếu lòng tràn nên phải bù bằng K thấp.

### 3.2. 10 NHÁNH LĂNG TRỤ phá phân lưu — ĐỘC LẬP với K

Nhánh chỉ có **1 mặt cắt MIKE** → `build_geometrie` (dòng 342–343) nhân đôi
ra 2 đầu bief → tiết diện không đổi suốt 4–10 km.

**Danh sách:** `Tien_1, Tien_5, Tien_6, Tien_8, Hau_2, Hau_3, Hau_5, Hau_6,
Hau_9, CuaDai_3`

Bằng chứng độc lập với K — **cùng K=30**:
- 47 bief (bỏ lăng trụ): VamNao **+0.481**
- 82 bief (có lăng trụ): VamNao **−0.218**

K không che được lỗi hình học.

**Nhưng lăng trụ lại giúp HẠ LƯU** (thêm đường thoát dù dẫn sai):
CanTho WL 0.291→**0.534**, MyThuan Q 0.671→**0.727**.

---

## 4. XU THẾ: thêm nhánh → WL tốt, Q xấu

| | 15 bief | 47 bief | 82 bief |
|---|---|---|---|
| CanTho WL_KGE (K40) | 0.433 | **0.566** | 0.385 |
| CanTho Q_KGE (K40) | 0.607 | **0.684** | 0.544 |
| MyThuan WL_KGE (K40) | 0.580 | 0.535 | **0.672** |
| VamNao Q_KGE (K40) | **0.301** | −0.618 | −2.503 |
| Froude max (K40) | 0.525 | ? | 0.810 |

Cù lao mở thêm đường thoát → dung tích trữ tăng → **dạng triều hạ lưu đúng hơn**.
Nhưng cũng **chia bớt nước khỏi Vàm Nao** → phân lưu giảm.

---

## 5. BẪY ĐÃ GẶP (đừng lặp)

### 5.1. `sed` không sửa được Strickler
`<coefLitMin>` là **chuỗi n giá trị** (1/bief). `sed 's|40.0|30.0|'` chỉ đổi
số đầu → 14/15 bief vẫn K=40 → thí nghiệm vô hiệu. **Phải thay cả chuỗi bằng Python.**

### 5.2. Biên `.loi` hardcode số extremité
`BND` cũ ghi cứng `Z_CuaTieu_16`. Lưới 34 nhánh đánh số lại → xcas cần `_68`
→ file `.loi` thực đo ghi sai tên → **7 biên Z vẫn là TRIỀU SIN GIẢ** → lỗi 701.
**Đã sửa:** `doc_bien_tu_xcas()` đọc `<string>` từ xcas, bóc số, tra theo tên sông.
Có chặn cứng `SystemExit(1)` nếu còn `"trieu sin"`.

### 5.3. `--slope` của C_init_smart phụ thuộc số bief
`Z = z_sea + slope × d_cua`. Lưới 15 bief `d_cua_max=3` → slope 2.0 → Z≤9m.
Lưới 82 bief `d_cua_max=11` → slope 2.0 → **Z=25m (vô lý!)**.
**Quy tắc:** chọn slope sao cho `z_sea + slope×d_cua_max ≈ 9m`.
15 bief→2.0 | 47 bief→0.55 | 82 bief→0.55

### 5.4. KHÔNG rút ngắn được chuỗi mô phỏng
Thử 5 ngày (10.2s) và 12 ngày (21.4s) để chạy nhanh → **KGE méo hoàn toàn**:

| | 5d (n=97) | 12d (n=121) | 30d (n=553) |
|---|---|---|---|
| VamNao Q_KGE | −7.98 | **−15.50** | −2.50 |
| TanChau WL_NSE | −2985 | **−5912** | −385 |

Không đơn điệu → không phải warm-up. Vùng thượng lưu cần rất lâu để ổn định.
**Mọi thí nghiệm phải chạy đủ 30 ngày.**

### 5.5. `listing.lis` chứa cả nội dung init.lig
`tail listing.lis` ra khối số + ` FIN` → **tưởng nhầm là init.lig**.
Cách kiểm chạy xong đúng: `tail -2 ResultatsOpthyca.opt | cut -c1-70`
→ cột đầu `temps` phải đạt **2592000.0** (30 ngày).

### 5.6. KHÔNG cần `dico.txt` trong thư mục chạy
Playbook LỖI 12 và `E_package_run.py:INPUT_FILES` ghi cần — **SAI**.
`backbone` chạy thông mà không có file này. MASCARET tự tìm ở `~/telemac`.

### 5.7. `catalog_survey.csv` báo `mike=0` cho cù lao — SAI
`build_catalog` tra tên nwk11 (`Tien_1`) thẳng vào `location_id` (`TIEN_1`)
không qua alias → đếm 0. Thực tế `Tien_1` có 1, `NamThon` có 12 mặt cắt.
**Đã sửa** bằng `sinh_alias()` (vn_norm) trong B_build_grid + `F_catalog_3nguon.py`.

---

## 6. KIỂM CHỨNG NGƯỢC VỚI GIẢ THIẾT

- **Số liệu thực đo WL KHÔNG sai.** Nghi ngờ `H_TanChau` phẳng 4.7m là lỗi đọc
  → **SAI**. Tháng 10/2011 đỉnh lũ, Tân Châu 4.7m, lũ lấn át triều hoàn toàn.
  Tháng 7 cùng trạm có triều biên độ 1.77m. `read_obs` đọc đúng.
  → **Mô hình thiếu 2m WL mới là lỗi thật.**
- **Tọa độ 5 trạm ĐÚNG.** Kiểm lại bằng pyproj (VN2000→WGS84) + chiếu lên
  polyline: TanChau d=116m tới nhánh `Tien`. Bảng phiên 2B chốt là chuẩn.
  **Đừng dò lại lần nữa.**
- **topo 2021 = survey 2020 ADCP.** So từng mặt cắt trên BASSAC: **36/36 đáy
  lệch 0.00m**, 34/36 bề rộng lệch 0.0m. Toàn mạng: 181/185 cặp giống nhau,
  lệch đáy TB **0.04m**. → `get_cross_sections` đọc topo 2021 = đọc survey 2020.
  Nguyên tắc §4.4 KHÔNG bị vi phạm.
- **3 mặt cắt lệch >900m** (SH36, SH36A ở BASSAC; SH35 ở Hau_7): Excel 3300–3450m
  vs MIKE 2100–2400m. Đều ở cửa sông — MIKE cắt bãi bồi, giữ lòng dẫn. **Hợp lý.**
- **5 cụm survey "LỆCH"** (ST12/16/28/33, VN1): kiểm `mike2/mike3` → **topology
  MIKE đúng cả 5**. Nguyên nhân: VN1 trùng bản ghi; ST12 có hai `P` (đáng lẽ P/P1);
  ST16P, ST28P2 trỏ vào sông mẹ. Lỗi đặt tên survey, không phải MIKE thiếu nhánh.

---

## 7. HƯỚNG TIẾP THEO

### 7.1. [NGAY] K PHÂN BỐ theo vùng
Đánh đổi đã đo rõ: **K thấp → thượng lưu tốt, hạ lưu xấu**.
Không K đồng nhất nào thắng cả mạng.

| Vùng | K đề xuất | Căn cứ |
|---|---|---|
| Tien/BASSAC thượng lưu, VamNao | 25 | VamNao 0.615, TanChau Q 0.980 |
| Tien/BASSAC hạ lưu, CoChien, HamLuong | 30 | cân bằng |
| 6 cửa biển | 40 | CanTho WL 0.566 ở K40 |

`write_xcas` đã sẵn sàng: `fr_k` là chuỗi n giá trị. Chỉ cần đổi cách sinh —
gán K theo `bief → tên sông → vùng`.

### 7.2. Xử lý 10 nhánh lăng trụ
Không nội suy từ sông mẹ được (cù lao 190–600m vs sông mẹ 1000–2400m — co giãn
là **bịa hình học**). Ba lựa chọn:
1. **Bỏ hẳn** (dùng `truc_du` 22 nhánh) — mất 10 nhánh thật
2. **Bổ sung mặt cắt** từ survey 2020 nếu có (`Tien_8` có sv=2 nhưng mike=1!)
3. **Chấp nhận** — MIKE cũng chỉ có 1 mặt cắt và nó chạy được

→ Ưu tiên (2) cho `Tien_8`: survey có 2 mặt cắt mà MIKE chỉ 1.

### 7.3. Lòng tràn (`litMajeur`)
MIKE bật (`G_flood_plan_res = -99`), ta tắt (`<litMajeur>false`).
Tháng 10/2011 đỉnh lũ, nước tràn bờ mạnh. **Nghi đây là gốc của WL thấp 2m** —
và lý do ta phải hạ K để bù. Thử bật.

### 7.4. Thêm kênh nội đồng theo vùng
**Chỉ làm sau khi K phân bố + lăng trụ xong.** Thêm kênh vào lưới đang sai
= nhân thêm lỗi.

Thứ tự đề xuất (theo mức ảnh hưởng tới phân lưu Tiền↔Hậu):
1. **Tứ giác Long Xuyên (TGLX)** — nối Hậu→biển Tây, ảnh hưởng trực tiếp
   phân lưu tại Châu Đốc. Kênh Vĩnh Tế, Tri Tôn, Ba Thê, Rạch Giá–Long Xuyên.
   Trạm kiểm: H_XuanTo, H_TriTon, H_TanHiep, H_RachGia (đã có trong WL_OBS)
2. **Đồng Tháp Mười (ĐTM)** — nối Tiền→Vàm Cỏ. Kênh Hồng Ngự, Đồng Tiến,
   Nguyễn Văn Tiếp. Trạm: H_MocHoa, H_TuyenNhon, H_KienBinh, H_TruongXuan
3. **Tây Nam Sông Hậu (TNSH)** — Hậu→biển Tây. Kênh Ô Môn, Xà No, Quản Lộ.
   Trạm: H_ViThanh, H_PhungHiep, H_XeoRo
4. **Nam Măng Thít** — Cổ Chiên↔Hậu. Trạm: H_TraVinh
5. **Bán đảo Cà Mau (BĐCM)** — Trạm: H_CaMau, H_PhuocLong, H_GanhHao, H_SongDoc

**Lợi ích:** 34 cột WL_OBS hiện chỉ dùng 7 → thêm kênh trục sẽ dùng được
**~20 trạm kiểm định** nữa, đánh giá mô hình chặt hơn nhiều.

**Rủi ro:** ledger có 1899 nhánh. `--subset full` = quá lớn. Cần subset theo
vùng, mỗi vùng FIN CORRECTE mới thêm vùng sau (đúng nguyên tắc phân tầng).

**Tốc độ:** hiện 46s/82 bief. Thêm 5 vùng → có thể 300–500 bief, `.opt` cỡ GB.
Nút cổ chai KHÔNG phải MASCARET mà là `D_run_eval` (đọc 1.17M dòng lấy 3605).
Khi đó mới cần tối ưu: `grep` lọc trước, hoặc giảm `variablesStockees`
(cẩn thận: `D_run_eval` đọc theo chỉ số cột cố định `C_Z=5`, `C_Q=13`).

---

## 8. LỆNH TÁI TẠO 3 CẤU HÌNH TỐT NHẤT

```bash
cd ~/mekong_telemac_v2

# ---- HANG 1: truc_du K=30 (baseline moi) ----
python3 src/B_build_grid.py --subset truc_du --outdir output/grid/truc_du
python3 src/C_assign_boundaries.py --outdir output/grid/truc_du \
    --start 2011-10-01 --end 2011-10-31
python3 src/C_init_smart.py --outdir output/grid/truc_du \
    --z-sea 3.0 --slope 0.55 --h-min 8.0
python3 - <<'PYEOF'
import re; from pathlib import Path
p = Path("output/grid/truc_du/mascaret.xcas")
x = p.read_text(encoding="latin-1")
for tag in ("coefLitMin","coefLitMaj"):
    m = re.search(rf"<{tag}>([^<]*)</{tag}>", x)
    n = len(m.group(1).split())          # CHUOI n gia tri — khong sed 1 so!
    x = x.replace(m.group(0), f"<{tag}>{' '.join(['30.0']*n)}</{tag}>")
p.write_text(x, encoding="latin-1")
PYEOF
cp output/grid/truc/{Abaques.txt,Controle.txt,dico_Courlis.txt} output/grid/truc_du/
cd output/grid/truc_du && mascaret.py mascaret.xcas   # ~41s
cd ~/mekong_telemac_v2
python3 src/D_run_eval.py --outdir output/grid/truc_du --eval-start 2011-10-08

# ---- HANG 2: doi 30.0 -> 25.0 o tren ----
# ---- HANG 3: --subset backbone, --slope 2.0, K=30 ----
```

⚠️ **BẮT BUỘC `--eval-start 2011-10-08`** (bỏ 7 ngày warm-up) → n=553.

---
---

# NHẬT KÝ PHIÊN 3B — 17/07/2026 chiều (mở khóa biên toàn ĐBSCL)

**MỐC: giải được bài toán "biên cho kênh nội đồng" — thứ chặn đường mở rộng
từ đầu dự án. Nhưng lưới `paA` CHƯA chạy thông.**

---

## 1. 🔑 CHÌA KHÓA: `Boundary_2011.bnd11` có sẵn biên cho MỌI kênh cụt

**Vấn đề tưởng là bế tắc:** `--subset full` sinh 4584 bief / **126 biên tự do**.
`MAP_SONG` gõ tay chỉ biết 10 → 116 biên không có số liệu → tưởng phải bịa Q=0.

**Sự thật:** `.bnd11` có **1709 BndItem**. MIKE đã gán sẵn biên cho mọi nhánh:

```
DescType = <type>, <sub>, '<nhanh>', <CHAINAGE>, 0, '', '<nhan/tram>'
Inflow   = 2,0,0, |<file.dfs0>|, 0, <idx>, '<ten item>', 0, 1
```

| type | nghĩa | ví dụ |
|---|---|---|
| **0** | **biên mở (cửa biển)** — 102 cái | `0,5,'CuaCoChien',30881,..,'Ben Trai'` |
| 1 | nhu cầu nước (`Waterdemand2.dfs0`, 1595 cái) | `1,0,'BASSAC',74310,..,'W16'` |
| 5 | biên vùng | `5,0,'AMAB7',0,..,'Rach Gia'` |

**Kiểm chứng ngược:** type=0 khớp **3/3** với `MAP_SONG` gõ tay
(`CuaCoChien→Ben Trai`, `CuaTieu→Vam Kenh`, `Ham Luong→An Thuan`)
→ cách map biên→trạm của ta ĐÚNG, chỉ thiếu độ phủ.

**Script mới `G_doc_bnd11.py`** → `data_ref/catalog/bnd_map.csv`:
nhánh | chainage | type | nhãn | file_dfs0 | item | **cot_obs** | co_so_lieu

**Kết quả:** 93/102 biên mở tra được cột OBS. 9 cái không tra được đều có lý do:
`My Thanh` ×3 (không có trạm trong WL_OBS — dùng `H_TranDe` thay),
Campuchia ×2, `Tri An`/`Dau Tieng`/`Kratie`/`GREATLAKE` (ngoài vùng).

**`C_assign_boundaries` giờ 3 tầng:**
1. `MAP_SONG` gõ tay → `TanChau`, `ChauDoc` (biên Q ta tự gán tại điểm cắt
   thượng lưu — MIKE lấy từ Kratie nên KHÔNG có entry, ĐÚNG thiết kế) + 6 cửa
2. `bnd_map.csv` → biên MIKE gán sẵn
3. Còn lại → **Q=0** (kênh cụt/công trình `*_cau`, `Dap_Tha_La`)

**paA:** 9 gõ tay + **132 từ bnd_map** + 32 Q=0 = 173 biên.
Trước: 9. Giờ: **141 biên có số liệu thật.**

---

## 2. ⛔ GIỚI HẠN CỨNG CỦA MASCARET — không sửa được bằng lưới

```
lec_reseau.f90:107   character(len=8192) :: line
```

`.xcas` với 4513 bief → thẻ `<abscDebut>` = **57555 ký tự** → bị cắt ở 8192
→ `Fortran runtime error: Bad integer for item 1 in list input`

**16 thẻ vượt 8192** khi lưới 4513 bief. Dài nhất 57555.

**NGÂN SÁCH: ~700 bief.** (8192 ÷ ~11 ký tự/bief cho `abscDebut`)

| Lưới | bief | Thẻ dài nhất | |
|---|---|---|---|
| `du_k30` (baseline) | 47 | 135 | ✓ |
| `truc` | 82 | ~250 | ✓ |
| **`paA`** | **423** | **4963** | ✓ còn dư 40% |
| `full` | 4513 | 57555 | ✗ |

**QUYẾT ĐỊNH: KHÔNG sửa source TELEMAC.** Nó đã chạy thông 4 lần —
vấn đề nằm ở lưới ta sinh quá rối, không phải công cụ.
Đơn giản hóa LƯỚI, không sửa CÔNG CỤ.
(Đã suýt đi sai hướng: định `sed len=8192 → 262144` rồi build lại.)

---

## 3. LƯỚI `paA` — thuật toán lọc chốt

**GIỮ CỨNG:**
- 11 nhánh TRỤC: `Tien, BASSAC, VamNao, CoChien, Ham Luong` + 6 cửa
- **95 nhánh CÓ BIÊN** trong `bnd_map.csv` — cửa ra biển. **Bỏ là mạng không thoát.**
  (Duy: *"có biên từ số liệu thực đo là phải giữ"*)

**LỌC phần còn lại:** `cấp ≤ 2` (BFS từ TRỤC) **và** `rộng ≥ 100m`

→ **208 nhánh → 423 bief / 221 nút / 173 biên / 11232→? PROFIL**

**Bảng 6 phương án đã đo** (luôn giữ TRỤC + 95 biên):

| K | W | nhánh | ~bief | |
|---|---|---|---|---|
| 1 | 100m | 173 | 415 | |
| 1 | 80m | 196 | 470 | |
| 2 | 100m | **208** | **423 (thật)** | ← **PA A** |
| 2 | 80m | 288 | 691 | sát trần |
| 3 | 100m | 234 | 562 | |
| 2 | 60m | 374 | 898 | ✗ vượt |
| 3 | 80m | 354 | 850 | ✗ vượt |

Tỉ lệ thật: **2.03 bief/nhánh** (không phải 2.4 như cù lao).

**File danh sách:** `/tmp/pa_A.txt` (sinh lại bằng đoạn script trong §6)
**Dùng:** `python3 src/B_build_grid.py --subset-file /tmp/pa_A.txt --outdir output/grid/paA`

---

## 4. PHÂN CẤP MẠNG (BFS từ TRỤC) — ledger 1847 nhánh

| cấp | n | ≥60m | ≥80m | ≥100m |
|---|---|---|---|---|
| 0 (TRỤC) | 11 | 11 | 11 | 11 |
| 1 (nối trực tiếp) | 177 | 136 | 98 | 75 |
| 2 | 339 | 148 | 99 | 41 |
| 3 | 332 | 118 | 73 | 31 |
| 4 | 378 | | | |
| 5–9 | 610 | | | |

**Cô lập: 0.** Mạng sâu tới **cấp 9** (BFS 5 vòng của tôi lúc đầu SAI → 40 nhánh
báo nhầm là "chơi vơi").

**Lọc theo chiều dài/độ thẳng VÔ DỤNG:**
- P50 chiều dài = 5.95 km, P75 = 11.6 km → không có "ngắn ngủn" rõ rệt
- Độ thẳng P75 = 1.15, P90 = 1.44 → gần như mọi kênh đều thẳng (kênh đào)

---

## 5. ❌ LỖI CÒN LẠI — `paA` CHƯA CHẠY THÔNG

```
=> ERROR <=
Open boundary 1 : Z_BASI_CR_10  is with a supercritical flow
```

`BASI_CR` = kênh nội đồng, được gán Q=0. **Chưa xem mặt cắt nó.**
→ Đúng LỖI 6 playbook V1: *"mặt cắt co thắt cục bộ → Froude>1"*
→ Duy: *"mặt cắt các kênh đóng vai trò quan trọng tạo ra lỗi nếu chúng vô lý"*

**Việc kế tiếp:** xem mặt cắt `BASI_CR` (tra `numExtrem` → bief nào), nếu vô lý
(rộng vài m + sâu) → bỏ khỏi subset hoặc lọc `WIDTH_MIN`.

Cũng nên kiểm: 41/11712 mặt cắt có **đáy > 0m** (`Cam8` +2.00m),
`kenhkn8` đáy **−80.59m** (phi lý — sông Tiền sâu nhất mới −38m),
1414/11712 mặt cắt rộng **<20m** (`NETF.WIDTH_MIN=50` có trong config nhưng
KHÔNG thấy áp dụng).

---

## 6. LỖI MỚI CHO PLAYBOOK (14–18)

### LỖI 14 — `.xcas` thẻ >8192 ký tự → "Bad integer"
`lec_reseau.f90:107 character(len=8192)`. Lưới >~700 bief là vỡ.
**Không sửa source.** Giảm số bief.

### LỖI 15 — Q=0 phải sửa **CẢ HAI** chỗ trong xcas
Gán Q=0 cho kênh cụt nhưng `write_xcas` khai `typeCond=2` (Z) →
MASCARET đọc `0.0` như **cao độ 0m** → supercritical → STOP 1.
**Phải sửa:**
1. `<typeCond>` trong `<extrLibres>`: 2 → 1
2. `<type>` trong `<structureParametresLoi>`: 2 → 1
   (KHÔNG phải `<typeLoi>` — thẻ đó không tồn tại!)

Sai một chỗ → `"The graph #N of type #2 is incompatible with the boundary
condition #N of type 1"`.

Cấu trúc đúng (đối chiếu `du_k30` đã FIN CORRECTE):
```xml
<structureParametresLoi>
  <nom>Q_ChauDoc</nom>
  <type>1</type>            <!-- Q -> 1 | Z -> 2, PHẢI KHỚP typeCond -->
  <donnees><fichier>Q_ChauDoc.loi</fichier>...
```

### LỖI 16 — `| head` GIẾT script đang ghi file ⚠️
```bash
python3 src/C_assign_boundaries.py ... | head -8     # SAI!
```
SIGPIPE giết script sau 8 dòng → chỉ ghi vài `.loi`, **171/173 còn triều sin giả**
→ MASCARET đọc sin giả → supercritical. Mất 1 lượt chẩn đoán.
**Dùng `| tail` hoặc `> log 2>&1`.**

### LỖI 17 — OFFSET tràn định dạng `.opt`
`OFFSET = 1e6` × 423 bief = **422 triệu** → `.opt` ghi `"**"` và `***********`.
**Sửa `config.py`: OFFSET 1e6 → 2e5** → absc max 84.4 triệu, vừa.
Ràng buộc: `OFFSET > bief dài nhất` (paA 96.7km, du_k30 86.5km → 200km an toàn)
và `OFFSET × nb_bief < 1e8`.
`D_run_eval` KHÔNG dùng OFFSET (map trạm bằng `bief_map.txt`) → baseline an toàn.

### LỖI 18 — bỏ Vàm Cỏ làm biên TĂNG
Thử lọc `Vam Co/Dong/Tay` → biên **124 → 155**. Vì 30+ kênh ĐTM
(`Thu_Thua`, `kenhLA285..508`, `T3..T8`, `KENHTG1`) thoát vào Vàm Cỏ → thành cụt.
→ **KHÔNG lọc nhánh mà kênh nội đồng đang thoát vào.**
`WL_OBS` có `H_TanAn`, `H_BenLuc` trên Vàm Cỏ → gán biên được.

---

## 7. `DROP_UPSTREAM` mở rộng 8 → 30 nhánh

| Nhóm | Nhánh |
|---|---|
| Campuchia | `MekongCam, BassacCam, Tonle_Sap, GREATLAKE, Mkampoul_s, Stung-Takaev, Cam6/7/8/30..49` (15 nhánh Cam*) |
| Sài Gòn–Đồng Nai | `Dong Nai, Sai Gon, Vinh Cuu, K. LONG TAU, R.PHUOC KIENG, Can Giuoc, Song Kinh, East Vaico, R. BEN NGHE*, S.BenCat, R.NhanhCanGiuoc*, RachTra_*, RACHTRAQUAN, ThayCaiRachTra, KENHTHAYCAI*` |
| **KHÔNG lọc** | **`Vam Co`, `Vam Co Dong`, `Vam Co Tay`** — xem LỖI 18 |

**Ledger: 1899 → 1847 nhánh. Baseline `truc_du` VẪN 22/47/224** (đã kiểm 3 lần).

---

## 8. LÀM TIẾP Ở NHÀ

```bash
export MEKONG_MACHINE=home
cd ~/mekong_telemac_v2
git pull origin v3-kenh-truc
python3 -m config.config              # phai ra 5 file [OK]
```
⚠ `config.py` máy home trỏ `/mnt/c/Users/win/...` — máy cơ quan là `Hello`.
Nếu sai path, sửa `_BASE_BY_MACHINE`.

**Sinh lại `/tmp/pa_A.txt`:**
```bash
python3 - <<'PYEOF'
import csv, pandas as pd
from collections import defaultdict, deque
noi = defaultdict(set)
for row in csv.reader(open("output/ledger/nodes.csv", encoding="utf-8"), delimiter=";"):
    if len(row)<4: continue
    for it in row[3].split("|"):
        p = it.split(":")
        if p[0]: noi[p[0]].add(row[1]); noi[row[1]].add(p[0])
giu = {r["ten_mike"]: float(r["width_m"] or 0) for r in csv.DictReader(
       open("output/ledger/branches.csv", encoding="utf-8"), delimiter=";") if r["giu"]=="GIU"}
TRUC = {"Tien","BASSAC","VamNao","CoChien","Ham Luong","CuaTieu","CuaDai",
        "CuaCoChien","CuaCungHau","CuaDinhAn","CuaTranDe"}
cap = {n: None for n in giu}; dq = deque()
for n in TRUC & set(giu): cap[n]=0; dq.append(n)
while dq:
    u = dq.popleft()
    for v in noi[u]:
        if v in giu and cap[v] is None: cap[v]=cap[u]+1; dq.append(v)
bien = set(pd.read_csv("data_ref/catalog/bnd_map.csv", sep=";").query("type==0")["nhanh"]) & set(giu)
S = {n for n in giu if (cap[n] is not None and cap[n]<=2) or n in bien or n in TRUC}
S = {n for n in S if giu[n]>=100 or n in bien or n in TRUC}
open("/tmp/pa_A.txt","w").write("\n".join(sorted(S)))
print(f"PA A: {len(S)} nhanh -> /tmp/pa_A.txt")
PYEOF
```

**Chạy `paA` (KHÔNG dùng `| head`!):**
```bash
python3 src/B_build_grid.py --subset-file /tmp/pa_A.txt --outdir output/grid/paA > /tmp/g.log 2>&1
python3 src/C_assign_boundaries.py --outdir output/grid/paA \
    --start 2011-10-01 --end 2011-10-31 > /tmp/bnd.log 2>&1
python3 src/C_init_smart.py --outdir output/grid/paA \
    --z-sea 3.0 --slope 0.25 --h-min 8.0 > /tmp/init.log 2>&1
cp output/grid/du_k30/{Abaques.txt,Controle.txt,dico_Courlis.txt} output/grid/paA/
cd output/grid/paA && mascaret.py mascaret.xcas > /tmp/run.log 2>&1
grep -i -A4 "=> ERROR" /tmp/run.log
```

**VIỆC ĐẦU TIÊN: sửa `Z_BASI_CR_10 supercritical`**
```bash
# tra numExtrem -> bief nao
python3 -c "
import re
from pathlib import Path
x = Path('output/grid/paA/mascaret.xcas').read_text(encoding='latin-1', errors='replace')
m = re.search(r'<extrLibres>(.*?)</extrLibres>', x, re.S)
noms = re.findall(r'<string>([^<]*)</string>', m.group(1))
ext = re.search(r'<numExtrem>([^<]*)</numExtrem>', m.group(1)).group(1).split()
i = noms.index('Z_BASI_CR_10')
e = int(ext[i]); print(f'numExtrem={e} -> Bief_{(e+1)//2}')
"
# roi xem mat cat bief do trong geometrie
```

---

## 9. BASELINE VẪN LÀ `truc_du` K=30 (47 bief)

`paA` chưa chạy thông → **KHÔNG thay baseline**.
Gói: `runs/RUN_baseline_truc_du_K30/` → `bash RUN.sh` (41s)
⚠ `input/geometrie` trong gói ghi bằng **OFFSET=1e6**. Config giờ là 2e5.
Sinh lại từ `B_build_grid` sẽ ra geometrie khác — nhưng gói vẫn chạy được
độc lập (có sẵn geometrie).

**Kiểm baseline sau mọi thay đổi:**
```bash
python3 src/B_build_grid.py --subset truc_du --outdir /tmp/kt > /tmp/kt.log 2>&1
grep -E "Tập con|SPLIT|Geometrie" /tmp/kt.log     # PHAI ra 22 / 47 / 224
```
