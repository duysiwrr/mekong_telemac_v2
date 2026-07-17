#!/bin/bash
# Chay lai goi nay: baseline_truc_du_K30
# Dong goi: 2026-07-17 13:50:59 | git dc8697c
set -e
D=$(cd "$(dirname "$0")" && pwd)
W=${1:-$D/work}
echo "Thu muc chay: $W"
mkdir -p "$W"
cp "$D"/input/* "$W"/
cd "$W"
echo "Chay mascaret (uoc ~35s)..."
time mascaret.py mascaret.xcas
grep -c FIN listing.lis && echo ">>> XONG: $W/ResultatsOpthyca.opt"
