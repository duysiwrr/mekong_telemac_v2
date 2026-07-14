#!/usr/bin/env bash
# commit_session.sh — Commit toàn bộ tiến độ phiên 14/07 lên git
# DÙNG: bash commit_session.sh

cd ~/mekong_telemac_v2

# khởi tạo git nếu chưa có
if [ ! -d .git ]; then
    git init
    echo "# mekong_telemac_v2" > .gitignore.tmp
fi

# dọn pycache trước khi commit
rm -rf src/__pycache__ config/__pycache__ 2>/dev/null

# thêm tất cả (trừ file nặng theo .gitignore)
git add -A

# commit
git commit -m "GD A hoan chinh (phien 14/07): 1899 nhanh lien thong 1899/1899

- Cat thuong luu tai Tan Chau/Chau Doc, chan Campuchia
- Loc linkchannel/storagearea (1043 kenh noi dong DTM/TGLX)
- SUA LOI GHI DE nhanh chia manh (162 nhanh, khoi phuc 301 doan, Cai San 59km)
- Dong bo mat cat survey 2020 <-> MIKE bang toa do (median 46m)
- Loai 3 nhanh co lap Campuchia, lien thong hoan toan
- Kho data_ref: mat cat chuan hoa + bien Q/WL
- Tai lieu: SESSION_LOG.md, PROGRESS.md, ERROR_PLAYBOOK_ref.md"

echo ""
echo "=== Trạng thái git ==="
git log --oneline -5
echo ""
echo "=== Đẩy lên GitHub (nếu đã có remote) ==="
echo "Nếu chưa có remote, tạo repo trên github rồi:"
echo "  git remote add origin https://github.com/duysiwrr/mekong_telemac_v2.git"
echo "  git branch -M main"
echo "  git push -u origin main"
echo ""
echo "Nếu đã có remote:  git push origin main"
