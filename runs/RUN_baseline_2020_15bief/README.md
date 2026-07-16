# RUN_baseline_2020_15bief

v2 chay thong lan dau voi mat cat THUC DO. Toa do 5 tram da chot.

Đóng gói: 2026-07-16 17:54:45 | git `33f823f`

## Lưới
15 bief, 7 nút, 176 PROFIL
Mặt cắt: survey 2020 / MIKE topo `2021_SIWRP_QHPCTT` (**bỏ 2006**)

## Tham số
`pasTemps=300.0` | `tempsMax=2592000.0` |
`Strickler=40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0 40.0` | `hauteurEauMini=0.005`

## Kết quả
Thời gian chạy: **36.7s** | Froude max: **0.525**

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
| TanChau | -0.647 | 0.706 |
| ChauDoc | -1.499 | 0.737 |
| VamNao | None | 0.301 |
| MyThuan | 0.58 | 0.432 |
| CanTho | 0.433 | 0.607 |

## Chạy lại
```bash
bash RUN.sh              # chay vao ./work/
bash RUN.sh /tmp/thu     # hoac thu muc khac
```

## Cấu trúc
- `input/` — đủ để chạy lại ngay (1.0 MB)
- `summary/` — báo cáo + hình
- `extract/timeseries_stations.csv` — Z,Q tại 5 trạm (3605 dòng)
  (thay cho `.opt` 158MB — tái tạo bằng `RUN.sh` nếu cần đầy đủ)
- `META.json` — tham số + kết quả dạng máy đọc
