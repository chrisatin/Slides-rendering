"""
Slide 06 animation for the LWIR spectral simulator: the thesis's final scene
(fig72_final_scene in ~/mitsuba3/thesis_docs/scripts/figs_final_scene.py)
with the camera orbiting the spheres while the wavelength sweeps. Five spheres
of measured ECOSTRESS materials at 25 to 50 C on measured soil at 30 C, in
emitting air at 20 C under a sky at -20 C, rendered by volpathmis_thermal.
The scene comes unchanged from the thesis script; only camera, resolution,
samples and variant are set here. The air takes the sigma_t and albedo of the
midlatitude-summer preset at each wavelength.

Frame k of N puts the camera at the angle theta = 2 pi k / N on a circle
around the spheres (frame 0 is the thesis camera), so N frames make one full
turn. The band centre goes 8 -> 10 um while theta goes 0 -> pi, and 10 -> 8 um
while theta goes pi -> 2 pi, so the last frame leads back into the first and
the video loops without a jump.

Why bands and not point wavelengths: the preset is line-by-line (about 0.1 nm
apart) and its lines are far narrower than the step between frames, so a point
band per frame lands on or off a line at random and the frame flashes. Each
frame is a triangular band, 2 x --half nm at the base, read as the thesis
reads a camera band (Section 10.7, method 1): the weighted mean radiance of K
point-band renders across it. The K offsets are fixed for the whole video, so
each point band slides smoothly with the band centre and a line it crosses
moves the frame by about 1/K, not all at once.

Speed: the scene is loaded once per frame, with the film's point band at the
band centre, and for each of the K point bands only the air (sigma_t, albedo)
and the reflectances are updated in place (opaque values, so the GPU does not
compile a kernel per point band). An updated scene renders exactly what a
freshly loaded one does. The film band cannot be updated after loading, so
within a frame Planck's law is evaluated at the band centre while the line
structure of the air and the materials comes from each point band: across
+-100 nm, B changes by at most 1.3 % (8 um) and 0.2 % (10 um), and the
brightness temperature inverts the same centre-wavelength Planck curve.
Scale: one fixed range (-20 to 50 C, inferno, the thesis colormap), with the
band centre written in the corner.

Frames are written as they finish (radiance .npy + .png) and skipped when
present, so a killed job resumes where it stopped.

    cd ~/mitsuba3 && source build-restructure/setpath.sh        # local
    python3 ~/Documents/rendering/src/rendering/proyecto_lwir.py --variant llvm_ad_spectral

On the cluster, cluster/render.sbatch runs it with cuda_ad_spectral. Run from
the mitsuba3 directory (the thesis data paths are relative to it), or set
MI_THERMAL_DATA. Writes assets/videos/proy_jorge_lwir.mp4, the poster
assets/images/proy_jorge_lwir.png and data/results/proy_jorge_lwir.json.
"""
import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
THESIS = os.environ.get('THESIS_SCRIPTS', os.path.expanduser('~/mitsuba3/thesis_docs/scripts'))
sys.path.insert(0, THESIS)

import figs_final_scene as F  # noqa: E402
from figs_examples import MATERIALS  # noqa: E402
from figs_sensor import SOIL, _planck  # noqa: E402
from make_figures import _find_data  # noqa: E402

# Orbit: around the middle of the sphere arc, through the thesis camera at theta = 0.
PIVOT = (0.0, F.CAM_T[1], -1.8)
RADIUS = math.hypot(F.CAM_O[0] - PIVOT[0], F.CAM_O[2] - PIVOT[2])
HEIGHT = F.CAM_O[1]


def band_centre(theta, lo, hi):
    """8 -> 10 um over theta in [0, pi], 10 -> 8 um over [pi, 2 pi]."""
    t = theta / math.pi
    return lo + (hi - lo) * (t if t <= 1.0 else 2.0 - t)


def camera(theta):
    return ((PIVOT[0] + RADIUS * math.sin(theta), HEIGHT, PIVOT[2] + RADIUS * math.cos(theta)),
            PIVOT)


def offsets(k, seed=1):
    """K fixed, stratified offsets in [-1, 1] and their triangular weights."""
    rng = np.random.default_rng(seed)
    u = -1.0 + (np.arange(k) + rng.uniform(0, 1, k)) * (2.0 / k)
    return u, 1.0 - np.abs(u)


def band_values(mi, wl, spectra, atm):
    """sigma_t and albedo of the air, and the reflectance of each material, at wl (nm)."""
    T = mi.python.thermal
    refl = {name: float(T.interp_checked(wl, w, r, name)) for name, (w, r) in spectra.items()
            if name in dict(F.SPHERES) or name == 'soil'}
    return (float(np.interp(wl, atm.wavelength_nm, atm.sigma_t)),
            float(np.interp(wl, atm.wavelength_nm, atm.albedo)), refl)


def set_band(mi, params, sig, alb, refl):
    """Update the air and every reflectance of a loaded fig72 scene in place."""
    import drjit as dr
    v = lambda x: dr.opaque(mi.Float, x)  # noqa: E731
    params['air.sigma_t.value.value'] = v(sig)
    params['air.albedo.value.value'] = v(alb)
    for k, (name, _) in enumerate(F.SPHERES):
        params[f'sph{k}.bsdf.reflectance.value'] = v(refl[name])
        params[f'sph{k}.emitter.reflectance.value'] = v(refl[name])
    params['ground.bsdf.reflectance.value'] = v(refl['soil'])
    params['ground.emitter.reflectance.value'] = v(refl['soil'])
    params.update()


def to_frame(L, B, lut_T, vmin, vmax, label, font, height):
    import matplotlib
    from PIL import Image, ImageDraw
    ok = np.isfinite(L) & (L > 0)
    Tb = np.where(ok, np.interp(np.where(ok, L, B[0]), B, lut_T) - 273.15, vmin)
    rgb = (matplotlib.colormaps['inferno'](np.clip((Tb - vmin) / (vmax - vmin), 0, 1))[..., :3] * 255).astype(np.uint8)
    im = Image.fromarray(rgb)
    # The label sits on the sky, the coldest (darkest) part of every frame, so white reads on it.
    ImageDraw.Draw(im).text((height // 20, height // 24), label, font=font, fill=(248, 250, 252))
    return im, int((~ok).sum())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', default=F.VARIANT)
    ap.add_argument('--width', type=int, default=800)
    ap.add_argument('--height', type=int, default=400)
    ap.add_argument('--fov', type=float, default=62.0)
    ap.add_argument('--frames', type=int, default=360, help='N: frames per full turn')
    ap.add_argument('--k', type=int, default=32, help='point bands per frame')
    ap.add_argument('--spp', type=int, default=16, help='per point band')
    ap.add_argument('--half', type=float, default=100.0, help='nm, half-width of each frame\'s triangular band')
    ap.add_argument('--wl-lo', type=float, default=8000.0, help='nm')
    ap.add_argument('--wl-hi', type=float, default=10000.0, help='nm')
    ap.add_argument('--fps', type=int, default=30)
    ap.add_argument('--work', default=os.path.join(ROOT, 'build', 'proy_jorge_lwir'), help='per-frame outputs')
    ap.add_argument('--first', type=int, default=0, help='render frames [first, last) only')
    ap.add_argument('--last', type=int, default=None)
    ap.add_argument('--assemble-only', action='store_true')
    args = ap.parse_args()

    from PIL import ImageFont
    F.RES_X, F.RES_Y, F.SPP, F.FOV, F.VARIANT = args.width, args.height, args.spp, args.fov, args.variant
    vmin, vmax = F.T_SKY - 273.15, max(t for _, t in F.SPHERES) - 273.15
    lut_T = np.linspace(F.T_SKY - 15.0, 340.0, 1201)
    font = ImageFont.truetype(os.path.join(ROOT, 'assets', 'fonts', 'FiraCode[wght].ttf'), args.height // 11)
    tag = f'{args.width}x{args.height}_N{args.frames}_K{args.k}_spp{args.spp}_h{args.half:g}_bc'
    work = os.path.join(args.work, tag)
    os.makedirs(work, exist_ok=True)
    u, wts = offsets(args.k)
    thetas = [2.0 * math.pi * k / args.frames for k in range(args.frames)]
    centres = [band_centre(t, args.wl_lo, args.wl_hi) for t in thetas]

    if not args.assemble_only:
        mi = F._mi(args.variant)
        T = mi.python.thermal
        spectra = {name: T.read_ecostress(_find_data(T, 'reflectance', 'ecostress', f)) for name, f in MATERIALS}
        spectra['soil'] = T.read_ecostress(_find_data(T, 'reflectance', 'ecostress', SOIL))
        atm = T.read_atmosphere_medium(T.atmosphere_path('midlatitude_summer'))
        last = args.frames if args.last is None else min(args.last, args.frames)
        t0 = time.time()
        for k in range(args.first, last):
            npy = os.path.join(work, f'{k:05d}.npy')
            if os.path.exists(npy):
                continue
            F.CAM_O, F.CAM_T = camera(thetas[k])
            scene = F._scene(mi, centres[k], *band_values(mi, centres[k], spectra, atm))
            params = mi.traverse(scene)
            acc = np.zeros((args.height, args.width), np.float64)
            for j, (uj, wj) in enumerate(zip(u, wts)):
                set_band(mi, params, *band_values(mi, centres[k] + args.half * uj, spectra, atm))
                acc += wj * np.array(mi.render(scene, seed=k * args.k + j), dtype=np.float64)[..., 0]
            L = (acc / wts.sum()).astype(np.float32)
            B = _planck(centres[k], lut_T)
            np.save(npy, L)
            np.save(os.path.join(work, f'{k:05d}_planck.npy'), B)
            im, _ = to_frame(L, B, lut_T, vmin, vmax, f'λ = {centres[k] / 1000:.2f} µm', font, args.height)
            im.save(os.path.join(work, f'{k:05d}.png'))
            done = k - args.first + 1
            eta = (time.time() - t0) / done * (last - k - 1)
            print(f'  frame {k + 1}/{args.frames}: theta {math.degrees(thetas[k]):.0f} deg, '
                  f'band {centres[k] / 1000:.3f} um, ETA {eta / 60:.0f} min', flush=True)
        if args.first != 0 or last != args.frames:
            return

    missing = [k for k in range(args.frames) if not os.path.exists(os.path.join(work, f'{k:05d}.png'))]
    if missing:
        sys.exit(f'{len(missing)} frames missing, first {missing[0]}')
    os.makedirs(os.path.join(ROOT, 'assets', 'videos'), exist_ok=True)
    video = os.path.join(ROOT, 'assets', 'videos', 'proy_jorge_lwir.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(args.fps), '-i',
                    os.path.join(work, '%05d.png'), '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '16',
                    '-preset', 'slow', '-movflags', '+faststart', video], check=True)
    os.makedirs(os.path.join(ROOT, 'assets', 'images'), exist_ok=True)
    shutil.copy(os.path.join(work, '00000.png'), os.path.join(ROOT, 'assets', 'images', 'proy_jorge_lwir.png'))

    import matplotlib
    invalid = sum(int((~(np.isfinite(L) & (L > 0))).sum())
                  for L in (np.load(os.path.join(work, f'{k:05d}.npy')) for k in range(args.frames)))
    meta = {'frames': args.frames, 'fps': args.fps, 'turn_s': args.frames / args.fps,
            'band_centres_nm': centres, 'theta_deg': [math.degrees(t) for t in thetas],
            'band': 'triangular', 'half_width_nm': args.half, 'planck_at': 'band centre', 'point_bands_per_frame': args.k,
            'spp_per_point_band': args.spp, 'orbit': {'pivot': PIVOT, 'radius': RADIUS, 'height': HEIGHT},
            'vmin_C': vmin, 'vmax_C': vmax, 'cmap': 'inferno',
            'stops': [matplotlib.colors.to_hex(matplotlib.colormaps['inferno'](x)) for x in np.linspace(0, 1, 6)],
            'spheres_C': {n: t - 273.15 for n, t in F.SPHERES}, 'T_air_C': F.T_AIR - 273.15,
            'T_sky_C': F.T_SKY - 273.15, 'T_soil_C': F.T_SOIL - 273.15, 'invalid_px': invalid,
            'res': [args.width, args.height], 'variant': args.variant,
            'source': 'thesis_docs/scripts/figs_final_scene.py'}
    os.makedirs(os.path.join(ROOT, 'data', 'results'), exist_ok=True)
    with open(os.path.join(ROOT, 'data', 'results', 'proy_jorge_lwir.json'), 'w') as fh:
        json.dump(meta, fh, indent=2)
    print('wrote', video, f'({args.frames} frames, {args.frames / args.fps:.1f} s per turn)', '| invalid px', invalid)


if __name__ == '__main__':
    main()
