# TÀI LIỆU BÀN GIAO V2 — DỰ ÁN TELEMAC-1D ĐBSCL (mekong_telemac_v2)

> Đọc file này TRƯỚC khi làm bất cứ gì. Cập nhật: **16/07/2026** (phiên 2).
> Repo: https://github.com/duysiwrr/mekong_telemac_v2 (**PRIVATE** — AI không tự
> đọc được, phải dán/upload nội dung vào chat).

---

## 0. NGƯỜI DÙNG & NGUYÊN TẮC LÀM VIỆC (QUAN TRỌNG NHẤT)

Duy — nghiên cứu sinh SIWRR, làm luận án tích hợp mô hình thủy lực 1D
(TELEMAC/MASCARET) + machine learning cho sông Tiền/Hậu ĐBSCL.

**Yêu cầu tuyệt đối của Duy (vi phạm = làm lại):**
1. **KHÔNG suy diễn lòng vòng.** Kiểm chứng bằng dữ liệu thật TRƯỚC khi kết luận.
2. **Đối chiếu file mẫu đã chạy thông** thay vì tự nghĩ ra cách mới.
3. **In hình ra để kiểm mắt** — Duy tin hình hơn con số. **In hình TRƯỚC, đừng hứa
   rồi hoãn.** Nếu đã có script vẽ sẵn thì DÙNG, đừng viết cái mới.
4. **Đọc code cũ (V1) để HỌC CÁCH CODE**, KHÔNG kế thừa thông số/thiết kế.
5. Phân tích độc lập, đừng hỏi Duy câu hỏi phân tích.
6. Chạy lại cái đã work trước khi dựng cái mới.
7. **Rà soát TOÀN BỘ một lượt**, đừng sửa lắt nhắt từng lỗi rồi chạy lại.

**Lỗi AI đã mắc ở phiên 2 (tránh lặp):**
- Hứa in hình rồi hoãn 3 lần → Duy phê bình đúng.
- Sửa `mascaret.xcas` (file output, bị ghi đè) thay vì sửa `src/*.py` (file nguồn).
- Vẽ SVG bằng tay trong khi `plot_network_xsec.py` đã có sẵn.
- Kết luận "cửa Đại không có khảo sát" khi chưa kiểm chữ `Đ` tiếng Việt.
- Đổ lỗi cho GĐ A khi lỗi nằm ở GĐ B.
- Fix từng lỗi một thay vì diff toàn bộ xcas với file mẫu ngay từ đầu.

---

## 1. MÔI TRƯỜNG

| | Máy nhà | Máy cơ quan |
|---|---|---|
| BASE data | `/mnt/c/Users/win/OneDrive/De Tai/De Tai TELEMAC/MIKE11-DBSCL` | `/mnt/d/OneDrive/De Tai/De Tai TELEMAC/MIKE11-DBSCL` |
| export | `export MEKONG_MACHINE=home` | `export MEKONG_MACHINE=office` |

**venv BẮT BUỘC** (python hệ thống thiếu mikeio1d):
```bash
source ~/TELEMAC_1D_MEKONG/.venv/bin/activate
```
TELEMAC: `~/telemac/v8p4r0`, build `gfortranOMP`, chạy `mascaret.py mascaret.xcas`

**Đầu phiên LUÔN chạy:**
```bash
cd ~/mekong_telemac_v2 && git pull origin main
source ~/TELEMAC_1D_MEKONG/.venv/bin/activate
export MEKONG_MACHINE=office   # hoặc home
python3 -m config.config       # phải ra 5 file [OK]
```

**Lưu ý cài file mới:** repo private → AI không push được. Khi AI gửi file, Duy
phải bấm tải rồi `cp` vào `src/`, HOẶC chạy đoạn `python3 - <<'PYEOF'` mà AI cấp
(sửa thẳng file nguồn, có `.bak` + `assert` bảo vệ). Kiểm bằng `grep -c` trước
khi chạy tiếp — **đã mất 3 lượt vì file chưa được cài mà cứ chạy lại**.

---

## 2. DỮ LIỆU NGUỒN

### MIKE 11
- `Networks/Net_2024.nwk11.nwk11` — 3009 nhánh, 38964 điểm
- `Networks/XSecF_2011-update2023.xns11` — **2401 location_id, 11098 mặt cắt**
  (số cũ ghi 2362/8867 là SAI — do `norm()` gộp nhầm)
- `Boundary/Boundary_2011.bnd11` — 1709 biên
- `OBS/Q/Q_theo Gio/Q-Observed-for-Calibration-2011.txt` — 5 cột: Q_ChauDoc,
  Q_TanChau, Q_VamNao, Q_CanTho, Q_MyThuan
- `OBS/.../WL-Observed-for-Calibration-2011.txt` — 34 cột (H_ChauDoc, H_TanChau,
  H_VamKenh, H_AnThuan, H_BenTrai, H_TranDe...)

### Survey 2020 (ADCP) — CHUẨN CAO NHẤT
`/mnt/{c,d}/.../TELEMAC_1D_MEKONG/01_data/processed/cross_sections/clean/`
- 5 Excel: `SongTien/SongHau/SongVamNao/SongCoChien/SongHamLuong__clean.xlsx`
  → **212 mặt cắt có z** (số cũ 201 là SAI — regex bỏ sót chữ `Đ`)
- `Shapefiles/Vi tri MCN.shp` — **229 điểm** (EPSG:32648), cột `Name`, `FolderPath`
- `Shapefiles/Tuyen do.shp` — **245 LineString** = tuyến đo ADCP thật.
  `geometry.length` = **BỀ RỘNG SÔNG THẬT** — dùng kiểm chứng mặt cắt.
- Khớp shp↔Excel qua tọa độ: **201/229**

---

## 3. GIẢI MÃ CÁCH ĐẶT TÊN MIKE 11 — THÀNH TỰU LỚN NHẤT PHIÊN 2

> **Bối cảnh:** mô hình MIKE này do người làm thủ công qua nhiều năm, nhiều đợt
> khảo sát, nhiều người. Tên đặt KHÔNG logic, KHÔNG nhất quán, gây hiểu nhầm
> nghiêm trọng. Nhưng **mô hình MIKE đã chạy thông → nó KHÔNG thiếu gì**. Mọi
> "thiếu" đều là do ta chưa hiểu cách khai báo.
>
> **Phương pháp giải mã (dùng lại khi gặp tên lạ):**
> 1. **Phân tích logic** — tách tên thành (tiền tố, số, hậu tố)
> 2. **Phân tích tọa độ** — TỌA ĐỘ LÀ CHÂN LÝ, không tin tên
> 3. **Phân tích hợp lý mặt cắt** — bề rộng/độ sâu có hợp sông thật không
> 4. **Phân tích vị trí sông kênh thực tế** — đối chiếu bản đồ

### 3.1. Quy luật đặt tên SURVEY 2020

```
<tiền tố><số><hậu tố>
   ST      37     CT
```
- **Tiền tố** = sông: `ST`=sông Tiền, `SH`=sông Hậu, `VN`=Vàm Nao,
  `CC`=Cổ Chiên, `HL`=Hàm Luông
- **Số** = thứ tự mặt cắt **từ thượng lưu ra biển**
- **Hậu tố** = nhánh tại vị trí đó:
  - rỗng = nhánh chính
  - `P`, `P1`, `P2`, `P3` = nhánh phụ (ôm cù lao)
  - `CT` = **Cửa Tiểu**, `CĐ` = **Cửa Đại** (chỉ sông Tiền, từ ST37)
  - `CĐP`, `CĐP1`, `CĐP2` = nhánh phụ trong cửa Đại
  - `A`, `B`, `AP`, `AP1` = mặt cắt bổ sung

**QUY LUẬT VÀNG: CÙNG SỐ = CÙNG VỊ TRÍ DỌC SÔNG, KHÁC NHÁNH (tạo cù lao).**
Ví dụ ST37 có 3 điểm = sông Tiền chia 3 nhánh tại đó:
```
ST37CT  (662967,1139894) -> MIKE: CuaTieu@3929   d=28m   rộng 726m
ST37CĐP (662825,1138846) -> MIKE: CuaDai_1@1165  d=2m    rộng 473m  <- cù lao
ST37CĐ  (662095,1137188) -> MIKE: CuaDai@4129    d=144m  rộng 1021m
```

### 3.2. BẪY CHÍ TỬ #1 — chữ `Đ` tiếng Việt

Excel dùng **`ST37CĐ`** (chữ Đ tiếng Việt), shapefile dùng **`ST37CD`** (chữ D).
Regex cũ `[A-Za-z]+` **không bắt được `Đ`** → **11 mặt cắt cửa Đại biến mất im
lặng** → kết luận sai "cửa Đại chưa khảo sát".

**Cách sửa — BẮT BUỘC dùng hàm này ở MỌI script đọc tên:**
```python
import unicodedata, re
def vn_norm(s):
    """Bo dau tieng Viet. 'ST37CĐ' -> 'ST37CD'."""
    s = str(s).replace('Đ','D').replace('đ','d')
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r"[^A-Za-z0-9]", "", s).upper()

NAME_RE = re.compile(r"([^\s(]+)\s*\((\d+)\+(\d+)\)")   # bắt MỌI ký tự
SPLIT_RE = re.compile(r"^([A-Z]+?)(\d+)([A-Z0-9]*)$")   # tách pre/num/suf
```
Kết quả: khớp shp↔Excel **188 → 201**.

### 3.3. BẪY CHÍ TỬ #2 — `norm()` xóa dấu cách gộp nhầm location

`norm()` cũ = `re.sub(r"[^A-Za-z0-9]","",s).upper()` → xóa dấu cách →
**`CO CHIEN` và `COCHIEN` bị gộp thành một**, dù đó là **HAI location_id RIÊNG
BIỆT** trong MIKE với **HAI đợt khảo sát khác nhau**:

| norm() gộp | location_id thật | n | topo_id |
|---|---|---|---|
| `COCHIEN` | `CO CHIEN` | 57 | 2006 |
| | `COCHIEN` | 13 | 2021_SIWRP_QHPCTT |
| `HAMLUONG` | `HAM LUONG` | 62 | 2006(46)+2021(16) |
| | `HAMLUONG` | 16 | 2021 |
| | `Ham Luong` | 1 | 2021 |
| `CUADAI` | `CUA DAI` | 28 | 2006 |
| | `CUADAI` | 7 | 2021 |
| `TIEN` | `TIEN` | 40 | 2021 |
| | `Tien` | 2 | 2021 |

→ Mặt cắt 2006 (rộng TB 1359m, 265 điểm) trộn xen kẽ với 2021 (rộng TB 829m,
203 điểm) → **bề rộng răng cưa 164↔3481m** → MASCARET nội suy phi vật lý → nổ.

**Cách sửa: KHỚP TÊN CHÍNH XÁC, không `norm()` xóa dấu cách. Lọc `topo_id`.**

### 3.4. topo_id — nhiều đợt khảo sát trong 1 file

`xns11` có **190 topo_id**: `2006`(1985), `2000`(1676), `2014`(1244), `TOPO?`(876),
`DH2020`(427), `2021_SIWRP_QHPCTT`, `SIWRR2020`, `TGLX2010`...

**18 nhánh có >1 topo_id — TUYỆT ĐỐI KHÔNG TRỘN.** Trong backbone chỉ có
**BASSAC** (2006: 123 + 2021: 40).

### 3.5. Tên nhánh cù lao trong MIKE

Nhánh cù lao dùng hậu tố `_1`, `_2`, `_3`... hoặc tên riêng:

| Sông mẹ | Nhánh cù lao MIKE |
|---|---|
| Tien | `Tien_1..Tien_9`, `CaiBe_TG`, `NamThon`, `Lap Vo` |
| BASSAC | `Hau_1..Hau_11` |
| CoChien | `CoChien_1..CoChien_4` |
| Ham Luong | `HamLuong_1..HamLuong_6` |
| CuaDai | `CuaDai_1`, `CuaDai_2`, `CuaDai_3` |

**Chiếu survey 2020 vào rất sát: d = 0.3–70m** → xác nhận MIKE khai báo đầy đủ,
không thiếu nhánh nào. Vài điểm lệch cần xem: `CC10P1`→CoChien d=900m,
`CC17P2`→CuaCungHau d=1095m.

---

## 4. QUYẾT ĐỊNH THIẾT KẾ (đã chốt, không bàn lại)

1. **Phạm vi:** toàn mạng liên thông ĐBSCL, mở rộng theo tầng. Mỗi tầng phải
   FIN CORRECTE mới lên tầng sau. **Bắt đầu từ sông Tiền, sông Hậu trước.**
2. **Cắt thượng lưu tại Tân Châu + Châu Đốc.**
   - Tân Châu = đầu nhánh `Tien`, x=520477, y=1206257, ch=0
   - Châu Đốc = đầu nhánh `BASSAC`, x=509000, y=1211161, ch=0
   - BFS từ `Tien`+`BASSAC`, chặn `MekongCam, BassacCam, GREATLAKE`
3. **Bỏ ô trữ** bằng cờ MIKE `[linkchannel]`/`[storagearea]`.
4. **MẶT CẮT — nguyên tắc CHỐT (phiên 2):**
   - **Survey 2020 (ADCP) là chuẩn CAO NHẤT — áp cho toàn mô hình nơi có**
   - **Bù bằng MIKE topo MỚI NHẤT** (`2021_SIWRP_QHPCTT`) nơi không có survey
   - **BỎ HẲN topo 2006** — qua nhiều năm lòng sông xói lở bồi lắng, không thể
     trộn số liệu cũ/mới
   - **Nội suy** nếu còn hở
   - `2006` chỉ dùng cho nội đồng nếu không có gì thay thế
5. **KẾT NỐI NHÁNH: theo MIKE, kiểm chứng bằng survey 2020.**
   **MẶT CẮT NGANG: survey 2020 trước, MIKE kiểm chứng sau.**
6. **Đồng bộ survey↔MIKE bằng TỌA ĐỘ**, không bằng tên. Kiểm lại bằng tên sau.
7. **Cù lao có survey 2020 PHẢI đưa vào.** Sau này mở rộng cả kênh trục ĐBSCL.
8. QC hình học: A_wet ≥ 90% thực đo, cao độ bờ/đáy ±1m.

---

## 5. TRẠNG THÁI

### GĐ A — XONG, ĐÚNG, KHÔNG CẦN DỰNG LẠI ✅
commit `5b1886a`. **1899 nhánh giữ, liên thông 1899/1899 (0 cô lập), 3166 nút.**
- GĐ A đọc `nwk11` (topology) — **không đụng mặt cắt** → không dính lỗi tên
- Catalog xác nhận: `NHANH CO SURVEY 2020 nhung ledger BO: (khong co)` →
  ledger giữ đủ mọi nhánh có survey, kể cả `CuaDai_1/2/3`, `Tien_1..9`, `Hau_1..11`
- **Sửa duy nhất cần làm:** `read_xns_widths` dùng `norm()` → đổi `vn_norm()`
  để `co_survey2020` nhận đủ 11 mặt cắt cửa Đại. Không ảnh hưởng kết quả 1899.

### GĐ B — ĐANG DỞ 🔄
`B_build_grid.py --subset backbone` → 15 bief, 426 PROFIL, 7 nút, 9 biên.

**Chuỗi lỗi MASCARET đã gỡ (phiên 2):**
| # | Lỗi | Crash tại | Nguyên nhân | Trạng thái |
|---|---|---|---|---|
| 1 | `End of file` | `pretrait.f90:1372` | thiếu 4 khối xcas | ✅ phiên 1 |
| 2 | `abscissa of debut not between` | — | abscDebut dùng base OFFSET | ✅ phiên 1 |
| 3 | `Error reading initial conditions` | — | format init.lig | ✅ |
| 4 | crash im lặng | `lec_sorties_` | `variablesStockees` **41 ≠ 42** | ✅ phiên 2 |
| 5 | segfault | `chainage_rezo_` | `nbZones=1` thay vì `=nb_bief` | ✅ phiên 2 |
| 6 | `Erreur 701` supercritical | biên `Z_CuaCungHau` | biên `.loi` triều sin giả + Z init mâu thuẫn | ✅ gán biên thực đo |
| 7 | `Erreur 1` Cross Section dry | section #26 | Z init sai (`bief/bmax`) | ✅ `C_init_smart.py` |
| 8 | `Erreur 701` supercritical | biên `Q_ChauDoc` | **BỀ RỘNG RĂNG CƯA 164↔3481m** do trộn topo 2006+2021 | 🔴 **ĐANG Ở ĐÂY** |

**Lỗi 8 là gốc rễ — phải sửa `get_cross_sections` trước khi làm gì khác.**

---

## 6. FORMAT MASCARET (từ file mẫu ĐÃ CHẠY FIN CORRECTE)

**Tham số sống còn:** `OFFSET=(bief−1)×1e6`, `versionCode=3`, `code=2` (REZO),
`profilsAbscAbsolu=true`, `hauteurEauMini=0.005`, `pasTemps=300`, `Strickler=40`
**Encoding:** `geometrie`/`.opt` = `latin-1`; `xcas`/`.loi`/`init.lig` = `ascii`

### xcas — khối BẮT BUỘC
- `fichReprise/fichRepriseEcr=net_ecr.rep`, `rubens/ecartInterBranch=1.0`,
  `stockage/option=1,nbSite=0`
- `ligneEau`: `modeEntree=1, fichLigEau=init.lig, formatFichLig=2, nbPts=-0`
- `variablesCalculees` = **15** giá trị
- `variablesStockees` = **42** giá trị ⚠️ (tài liệu phiên 1 ghi 41 — SAI, đó
  chính là lỗi 4. Thiếu 1 logical → crash `lec_sorties_`)
- **`planim`/`maillage`: 1 zone + 1 plage cho MỖI bief** ⚠️
  ```xml
  <nbZones>{nb_bief}</nbZones>              <!-- KHÔNG phải 1 -->
  <valeursPas>{"2.0 " × nb_bief}</valeursPas>
  <num1erProf>{prof_first[]}</num1erProf>   <!-- chỉ số PROFIL toàn cục, 1-based -->
  <numDerProf>{prof_last[]}</numDerProf>
  <nbPlages>{nb_bief}</nbPlages>
  <pasEspacePlage>{"500.0 " × nb_bief}</pasEspacePlage>
  ```
  `nbZones=1` → MASCARET cấp mảng 1 phần tử nhưng lặp theo nb_bief → **segfault
  trong `chainage_rezo_`**. Đây là lỗi 5.
- `abscDebut`/`abscFin` = abscissa PROFIL ĐẦU/CUỐI THẬT, không phải base OFFSET
- `<noeud><num>` pad đủ 5 số

### init.lig — 3 KHỐI RIÊNG X/Z/Q
```
RESULTATS CALCUL,DATE : ...
FICHIER RESULTAT MASCARET
-----------------------------------------------------------------------
 IMAX  =  426 NBBIEF=   15
 I1,I2 =      1     2 ...        <- 10 số/dòng, width 6
 X
         0.00      1478.00 ...   <- 5 giá trị/dòng, %13.2f
 Z
 Q
 FIN
```

### .loi
```
# ten <- nguon
# Temps(S) Debit        (hoặc Cote)
 S
 0.000 25300.000
```

---

## 7. ERROR PLAYBOOK

**LỖI NGHIÊM TRỌNG NHẤT — ghi đè nhánh chia mảnh:**
MIKE chia 162 nhánh thành nhiều đoạn cùng tên. `branches[name] = {...}` GHI ĐÈ
→ mất 301 đoạn. → Sửa: `branches.setdefault(name, []).append(...)`.
**KHÔNG gộp các đoạn** — chúng nối qua nút giao.

**LỖI TÊN (phiên 2) — xem §3:**
- Chữ `Đ` tiếng Việt → `vn_norm()`
- `norm()` xóa dấu cách gộp `CO CHIEN`+`COCHIEN` → khớp tên chính xác
- Trộn topo_id → lọc topo

**Các hướng SAI đã tránh:**
- Lọc ô trữ bằng "thẳng + ít điểm" → bắt nhầm cầu/đập. Dùng `[linkchannel]`.
- Lọc ô trữ bằng cao trình đáy → chỉ 8 nhánh đáy>0.
- **Chênh Z tại nút KHÔNG gây lỗi** — baseline V1 chênh 5.6m vẫn FIN CORRECTE.
  Cái gây lỗi là **h (độ sâu) quá nhỏ** và **hình học răng cưa**.
- `Z init` theo `bief/bmax` (V1) → SAI với v2 vì bief đánh số theo `sorted(mike)`
  = ALPHABET (BASSAC→Bief_1, VamNao→Bief_15). Phải dùng **BFS topology tới cửa**.

**Từ playbook cũ:**
- Điểm placeholder (0,0) trong nwk11 → lọc x<1000 & y<1000
- `mikeio` KHÔNG đọc được .xns11 → dùng `mikeio1d`
- Thiếu `dico.txt`/`FichierCas.txt` → không chạy
- `chainage` từ mikeio1d cần `pd.to_numeric()` trước khi tính

**Baseline V1 (`_archive_2026-07-14/mekong_telemac/baseline_culao_20260713/`)
CHỈ dùng học FORMAT. KHÔNG lấy thông số.** Nó FIN CORRECTE được là do
`24f_smooth_geometry.py` **hạ đáy lòng sông >10m — SAI VẬT LÝ**. v2 dùng mặt cắt
thực đo, chính xác, nhưng CHƯA BAO GIỜ chạy thông.

---

## 8. CẤU TRÚC REPO

```
mekong_telemac_v2/
├── config/config.py            # nguồn chân lý: path, tham số MASC, trạm
├── src/
│   ├── A_extract_ledger.py     # GĐ A: sổ cái (XONG)
│   ├── B_build_grid.py         # GĐ B: sinh lưới (ĐANG DỞ — cần sửa get_cross_sections)
│   ├── B_plot_grid.py          # [MỚI] vẽ lưới đang tính: trắc dọc/nút/mặt cắt/bảng
│   ├── B_plot_network.py       # [MỚI] bản đồ không gian lưới đang tính
│   ├── B_plot_proposed.py      # [MỚI] bản đồ 44 nhánh đề xuất + phân tầng
│   ├── build_catalog.py        # [MỚI] BẢNG TRA CỨU mặt cắt — dùng ĐẦU TIÊN khi cần tra
│   ├── C_assign_boundaries.py  # [MỚI] gán biên thực đo + smart init
│   ├── C_init_smart.py         # [MỚI] Z init theo BFS topology (không theo số bief)
│   ├── sync_sections.py        # đồng bộ survey↔MIKE (CẦN SỬA: vn_norm + parse_name)
│   ├── import_data.py          # build kho data_ref (CẦN SỬA: NAME_RE bỏ sót Đ)
│   ├── audit_network.py        # rà soát mạng
│   ├── check_gaps.py           # kiểm nhánh mảnh hở
│   ├── check_far_sections.py   # kiểm mặt cắt map xa
│   └── plot_network_xsec.py    # vẽ TOÀN BỘ 1899 nhánh ledger (≠ lưới đang tính)
├── data_ref/
│   ├── cross_sections/         # index.csv, sync_index.csv, sec/*.csv, qc/*.png
│   └── catalog/                # [MỚI] catalog_survey/mike/branch.csv + report
├── output/
│   ├── ledger/                 # GĐ A
│   ├── grid/backbone/          # GĐ B + plots/
│   └── audit/                  # bản đồ rà soát + proposed_*.png
└── docs/                       # file này, SESSION_LOG, PROGRESS
```

**Phân biệt 3 script vẽ (đừng nhầm):**
- `plot_network_xsec.py` → 1899 nhánh **ledger** (không phải lưới đang tính)
- `B_plot_network.py` → **lưới đang tính** (đọc geometrie)
- `B_plot_proposed.py` → **44 nhánh đề xuất** (đọc catalog, chưa sinh lưới)

---

## 9. KẾT QUẢ CATALOG (chạy `python3 src/build_catalog.py`)

```
Shapefile : 229 diem  |  Excel z : 212  |  Khop: 201  |  Tuyen ADCP: 245
MIKE      : 3009 nhanh, 11098 mat cat
Survey theo song: BASSAC 69(z=68) | Tien 72(z=71) | CoChien 34(z=30)
                  HamLuong 25(z=25) | VamNao 7(z=7)
```

**44 nhánh có survey 2020 (d<200m) — 11 chính + 33 cù lao, 1077 km, 197 mặt cắt:**

| Sông mẹ | n | Nhánh |
|---|---|---|
| Tien | 12 | `Tien`, `Tien_1..9`, `CaiBe_TG`, `NamThon` |
| BASSAC | 10 | `BASSAC`, `Hau_1..9` |
| Ham Luong | 7 | `Ham Luong`, `HamLuong_1..6` |
| CoChien | 5 | `CoChien`, `CoChien_1..4` |
| CuaDai | 4 | `CuaDai`, `CuaDai_1..3` |
| VamNao / CuaTieu / CuaCoChien / CuaCungHau / CuaDinhAn / CuaTranDe | 1 mỗi | |

**Phân tầng đề xuất (mỗi tầng FIN CORRECTE mới lên tầng sau):**
| Tầng | Nhánh | Ghi chú |
|---|---|---|
| `tien` | ~17 | Tien + Tien_1..9 + CaiBe_TG + NamThon + CuaTieu + CuaDai + CuaDai_1..3 |
| `hau` | ~12 | BASSAC + Hau_1..9 + CuaDinhAn + CuaTranDe |
| `truc` | ~24 | tien + hau + VamNao |
| `full` | 44 | + CoChien, HamLuong, CuaCoChien, CuaCungHau |

**Bảng tra cứu `data_ref/catalog/catalog_survey.csv`** — 229 điểm, mỗi điểm có:
`ten`, `vn` (bỏ dấu), `kmz`, `song`, `num`, `suf`, `x_utm`, `y_utm`, `co_z`,
`ch_survey`, `rong_excel`, **`rong_tuyen`** (từ ADCP), `z_day`, `n_pt`,
`file_excel`, + **3 nhánh MIKE gần nhất** (`mike1/2/3` + `_ch` + `_d`).
→ **Tra bằng file này TRƯỚC, đừng đoán tên.**

---

## 10. VIỆC TIẾP THEO (theo thứ tự)

1. **[NGAY] Sửa `get_cross_sections` trong `B_build_grid.py`:**
   - Khớp tên **CHÍNH XÁC** (không `norm()` xóa dấu cách)
   - **Lọc topo**: survey 2020 → `2021_SIWRP_QHPCTT` → BỎ 2006
   - Ưu tiên survey 2020 từ `catalog_survey.csv` (đã tra theo tọa độ)
   - **Kiểm bề rộng liên tục** — báo lỗi nếu nhảy >3x giữa 2 mặt cắt liền kề
   - So `rong_excel` với `rong_tuyen` (ADCP) để kiểm chứng
2. Sửa `vn_norm` trong `import_data.py`, `sync_sections.py`, `A_extract_ledger.py`
3. Sửa `parse_name` trong `sync_sections.py`: `CT`/`CĐ` = cửa, không phải `nhanh_phu`
4. Mở rộng `BACKBONE` → 44 nhánh, thêm `--subset tien/hau/truc`
5. **In hình kiểm mắt TRƯỚC KHI CHẠY**: `B_plot_grid.py` + `B_plot_network.py`
6. Chạy tầng `tien` → FIN CORRECTE → `hau` → `truc` → `full`
7. GĐ D `D_run_eval.py`: NSE/KGE tại TanChau/ChauDoc/VamNao/MyThuan/CanTho
8. Sau đó: mở rộng kênh trục toàn ĐBSCL

**Baseline V1 để so (nhưng nhớ: nó hạ đáy 10m):**
MyThuan Q_KGE=0.84, CanTho WL=0.53, TanChau Q=0.53

---

## 11. LỆNH HAY DÙNG

```bash
# Bang tra cuu (chay dau tien khi can tra ten/toa do)
python3 src/build_catalog.py

# Sinh luoi + in hinh kiem mat TRUOC khi chay
python3 src/B_build_grid.py --subset backbone
python3 src/B_plot_grid.py    --outdir output/grid/backbone
python3 src/B_plot_network.py --outdir output/grid/backbone

# Gan bien thuc do + init
python3 src/C_assign_boundaries.py --outdir output/grid/backbone \
    --start 2011-10-01 --end 2011-10-31
python3 src/C_init_smart.py --outdir output/grid/backbone \
    --z-sea 3.0 --slope 2.0 --h-min 8.0

# Chay
cd output/grid/backbone && mascaret.py mascaret.xcas 2>&1 | tail -6
grep -i "FIN CORRECTE" listing.lis && echo ">>> OK" \
  || grep -A5 "Erreur n0" listing.lis | head -10

# Trace crash (QUAN TRONG khi segfault)
mascaret.py mascaret.xcas 2>&1 | grep -E "in [a-z_0-9]+$" | head -12

# Dem so gia tri trong the xcas (KHONG phai dem so THE)
for t in valeursPas num1erProf numDerProf variablesStockees; do
  echo "$t = $(grep -o "<$t>[^<]*" mascaret.xcas | sed "s|<$t>||" | tr ' ' '\n' | grep -c .)"
done

# Ban do 44 nhanh de xuat
python3 src/B_plot_proposed.py
```
