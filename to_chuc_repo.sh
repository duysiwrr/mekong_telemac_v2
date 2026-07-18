#!/usr/bin/env bash
# to_chuc_repo.sh — DON RAC + PHAN LOAI src/ tools/ tools_ledger/
# Chay tu goc repo: bash to_chuc_repo.sh
set -e
cd ~/mekong_telemac_v2

echo "=========================================="
echo "1. XOA RAC Zone.Identifier + ban plot_6vung thua trong src/"
echo "=========================================="
find . -name "*:Zone.Identifier" -delete
rm -f src/plot_6vung.py          # da co ban trong tools/
echo "   OK"

echo "=========================================="
echo "2. TAO tools/ va tools/ledger/"
echo "=========================================="
mkdir -p tools tools/ledger

echo "=========================================="
echo "3. git mv — SCRIPT VE/DOI CHIEU (dung lai, khong phai pipeline) -> tools/"
echo "=========================================="
# Tieu chi: bo di van chay lai duoc nghien cuu A->B->C->D->E
for f in B_plot_grid.py B_plot_network2.py B_plot_proposed.py \
         F_catalog_3nguon.py plot_network_xsec.py; do
    [ -f "src/$f" ] && git mv "src/$f" "tools/$f" && echo "   src/$f -> tools/"
done

echo "=========================================="
echo "4. git mv — GD A da dong (giu de suy luan) -> tools/ledger/"
echo "=========================================="
for f in audit_network.py check_gaps.py check_far_sections.py \
         import_data.py sync_sections.py; do
    [ -f "src/$f" ] && git mv "src/$f" "tools/ledger/$f" && echo "   src/$f -> tools/ledger/"
done

echo "=========================================="
echo "5. SUA sys.path trong file vua chuyen (them 1 cap .parent)"
echo "=========================================="
# tools/X.py va tools/ledger/X.py can tro len goc repo de import config
for f in tools/*.py; do
    if grep -q "resolve().parent))" "$f" 2>/dev/null; then
        sed -i 's|resolve().parent))|resolve().parent.parent))|' "$f"
        echo "   sua sys.path: $f"
    fi
done
for f in tools/ledger/*.py; do
    if grep -q "resolve().parent))" "$f" 2>/dev/null; then
        sed -i 's|resolve().parent))|resolve().parent.parent.parent))|' "$f"
        echo "   sua sys.path: $f"
    fi
done

echo "=========================================="
echo "6. KET QUA"
echo "=========================================="
echo "--- src/ (PIPELINE cot loi — chay lai nghien cuu) ---"
ls src/
echo "--- tools/ (ve, doi chieu) ---"
ls tools/
echo "--- tools/ledger/ (GD A da dong) ---"
ls tools/ledger/

echo ""
echo "=========================================="
echo "7. KIEM pipeline con chay (import config)"
echo "=========================================="
python3 -m py_compile src/*.py && echo "   src/ cu phap OK"
python3 -c "from config.config import CFG; print('   config OK')"

cat <<'EOF'

=========================================================
BUOC TIEP — chay tay sau khi xem ket qua tren:

# Kiem cac file da chuyen van chay (sys.path dung)
python3 tools/B_plot_network2.py --outdir output/grid/paA 2>&1 | tail -3
python3 tools/plot_6vung.py 2>&1 | tail -2

# Commit
git add -A
git commit -m "Cau truc: src/ chi giu PIPELINE, tools/ giu script ve+GD A

src/ (chay lai nghien cuu A->B->C->D->E):
  config, A_extract_ledger, B_build_grid, C_assign_boundaries,
  C_init_smart, D_run_eval, E_package_run, G_doc_bnd11, build_catalog

tools/ (ve + doi chieu, bo di van chay duoc):
  B_plot_grid, B_plot_network2, B_plot_proposed, F_catalog_3nguon,
  plot_network_xsec, plot_6vung

tools/ledger/ (GD A da dong, giu de suy luan sua loi):
  audit_network, check_gaps, check_far_sections, import_data, sync_sections

Xoa rac Zone.Identifier. Sua sys.path cho file chuyen thu muc."
git push origin v3-kenh-truc

EOF
