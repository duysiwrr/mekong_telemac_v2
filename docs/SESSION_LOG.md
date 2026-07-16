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
