#!/usr/bin/env bash
# Run on cvail-deploy: build on the CPU partition, then render on the GPU once the build succeeds.
#   ~/hocv-render/rendering/cluster/submit.sh [render args...]
# SKIP_BUILD=1 submits only the render (after a successful earlier build).
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p logs
if [ "${SKIP_BUILD:-0}" = 1 ]; then
  sbatch render.sbatch "$@"
else
  build=$(sbatch --parsable build.sbatch)
  echo "build job $build"
  sbatch --dependency=afterok:"$build" render.sbatch "$@"
fi
