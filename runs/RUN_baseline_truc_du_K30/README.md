# RUN_baseline_truc_du_K30

VO DICH 17/07: truc_du 22 nhanh / 47 bief / K=30 dong nhat.
Q_KGE 0.48-0.92 ca 5 tram | MyThuan WL 0.653 | TanChau WL +0.319 (lan dau duong)
Froude 0.983 (o Hau_1 197m — HINH HOC, khong doi theo K: da thu K20/25/30/38/40)
Thay the baseline cu backbone K40 (VamNao 0.301)

Đóng gói: 2026-07-17 13:50:59 | git `dc8697c`

## Lưới
47 bief, 28 nút, 224 PROFIL
Mặt cắt: survey 2020 / MIKE topo `2021_SIWRP_QHPCTT` (**bỏ 2006**)

## Tham số
`pasTemps=300.0` | `tempsMax=2592000.0` |
`Strickler=30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0 30.0` | `hauteurEauMini=0.005`

## Kết quả
Thời gian chạy: **Nones** | Froude max: **0.983**

| Trạm | WL_KGE | Q_KGE |
|---|---|---|
| TanChau | 0.319 | 0.917 |
| ChauDoc | -0.326 | 0.92 |
| VamNao | None | 0.481 |
| MyThuan | 0.653 | 0.671 |
| CanTho | 0.291 | 0.488 |

## Chạy lại
```bash
bash RUN.sh              # chay vao ./work/
bash RUN.sh /tmp/thu     # hoac thu muc khac
```

## Cấu trúc
- `input/` — đủ để chạy lại ngay (1.1 MB)
- `summary/` — báo cáo + hình
- `extract/timeseries_stations.csv` — Z,Q tại 5 trạm (3605 dòng)
  (thay cho `.opt` 158MB — tái tạo bằng `RUN.sh` nếu cần đầy đủ)
- `META.json` — tham số + kết quả dạng máy đọc
