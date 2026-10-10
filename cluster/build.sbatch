#!/usr/bin/env bash
# Build Mitsuba 3 (thermal branch) on cvail-01's CPU partition with GCC 14. Ubuntu 22.04's
# clang is 14.0.0, which Dr.Jit refuses (14.0.0-14.0.4 miscompile it); override with CC/CXX.
# Variants come from cluster/mitsuba.conf: scalar_rgb, scalar_spectral,
# llvm_ad_spectral and cuda_ad_spectral (the one render.sbatch uses).
#SBATCH --job-name=mi3-build
#SBATCH --partition=cpu-cvail01
#SBATCH --cpus-per-task=24
#SBATCH --mem=48000
#SBATCH --time=04:00:00
#SBATCH --output=logs/build-%j.out
set -euo pipefail
ROOT=$HOME/hocv-render
cd "$ROOT/mitsuba3"

mkdir -p build
# A compiler change needs a fresh configure; the object files are rebuilt only if flags changed.
rm -rf build/CMakeCache.txt build/CMakeFiles
cp "$ROOT/rendering/cluster/mitsuba.conf" build/mitsuba.conf

CC=${CC:-gcc-14} CXX=${CXX:-g++-14} cmake -G Ninja -S . -B build -DCMAKE_BUILD_TYPE=Release
# 16 jobs keep the compiler under the 48 GB the job asks for (about 2-3 GB per translation unit).
ninja -C build -j 16

set +u; source build/setpath.sh; set -u   # setpath.sh reads an unset PYTHONPATH
python3 -c "import mitsuba as mi; print('variants', mi.variants()); mi.set_variant('llvm_ad_spectral'); import mitsuba.python.thermal as T; print('thermal data', T.data_dir())"
