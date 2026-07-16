#!/bin/bash
# Chay lai goi nay: baseline_2020_15bief
# Dong goi: 2026-07-16 17:52:14 | git f96c2d6
set -e
D=$(cd "$(dirname "$0")" && pwd)
W=${1:-$D/work}
echo "Thu muc chay: $W"
mkdir -p "$W"
cp "$D"/input/* "$W"/
cd "$W"
echo "Chay mascaret (uoc 36.7s)..."
time mascaret.py mascaret.xcas
grep -c FIN listing.lis && echo ">>> XONG: $W/ResultatsOpthyca.opt"
