# TÀI LIỆU BÀN GIAO — DỰ ÁN TELEMAC-1D ĐBSCL (mekong_telemac_v2)

> Đọc file này TRƯỚC khi làm bất cứ gì. Cập nhật: 16/07/2026.
> Repo: https://github.com/duysiwrr/mekong_telemac_v2

---

## 0. NGƯỜI DÙNG & NGUYÊN TẮC LÀM VIỆC (QUAN TRỌNG NHẤT)

Duy — nghiên cứu sinh SIWRR, làm luận án tích hợp mô hình thủy lực 1D
(TELEMAC/MASCARET) + machine learning cho sông Tiền/Hậu ĐBSCL.

**Yêu cầu tuyệt đối của Duy (vi phạm = làm lại):**
1. **KHÔNG suy diễn lòng vòng.** Kiểm chứng bằng dữ liệu thật TRƯỚC khi kết luận.
2. **Đối chiếu file mẫu đã chạy thông** thay vì tự nghĩ ra cách mới.
3. **In hình ra để kiểm mắt** — Duy tin hình hơn con số.
4. **Đọc code cũ để học** (repo `mekong-telemac-1d`), không kế thừa cấu trúc.
5. Phân tích độc lập, đừng hỏi Duy câu hỏi phân tích.
6. Chạy lại cái đã work trước khi dựng cái mới.

---

## 1. MÔI TRƯỜNG

| | Máy nhà | Máy cơ quan |
|---|---|---|
| BASE data | `/mnt/c/Users/win/OneDrive/De Tai/De Tai TELEMAC/MIKE11-DBSCL` | `/mnt/d/OneDrive/De Tai/De Tai TELEMAC/MIKE11-DBSCL` |
| export | `export MEKONG_MACHINE=home` | `export MEKONG_MACHINE=office` |

**venv BẮT BUỘC** (python hệ thống thiếu mikeio1d):
```bash
source ~/TELEMAC_1D_MEKONG/.venv/bin/activate
# hoặc: ~/TELEMAC_1D_MEKONG/.venv/bin/python <script>
```
TELEMAC: `~/telemac/v8p4r0`, chạy `mascaret.py mascaret.xcas`

**Đầu phiên LUÔN chạy:**
```bash
cd ~/mekong_telemac_v2 && git pull origin main
source ~/TELEMAC_1D_MEKONG/.venv/bin/activate
export MEKONG_MACHINE=office   # hoặc home
python3 -m config.config       # phải ra 5 file [OK]
```

---

## 2. DỮ LIỆU NGUỒN

- `Networks/Net_2024.nwk11.nwk11` — 3009 nhánh, 38964 điểm
- `Networks/XSecF_2011-update2023.xns11` — 2362 location_id, **8867 mặt cắt**
- `Boundary/Boundary_2011.bnd11` — 1709 biên
- `OBS/Q/Q_theo Gio/Q-Observed-for-Calibration-2011.txt` — cột: Q_ChauDoc,
  Q_TanChau, Q_VamNao, Q_CanTho, Q_MyThuan
- `OBS/.../WL-Observed-for-Calibration-2011.txt` — 35 trạm (H_ChauDoc, H_TanChau,
  H_VamKenh, H_AnThuan, H_BenTrai...)
- Survey 2020 (ADCP): `/mnt/{c,d}/.../TELEMAC_1D_MEKONG/01_data/processed/
  cross_sections/clean/` — 5 Excel (SongTien/Hau/VamNao/CoChien/HamLuong__clean.xlsx)
  + `Shapefiles/Vi tri MCN.shp` (238 điểm, EPSG:32648)

---

## 3. TRẠNG THÁI: GĐ A XONG ✅ | GĐ B ĐANG DỞ 🔄

### GĐ A — SỔ CÁI MẠNG (HOÀN THÀNH, đã commit 5b1886a)
**Kết quả: 1899 nhánh giữ, liên thông 1899/1899 (0 cô lập), 3166 nút.**
- Lý do giữ: 1860 `co_mat_cat_mike` + 42 `co_survey2020` (trước bước lọc cuối)
- Lý do loại: 1043 `linkchannel_otru`, 53 `ngoai_lien_thong`, 11 `o_tru_w=*`,
  3 `co_lap_khong_noi_truc`
- Output: `output/ledger/{branches.csv,nodes.csv,boundaries.csv,ledger.json}`
- Mặt cắt survey 2020: 176 đồng bộ tọa độ, median chiếu **46m**

### GĐ B — SINH LƯỚI (ĐANG DỞ — VIỆC TIẾP THEO)
`src/B_build_grid.py --subset backbone` sinh được:
- 11 nhánh → **15 bief** (Tien cắt 4, BASSAC cắt 2), 7 nút, 9 extremité tự do
- 426 PROFIL, geometrie + xcas + 9 file .loi + init.lig

**Chuỗi lỗi MASCARET đã gỡ (bằng đối chiếu file mẫu):**
1. ✅ `End of file` (pretrait.f90:1372) → thiếu 4 khối xcas → đã thêm
2. ✅ `abscissa of debut not between...` → abscDebut dùng base OFFSET → sửa thành
   abscissa PROFIL đầu THẬT
3. 🔄 `Error reading initial conditions` → format init.lig sai → **đã sửa, CHƯA
   CHẠY THỬ** ← VIỆC TIẾP THEO

**Lệnh chạy tiếp:**
```bash
cd ~/mekong_telemac_v2
python3 src/B_build_grid.py --subset backbone
cd output/grid/backbone
[ -f dico.txt ] || cp $(find ~/telemac -name dico.txt | head -1) .
mascaret.py mascaret.xcas
grep -i "FIN CORRECTE" listing.lis && echo ">>> OK" || grep -iE "erreur|error" listing.lis | head -8
```

---

## 4. QUYẾT ĐỊNH THIẾT KẾ (đã chốt, không bàn lại)

1. **Phạm vi:** toàn mạng liên thông ĐBSCL, mở rộng theo tầng
   (`--subset backbone` → `culao` → `full`). Mỗi tầng phải FIN CORRECTE mới lên tầng sau.
2. **Cắt thượng lưu tại Tân Châu + Châu Đốc.** MIKE lấy biên từ Kratie (Campuchia)
   nhưng số liệu thực đo ở TC/CĐ. BFS từ `Tien` + `BASSAC`, chặn
   `MekongCam, BassacCam, GREATLAKE...`
   - **Tân Châu = đầu nhánh `Tien`**, x=520477, y=1206257, ch=0
   - **Châu Đốc = đầu nhánh `BASSAC`**, x=509000, y=1211161, ch=0
3. **Bỏ ô trữ.** Lọc bằng cờ MIKE `[linkchannel]`/`[storagearea]` (kiểm chứng:
   336 cái có mặt cắt đều là DTM/TGLX nội đồng, width ≤20m, KHÔNG có kênh trục).
4. **Mặt cắt trộn:** survey 2020 nơi có, MIKE 2011 bù. Kênh trục không có 2020
   vẫn lấy từ MIKE.
5. **Đồng bộ survey↔MIKE bằng TỌA ĐỘ**, không bằng tên.
6. **QC hình học:** A_wet ≥ 90% thực đo, cao độ bờ/đáy ±1m.

---

## 5. TOPOLOGY BACKBONE (đã xác minh từ .nwk11)

```
Ba Lai     ch[0->43085]    US=Giao Hoa@13214   DS=TU_DO   ← BỎ (Giao Hoa ngoài backbone)
BASSAC     ch[0->192715]   US=TU_DO            DS=CuaDinhAn@0
CoChien    ch[0->61160]    US=Tien@124961      DS=CuaCoChien@0
CuaCoChien ch[0->30881]    US=TU_DO            DS=TU_DO
CuaCungHau ch[0->28474]    US=CuaCoChien@0     DS=TU_DO
CuaDai     ch[0->39585]    US=Tien@189512      DS=TU_DO
CuaDinhAn  ch[0->33878]    US=TU_DO            DS=TU_DO
CuaTieu    ch[0->37961]    US=Tien@189512      DS=TU_DO
CuaTranDe  ch[0->34530]    US=CuaDinhAn@0      DS=TU_DO
Ham Luong  ch[0->75388]    US=Tien@152856      DS=TU_DO     ← CÓ DẤU CÁCH trong tên
Tien       ch[0->189512]   US=TU_DO            DS=TU_DO
VamNao     ch[0->23473]    US=Tien@32675       DS=BASSAC@71252
```
→ `Tien` PHẢI cắt 4 bief (tại 32675, 124961, 152856), `BASSAC` cắt 2 (tại 71252).

Số mặt cắt: BASSAC 163, Ham Luong 79, CoChien 70, Tien 42 (đều, TB 4576m,
max hở 7727m — CHẤP NHẬN ĐƯỢC), VamNao 6, các cửa 6-35.

---

## 6. FORMAT FILE MASCARET (từ file mẫu ĐÃ CHẠY FIN CORRECTE)

**Tham số sống còn:** OFFSET=(bief−1)×1e6, versionCode=3, code=2,
profilsAbscAbsolu=true, hauteurEauMini=0.005, pasTemps=300, Strickler=40
**Encoding:** geometrie/.opt = `latin-1`; xcas/.loi/init.lig = `ascii` (KHÔNG dấu tiếng Việt)

### geometrie
```
PROFIL Bief_1 Tien_s0_365_a 0.0
<y> <z> B          ← y tăng nghiêm ngặt
```

### xcas — khối BẮT BUỘC (thiếu → "End of file")
`fichReprise/fichRepriseEcr=net_ecr.rep`, `rubens/ecartInterBranch=1.0`,
`stockage/option=1,nbSite=0`, `ligneEau` phải có
`modeEntree=1, fichLigEau=init.lig, formatFichLig=2, nbPts=-0`
- `variablesCalculees`: **15** giá trị
- `variablesStockees`: **41** giá trị (chuỗi cụ thể trong `VAR_STOCK` của B_build_grid.py)
- **`abscDebut`/`abscFin` = abscissa PROFIL ĐẦU/CUỐI THẬT**, KHÔNG phải base OFFSET
  (mẫu: Bief_2 abscDebut=1003784.0 chứ không phải 1000000.0)
- `<noeud><num>` pad đủ 5 số (thiếu điền 0)

### init.lig — 3 KHỐI RIÊNG (không phải mỗi dòng 1 bộ XZQ!)
```
RESULTATS CALCUL,DATE : ...
FICHIER RESULTAT MASCARET
-----------------------------------------------------------------------
 IMAX  =  492 NBBIEF=   71
 I1,I2 =      1     2 ...        ← 10 số/dòng, width 6
 X
         0.00      1478.00 ...   ← 5 giá trị/dòng, width 13, format %13.2f
 Z
         9.00         9.00 ...
 Q
     10000.00     10000.00 ...
 FIN
```

### .loi
```
# ten
# Temps(S) Debit     (hoặc Cote)
 S
 0.000 25300.000
```

---

## 7. LỖI ĐÃ GẶP & CÁCH TRÁNH (ERROR PLAYBOOK)

**LỖI NGHIÊM TRỌNG NHẤT — ghi đè nhánh chia mảnh:**
MIKE chia 162 nhánh thành nhiều đoạn cùng tên (tại mỗi nút giao). Code
`branches[name] = {...}` GHI ĐÈ → mất 301 đoạn (Cái Sắn 59km còn 1km).
→ Sửa: `branches[name]` là LIST (`setdefault().append()`).
→ **KHÔNG gộp các đoạn lại** — chúng nối qua nút giao, gộp sẽ phá nút.

**Các hướng SAI đã tránh:**
- Lọc ô trữ bằng "thẳng + ít điểm" → bắt nhầm cầu/đập/kênh đào. Dùng `[linkchannel]`.
- Lọc ô trữ bằng cao trình đáy → chỉ 8 nhánh đáy>0, không lộ ra.

**Từ playbook cũ:**
- Điểm placeholder (0,0) trong nwk11 → lọc x<1000 & y<1000
- `mikeio` KHÔNG đọc được .xns11 → dùng `mikeio1d`
- Init phẳng → khô đáy → SMART INIT: `z = max(dốc 9→3m, bed_min + 5.0)`
- Thiếu dico.txt/FichierCas.txt → không chạy
- Script 70 cũ gọi 26/27 chứ không phải backbone 24b/24d

---

## 8. CẤU TRÚC REPO

```
mekong_telemac_v2/
├── config/config.py           # nguồn chân lý: path, tham số MASC, trạm STA
├── src/
│   ├── A_extract_ledger.py    # GĐ A: sổ cái (XONG)
│   ├── B_build_grid.py        # GĐ B: sinh lưới (ĐANG DỞ)
│   ├── sync_sections.py       # đồng bộ survey↔MIKE bằng tọa độ
│   ├── import_data.py         # build kho data_ref
│   ├── audit_network.py       # rà soát mạng
│   ├── check_gaps.py          # kiểm nhánh mảnh hở
│   ├── check_far_sections.py  # kiểm mặt cắt map xa
│   └── plot_network_xsec.py   # VẼ mạng + vị trí mặt cắt (kiểm mắt)
├── data_ref/cross_sections/   # index.csv, sync_index.csv, sec/*.csv, qc/*.png
├── output/ledger/             # sổ cái GĐ A
├── output/grid/backbone/      # lưới GĐ B
├── output/audit/              # bản đồ rà soát
└── docs/                      # SESSION_LOG, PROGRESS, ERROR_PLAYBOOK_ref, file này
```

**Thứ tự chạy lại từ đầu (nếu ledger sai):**
A (lần 1) → sync_sections → A (lần 2, có survey) → import_data → audit

---

## 9. VIỆC TIẾP THEO (theo thứ tự)

1. **[NGAY] Chạy thử B backbone** → tìm FIN CORRECTE. Nếu lỗi, đối chiếu file mẫu.
2. **GĐ B tầng culao** → thêm nhánh cù lao có survey.
3. **GĐ C** `C_assign_geometry_qc.py`: gán mặt cắt trộn 2020/2011 + QC
   (A_wet≥90%, bờ/đáy ±1m). Thay hẳn script 24f cũ (24f SAI VẬT LÝ: dịch đứng cả
   bờ khi làm mượt).
4. **GĐ D** `D_run_eval.py`: biên thực đo (Q_TanChau, Q_ChauDoc + 7 Z cửa) +
   smart init + chạy + NSE/KGE tại TanChau/ChauDoc/VamNao/MyThuan/CanTho.
   Baseline cũ để so: MyThuan Q_KGE=0.84, CanTho WL=0.53, TanChau Q=0.53.
5. Sau đó: mở rộng full 1899 nhánh.

**Lưu ý:** file mẫu chạy thông (geometrie, mascaret.xcas, init.lig, *.loi của
baseline 71 bief) nằm ở `_archive_2026-07-14/mekong_telemac/baseline_culao_20260713/`
hoặc repo cũ GitHub `duysiwrr/mekong-telemac-1d`. ĐÂY LÀ TÀI LIỆU THAM CHIẾU
QUAN TRỌNG NHẤT khi gỡ lỗi MASCARET.
