"""
Hero render for the title slide (Portada): a beam of light crossing thin haze,
refracted by a glass sphere into a caustic on the floor, beside a rough gold
sphere, with a dim indigo rim light in the deck's engines colour. The left
third of the frame stays dark so the title can sit over it.

    source ~/mitsuba3/build/setpath.sh
    python3 src/rendering/hero_portada.py --spp 1024 --width 1600 --height 900

Writes assets/images/hero_portada.png (tonemapped, denoised with OptiX when
the variant is CUDA) and the raw assets/images/hero_portada.exr.
"""
import argparse
import os

import drjit as dr
import numpy as np
import mitsuba as mi

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, 'assets', 'images')

# DESIGN.md tokens, linear RGB, so the render shares the deck's colours.
INDIGO = [0.125, 0.135, 0.85]   # #6366F1
GROUND = [0.012, 0.016, 0.03]   # close to #0B0F19 once lit


def look_at(origin, target, up=(0, 1, 0)):
    return mi.ScalarTransform4f().look_at(origin=origin, target=target, up=up)


def scene_dict(width, height, spp, haze):
    T = mi.ScalarTransform4f
    beam_from = mi.ScalarPoint3f(-3.2, 3.6, 1.4)
    beam_to = mi.ScalarPoint3f(0.55, 0.5, 0.0)
    axis = dr.normalize(beam_to - beam_from)
    snoot_end = beam_from + axis * 1.25

    return {
        'type': 'scene',
        'integrator': {'type': 'volpath', 'max_depth': 14, 'rr_depth': 8},
        'sensor': {
            'type': 'perspective',
            'fov': 34,
            'to_world': look_at((-0.6, 1.7, 8.6), (-0.7, 0.6, 0.0)),
            'medium': {'type': 'ref', 'id': 'haze'},
            'sampler': {'type': 'independent', 'sample_count': spp},
            'film': {'type': 'hdrfilm', 'width': width, 'height': height,
                     'pixel_format': 'rgb', 'rfilter': {'type': 'gaussian'}},
        },
        'haze': {
            'type': 'homogeneous',
            'albedo': 0.92,
            'sigma_t': haze,
            'phase': {'type': 'hg', 'g': 0.55},
        },
        # The haze fills a box around the scene; the box itself is invisible.
        'haze_box': {
            'type': 'cube',
            'to_world': T().translate([0, 4, 0]).scale([12, 8, 12]),
            'bsdf': {'type': 'null'},
            'interior': {'type': 'ref', 'id': 'haze'},
        },
        'floor': {
            'type': 'rectangle',
            'to_world': T().rotate([1, 0, 0], -90).scale(11),
            'bsdf': {'type': 'roughplastic', 'distribution': 'ggx', 'alpha': 0.12,
                     'diffuse_reflectance': {'type': 'rgb', 'value': [0.05, 0.055, 0.07]}},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
        'glass': {
            'type': 'sphere', 'center': [0.55, 0.62, 0.0], 'radius': 0.62,
            'bsdf': {'type': 'dielectric', 'int_ior': 1.5},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
        'gold': {
            'type': 'sphere', 'center': [1.6, 0.38, -1.0], 'radius': 0.38,
            'bsdf': {'type': 'roughconductor', 'material': 'Au', 'distribution': 'ggx', 'alpha': 0.18},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
        # Key light: a small bright sphere inside a black open tube (a snoot),
        # so it throws a beam instead of lighting the whole haze.
        'key': {
            'type': 'sphere', 'center': list(beam_from + axis * 0.2), 'radius': 0.16,
            'emitter': {'type': 'area', 'radiance': {'type': 'rgb', 'value': [4400, 4180, 3900]}},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
        'snoot': {
            'type': 'cylinder', 'p0': list(beam_from), 'p1': list(snoot_end), 'radius': 0.27,
            'bsdf': {'type': 'diffuse', 'reflectance': {'type': 'rgb', 'value': [0.01, 0.01, 0.01]}},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
        'snoot_cap': {
            'type': 'disk',
            'to_world': T().look_at(origin=list(beam_from - axis * 0.01), target=list(beam_from - axis), up=[0, 1, 0]).scale(0.28),
            'bsdf': {'type': 'diffuse', 'reflectance': {'type': 'rgb', 'value': [0.01, 0.01, 0.01]}},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
        # Rim light behind the objects, in the engines indigo.
        'rim': {
            'type': 'rectangle',
            'to_world': look_at((2.6, 4.6, -3.6), (1.0, 0.5, 0.0)).scale([1.4, 0.5, 1]),
            'emitter': {'type': 'area', 'radiance': {'type': 'rgb', 'value': [c * 5 for c in INDIGO]}},
            'exterior': {'type': 'ref', 'id': 'haze'},
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--spp', type=int, default=256)
    ap.add_argument('--width', type=int, default=1920)
    ap.add_argument('--height', type=int, default=1080)
    ap.add_argument('--passes', type=int, default=8)
    ap.add_argument('--haze', type=float, default=0.035)
    ap.add_argument('--variant', default='llvm_ad_rgb')
    ap.add_argument('--out', default='hero_portada')
    args = ap.parse_args()

    mi.set_variant(args.variant)
    scene = mi.load_dict(scene_dict(args.width, args.height, args.spp, args.haze))
    # Render in independent passes and keep the per-pixel median: haze -> glass
    # -> light paths are rare and very bright, and the median drops those
    # fireflies before the denoiser can smear them.
    passes = max(1, args.passes)
    stack = [mi.TensorXf(mi.render(scene, seed=i, spp=max(1, args.spp // passes))) for i in range(passes)]
    img = mi.TensorXf(np.median(np.stack([np.array(t) for t in stack]), axis=0)) if passes > 1 else stack[0]

    if args.variant.startswith('cuda'):
        denoiser = mi.OptixDenoiser(input_size=[img.shape[1], img.shape[0]], albedo=False, normals=False, temporal=False)
        img = denoiser(img)

    os.makedirs(OUT, exist_ok=True)
    mi.util.write_bitmap(os.path.join(OUT, args.out + '.exr'), img)
    bmp = mi.Bitmap(img).convert(mi.Bitmap.PixelFormat.RGB, mi.Struct.Type.UInt8, srgb_gamma=True)
    bmp.write(os.path.join(OUT, args.out + '.png'))
    print('wrote', os.path.join(OUT, args.out + '.png'))


if __name__ == '__main__':
    main()
