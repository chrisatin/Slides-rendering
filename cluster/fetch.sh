#!/usr/bin/env bash
# Bring the finished render back from cvail-deploy into this deck.
set -euo pipefail
HOST=${HOST:-cvail-deploy}
SRC=${SRC:-hocv-render/rendering}
DECK=$(cd "$(dirname "$0")/.." && pwd)
rsync -az "$HOST:$SRC/assets/videos/proy_jorge_lwir.mp4" "$DECK/assets/videos/"
rsync -az "$HOST:$SRC/assets/images/proy_jorge_lwir.png" "$DECK/assets/images/"
rsync -az "$HOST:$SRC/data/results/proy_jorge_lwir.json" "$DECK/data/results/"
echo "fetched into $DECK"
