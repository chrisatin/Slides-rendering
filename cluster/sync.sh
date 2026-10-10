#!/usr/bin/env bash
# Copy what the LWIR render needs to cvail-deploy (cvail-01), from this machine:
#   ~/mitsuba3 source (no .git, builds, papers or the 5 GB data tree)
#   + thesis_docs/scripts + the spectral data the scene reads
#   + this deck's render script, fonts and cluster jobs.
# Remote layout: ~/hocv-render/{mitsuba3,rendering}. Safe to re-run: rsync sends only changes
# and never touches the remote build/ directory.
set -euo pipefail
HOST=${HOST:-cvail-deploy}
DEST=${DEST:-hocv-render}
MI=${MI:-$HOME/mitsuba3}
DECK=$(cd "$(dirname "$0")/.." && pwd)

ssh "$HOST" "mkdir -p $DEST/mitsuba3/thesis_docs/figures $DEST/mitsuba3/thesis_docs/data $DEST/rendering/cluster/logs"

rsync -az --info=stats1 \
  --exclude '/build*' --exclude '/.git' --exclude '/review' --exclude '/thermal_docs' \
  --exclude '/spectral_data' --exclude '/thesis_docs' --exclude '/out' --exclude '__pycache__' \
  "$MI/" "$HOST:$DEST/mitsuba3/"

rsync -az --info=stats1 --exclude '__pycache__' \
  "$MI/thesis_docs/scripts/" "$HOST:$DEST/mitsuba3/thesis_docs/scripts/"

# Only the data the scene reads: the ECOSTRESS reflectances and one atmosphere preset.
rsync -azR --info=stats1 \
  "$MI/./spectral_data/README.md" \
  "$MI/./spectral_data/reflectance/ecostress" \
  "$MI/./spectral_data/atmosphere/midlatitude_summer" \
  "$HOST:$DEST/mitsuba3/"

rsync -azR --info=stats1 --exclude '__pycache__' --exclude 'logs/' \
  "$DECK/./src/rendering" "$DECK/./assets/fonts" "$DECK/./cluster" \
  "$HOST:$DEST/rendering/"

echo "synced to $HOST:~/$DEST"
