#!/usr/bin/env bash
# Render the orbiting LWIR sweep (src/rendering/proyecto_lwir.py) on cvail-01's GPU
# with cuda_ad_spectral. Frames are saved as they finish, so resubmitting resumes.
# Extra arguments go to the script, e.g.  sbatch render.sbatch --frames 360 --k 32
#SBATCH --job-name=lwir-render
#SBATCH --partition=gpu-cvail01
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=48000
#SBATCH --time=24:00:00
#SBATCH --output=logs/render-%j.out
set -euo pipefail
ROOT=$HOME/hocv-render
cd "$ROOT/mitsuba3"            # the thesis data paths are relative to this directory
set +u; source build/setpath.sh; set -u   # setpath.sh reads an unset PYTHONPATH
export THESIS_SCRIPTS=$ROOT/mitsuba3/thesis_docs/scripts
nvidia-smi -L || true

python3 "$ROOT/rendering/src/rendering/proyecto_lwir.py" --variant cuda_ad_spectral "$@"
