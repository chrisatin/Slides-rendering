"""
Slide 08 video for the semilleros project that took second place,
"De 2D a gemelos digitales: Creación automática de entornos 3D con IA"
(the PDF in the project root). It walks through the project's own pipeline
with the images of that PDF, crossfading from one step to the next:
satellite image -> SAM 3 segmentation -> generated trees -> BlenderGIS
buildings -> the 3D scene, then back to the start.

    python3 tools/media/semilleros_video.py

Needs pdfimages (poppler) and ffmpeg. Writes assets/videos/semilleros_2d_3d.mp4
and its poster assets/images/semilleros_2d_3d.png (the last step).
"""
import os
import shutil
import subprocess
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PDF = os.path.join(ROOT, 'De 2D a gemelos digitales Creación automática de entornos 3D con IA.pdf')
W, H, FPS = 960, 540, 30
HOLD, FADE = 1.8, 0.6   # seconds per step, seconds of crossfade

# (PDF page, image index on that page as listed by pdfimages, label)
STEPS = [
    (7, 2, '1 · Imagen satelital'),
    (12, 2, '2 · Segmentación con SAM 3'),
    (18, 2, '3 · Árboles generados'),
    (15, 2, '4 · Edificios con BlenderGIS'),
    (20, 2, '5 · Escena 3D'),
]


def extract(tmp, page, index):
    prefix = os.path.join(tmp, f'p{page}')
    subprocess.run(['pdfimages', '-png', '-f', str(page), '-l', str(page), PDF, prefix], check=True)
    return Image.open(f'{prefix}-{index:03d}.png').convert('RGB')


def cover(im):
    """Scale and centre-crop to W x H."""
    s = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
    x, y = (im.width - W) // 2, (im.height - H) // 2
    return im.crop((x, y, x + W, y + H))


def label(im, text, font):
    im = im.copy()
    d = ImageDraw.Draw(im)
    # Top left: the slide overlays its caption on the bottom of the video.
    x, y = 20, 20
    box = d.textbbox((x, y), text, font=font, anchor='lt')
    # A dark plate under the label keeps it readable over any part of the images.
    d.rectangle((box[0] - 10, box[1] - 8, box[2] + 10, box[3] + 8), fill=(11, 15, 25))
    d.text((x, y), text, font=font, anchor='lt', fill=(248, 250, 252))
    return im


def main():
    tmp = tempfile.mkdtemp(prefix='semilleros_')
    font = ImageFont.truetype(os.path.join(ROOT, 'assets', 'fonts', 'Inter[opsz,wght].ttf'), 26)
    stills = [np.asarray(label(cover(extract(tmp, p, i)), t, font), np.float32) for p, i, t in STEPS]

    frames = []
    hold, fade = int(HOLD * FPS), int(FADE * FPS)
    for k, a in enumerate(stills):
        b = stills[(k + 1) % len(stills)]
        frames += [a] * hold
        for f in range(1, fade + 1):
            t = f / (fade + 1)
            frames.append(a * (1 - t) + b * t)

    seq = os.path.join(tmp, 'seq')
    os.makedirs(seq)
    for n, fr in enumerate(frames):
        Image.fromarray(fr.astype(np.uint8)).save(os.path.join(seq, f'{n:05d}.png'))
    out = os.path.join(ROOT, 'assets', 'videos', 'semilleros_2d_3d.mp4')
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(seq, '%05d.png'),
                    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'slow',
                    '-movflags', '+faststart', out], check=True)
    Image.fromarray(stills[-1].astype(np.uint8)).save(os.path.join(ROOT, 'assets', 'images', 'semilleros_2d_3d.png'))
    shutil.rmtree(tmp)
    print('wrote', out, f'({len(frames)} frames, {len(frames) / FPS:.1f} s)')


if __name__ == '__main__':
    main()
