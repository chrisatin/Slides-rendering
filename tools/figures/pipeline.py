"""
Figure pipeline for the presentation: build a figure, check its SVG geometry,
have its PNG reviewed.

    python3 tools/figures/pipeline.py run    --id <stem or function>
    python3 tools/figures/pipeline.py check  --id <stem or function>
    python3 tools/figures/pipeline.py review --id <stem or function>

A figure is one SVG in assets/diagrams/, built from one of two sources:
  - a Typst/CeTZ drawing diagrams_src/<stem>.typ (lib/diagram_parts.typ),
    compiled with the deck's fonts from assets/fonts/;
  - a matplotlib function in tools/figures/make_figures.py or figs_*.py whose
    save(fig, name) writes the SVG and lists it in data/results/<function>.json.
`--id` is an SVG stem or a function name.

Every command prints a short report with the overall `[OK]` or `[FAIL]` on the
first line. `review` sends a PNG preview of each SVG, on the slide background,
to the Gemini vision API (google-genai SDK; GEMINI_API_KEY or the key file
~/.config/figure_pipeline/gemini_key). Logs, previews and raw replies go to
/tmp/figure_pipeline/, never to the report.

assets/diagrams/manifest.json holds one entry per SVG: its source, its path,
the slide (<section id>) of index.html that shows it, and the command that
builds it. pipeline_mcp.py exposes the three commands as MCP tools.
"""
import argparse
import glob
import json
import math
import os
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIGS = os.path.join(ROOT, 'assets', 'diagrams')
FONTS = os.path.join(ROOT, 'assets', 'fonts')
TYP_SRC = os.path.join(ROOT, 'diagrams_src')
RESULTS = os.path.join(ROOT, 'data', 'results')
MANIFEST = os.path.join(FIGS, 'manifest.json')
INDEX = os.path.join(ROOT, 'index.html')
# Optional shell script sourced before a matplotlib run, e.g. a Mitsuba setpath.sh for figures that render.
SETPATH = os.environ.get('FIGURE_PIPELINE_SETPATH')
WORK = os.environ.get('FIGURE_PIPELINE_WORK', '/tmp/figure_pipeline')
SLIDE_BG = '#0B0F19'


# ---------------------------------------------------------------- manifest

def _rel(path):
    # Always forward slashes: the manifest and its commands must read the same on Windows and Linux.
    return os.path.relpath(path, ROOT).replace(os.sep, '/')


def _static_outputs():
    """{svg stem: source} from literal save() calls in tools/figures/*.py and
    from the Typst drawings in diagrams_src/."""
    found = {}
    for path in sorted(glob.glob(os.path.join(HERE, '*.py'))):
        func = None
        with open(path) as f:
            for line in f:
                m = re.match(r'def (\w+)\(', line)
                if m:
                    func = m.group(1)
                for name in re.findall(r"\bsave\(\s*\w+\s*,\s*['\"]([\w.-]+)['\"]", line):
                    if func:
                        found[name] = f'{_rel(path)}:{func}'
    for path in sorted(glob.glob(os.path.join(TYP_SRC, '*.typ'))):
        found[os.path.splitext(os.path.basename(path))[0]] = _rel(path)
    return found


def _module_of(func):
    for path in sorted(glob.glob(os.path.join(HERE, '*.py'))):
        with open(path) as f:
            if re.search(rf'^def {re.escape(func)}\(', f.read(), re.M):
                return _rel(path)
    return None


def slide_of(svg_rel):
    """`#id` of the index.html slide that shows the SVG, or None."""
    if not os.path.exists(INDEX):
        return None
    with open(INDEX) as f:
        html = f.read()
    i = html.find(svg_rel.replace(os.sep, '/'))
    if i < 0:
        return None
    ids = re.findall(r'<section\b[^>]*\bid="([^"]+)"', html[:i])
    return f'#{ids[-1]}' if ids else None


def _is_typst(source):
    return bool(source) and source.endswith('.typ')


def _func_of(entry):
    source = entry.get('source')
    return source.split(':')[1] if source and ':' in source else None


def _entry(stem, source):
    svg_rel = f'assets/diagrams/{stem}.svg'
    if _is_typst(source):
        command = f'typst compile --root . --font-path assets/fonts --format svg {source} {svg_rel}'
    else:
        func = source.split(':')[1] if source else None
        command = f'python3 tools/figures/make_figures.py {func}' if func else None
    return {'id': stem, 'source': source, 'svg_path': svg_rel, 'slide': slide_of(svg_rel),
            'params': {'command': command}}


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST) as f:
            return {e['id']: e for e in json.load(f)['figures']}
    outputs = _static_outputs()
    manifest = {}
    for svg in sorted(glob.glob(os.path.join(FIGS, '*.svg'))):
        stem = os.path.splitext(os.path.basename(svg))[0]
        source = outputs.get(stem) or outputs.get(re.sub(r'_([a-z]|panels)$', '', stem))
        manifest[stem] = _entry(stem, source)
    save_manifest(manifest)
    return manifest


def save_manifest(manifest):
    os.makedirs(FIGS, exist_ok=True)
    with open(MANIFEST, 'w') as f:
        json.dump({'figures': [manifest[k] for k in sorted(manifest)]}, f, indent=2)
        f.write('\n')


def resolve(fig_id):
    """(manifest, entries) for an SVG stem or a function name; a stem whose
    source changed since the manifest was written gets a fresh entry."""
    manifest = load_manifest()
    source = _static_outputs().get(fig_id)
    if fig_id in manifest or source:
        entry = manifest.get(fig_id)
        if entry is None or (source and source != entry.get('source')):
            entry = _entry(fig_id, source)
            manifest[fig_id] = entry
            save_manifest(manifest)
        return manifest, [entry]
    return manifest, [e for e in manifest.values() if _func_of(e) == fig_id]


# --------------------------------------------------------------------- run

def _failure(log):
    """The exception line of a failed run and the innermost traceback frame
    inside tools/figures/, with its source line."""
    with open(log) as f:
        lines = [l.rstrip() for l in f if l.strip()]
    if not lines:
        return 'no output'
    err = lines[-1].strip()[:200]
    for i in range(len(lines) - 1, -1, -1):
        m = re.match(r'\s*File "([^"]+)", line (\d+), in (\S+)', lines[i])
        if m and os.path.dirname(os.path.abspath(m.group(1))) == HERE:
            code = lines[i + 1].strip()[:120] if i + 1 < len(lines) else ''
            return f'{err}\nat {os.path.basename(m.group(1))}:{m.group(2)} in {m.group(3)}: {code}'
    return err


def _record(stems, source, seconds):
    manifest = load_manifest()                  # re-read: another run may have saved meanwhile
    for stem in stems:
        entry = _entry(stem, source)
        entry['params']['seconds'] = round(seconds, 1)
        manifest[stem] = entry
    save_manifest(manifest)


def run_typst(stem, timeout=600):
    src = os.path.join(TYP_SRC, f'{stem}.typ')
    out = os.path.join(FIGS, f'{stem}.svg')
    os.makedirs(FIGS, exist_ok=True)
    t0 = time.time()
    proc = subprocess.run(['typst', 'compile', '--root', ROOT, '--font-path', FONTS, '--format', 'svg', src, out],
                          capture_output=True, text=True, timeout=timeout)
    dt = time.time() - t0
    if proc.returncode != 0:
        os.makedirs(WORK, exist_ok=True)
        log = os.path.join(WORK, f'{stem}.typst.log')
        with open(log, 'w') as f:
            f.write(proc.stderr)
        first = re.findall(r'^error: .*(?:\n.*){0,3}', proc.stderr, re.M)
        return f'[FAIL] run {stem}: typst exit {proc.returncode}\n{(first or [proc.stderr[:300]])[0]}\n(log {log})'
    warnings = [l for l in proc.stderr.splitlines() if l.startswith('warning')]
    _record([stem], _rel(src), dt)
    tail = f'\n{len(warnings)} warning(s): {warnings[0][:160]}' if warnings else ''
    return f'[OK] run {stem}: {_rel(out)} in {dt:.1f} s, manifest updated{tail}'


def run(fig_id, timeout=3600):
    """Build the figure behind fig_id: compile its Typst drawing, or run its
    matplotlib function and record the SVGs that save() reports."""
    if os.path.exists(os.path.join(TYP_SRC, f'{fig_id}.typ')):
        return run_typst(fig_id, min(timeout, 600))
    _, entries = resolve(fig_id)
    sources = {e['source'] for e in entries if e['source']}
    if len(sources) > 1:
        return f'[FAIL] run {fig_id}\nambiguous: written by {", ".join(sorted(sources))}'
    if sources and _is_typst(next(iter(sources))):
        return run_typst(os.path.splitext(os.path.basename(sources.pop()))[0], min(timeout, 600))
    func = sources.pop().split(':')[1] if sources else fig_id
    module = _module_of(func)
    if module is None:
        return f'[FAIL] run {fig_id}\nno diagrams_src/{fig_id}.typ and no function {fig_id}() in tools/figures/*.py'
    os.makedirs(WORK, exist_ok=True)
    log = os.path.join(WORK, f'{func}.run.log')
    result = os.path.join(RESULTS, f'{func}.json')
    setpath = f'source {SETPATH} >/dev/null 2>&1; ' if SETPATH else ''
    cmd = f'{setpath}cd {HERE} && {sys.executable} make_figures.py {func}'
    t0 = time.time()
    with open(log, 'w') as f:
        try:
            code = subprocess.run(['bash', '-c', cmd], stdout=f, stderr=subprocess.STDOUT,
                                  stdin=subprocess.DEVNULL, timeout=timeout).returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    dt = time.time() - t0
    if code != 0:
        return f'[FAIL] run {func}: exit {code} after {dt:.0f} s\n{_failure(log)}\n(log {log})'
    try:
        if os.stat(result).st_mtime < t0:
            raise FileNotFoundError
        with open(result) as f:
            outputs = json.load(f).get('outputs', [])
    except (FileNotFoundError, json.JSONDecodeError):
        return f'[FAIL] run {func}: exit 0 in {dt:.0f} s but {_rel(result)} was not written\n(log {log})'
    written = sorted(os.path.splitext(os.path.basename(p))[0] for p in outputs
                     if p.endswith('.svg') and os.path.exists(os.path.join(ROOT, p))
                     and os.stat(os.path.join(ROOT, p)).st_mtime >= t0)
    if not written:
        return f'[FAIL] run {func}: exit 0 in {dt:.0f} s but save() reported no SVG\n(log {log})'
    _record(written, f'{module}:{func}', dt)
    shown = ', '.join(written[:8]) + (f' (+{len(written) - 8})' if len(written) > 8 else '')
    return f'[OK] run {func}: {len(written)} SVG in {dt:.0f} s, manifest updated\n{shown}'


# ------------------------------------------------------------ SVG geometry

SVG_NS = '{http://www.w3.org/2000/svg}'
XLINK = '{http://www.w3.org/1999/xlink}href'
SKIP = {'defs', 'clipPath', 'mask', 'marker', 'pattern', 'metadata', 'style', 'title', 'desc',
        'linearGradient', 'radialGradient', 'symbol'}
NUM = r'[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?'
IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
SHAPES = ('path', 'polyline', 'polygon', 'line', 'rect', 'circle', 'ellipse')
COLOUR_NAMES = {'#6366f1': 'indigo', '#ec4899': 'pink', '#0c9ee2': 'sky', '#ea580c': 'orange',
                '#059669': 'emerald', '#ef4444': 'red', '#0d9488': 'teal', '#d97706': 'amber',
                '#818cf8': 'light indigo', '#38bdf8': 'cyan', '#f8fafc': 'ink', '#94a3b8': 'grey',
                '#334155': 'border grey'}


def _mul(m, n):
    a, b, c, d, e, f = m
    A, B, C, D, E, F = n
    return (a * A + c * B, b * A + d * B, a * C + c * D, b * C + d * D,
            a * E + c * F + e, b * E + d * F + f)


def _apply(m, x, y):
    return m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]


def _transform(text):
    m = IDENT
    for name, args in re.findall(r'(\w+)\s*\(([^)]*)\)', text or ''):
        v = [float(x) for x in re.findall(NUM, args)]
        if name == 'matrix':
            t = tuple(v)
        elif name == 'translate':
            t = (1, 0, 0, 1, v[0], v[1] if len(v) > 1 else 0)
        elif name == 'scale':
            t = (v[0], 0, 0, v[1] if len(v) > 1 else v[0], 0, 0)
        elif name == 'rotate':
            r = math.radians(v[0])
            t = (math.cos(r), math.sin(r), -math.sin(r), math.cos(r), 0, 0)
            if len(v) == 3:
                t = _mul(_mul((1, 0, 0, 1, v[1], v[2]), t), (1, 0, 0, 1, -v[1], -v[2]))
        elif name == 'skewX':
            t = (1, 0, math.tan(math.radians(v[0])), 1, 0, 0)
        elif name == 'skewY':
            t = (1, math.tan(math.radians(v[0])), 0, 1, 0, 0)
        else:
            continue
        m = _mul(m, t)
    return m


def _path_polys(d):
    """Subpaths of a path as point lists; curves are kept as control polygons,
    which contain the curve."""
    tokens = re.findall(r'[MmLlHhVvCcSsQqTtAaZz]|' + NUM, d or '')
    polys, cur, x, y, sx, sy, cmd, i = [], [], 0.0, 0.0, 0.0, 0.0, None, 0
    sizes = {'M': 2, 'L': 2, 'H': 1, 'V': 1, 'C': 6, 'S': 4, 'Q': 4, 'T': 2, 'A': 7, 'Z': 0}
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
            if cmd in 'Zz':
                if cur:
                    cur.append((sx, sy))
                    polys.append(cur)
                cur, x, y = [], sx, sy
                continue
        if cmd is None:
            break
        n = sizes[cmd.upper()]
        v = [float(t) for t in tokens[i:i + n]]
        i += n
        if len(v) < n:
            break
        rel = cmd.islower()
        ox, oy = (x, y) if rel else (0.0, 0.0)
        up = cmd.upper()
        if up == 'M':
            if len(cur) > 1:
                polys.append(cur)
            x, y = ox + v[0], oy + v[1]
            sx, sy, cur = x, y, [(x, y)]
            cmd = 'l' if rel else 'L'
            continue
        if not cur:
            cur = [(x, y)]
        if up == 'H':
            x = ox + v[0] if rel else v[0]
            pts = [(x, y)]
        elif up == 'V':
            y = (y + v[0]) if rel else v[0]
            pts = [(x, y)]
        elif up == 'A':
            x, y = ox + v[5], oy + v[6]
            pts = [(x, y)]
        else:
            pts = [(ox + v[k], oy + v[k + 1]) for k in range(0, n, 2)]
            x, y = pts[-1]
        cur.extend(pts)
    if len(cur) > 1:
        polys.append(cur)
    return polys


def _style(el, inherited):
    s = dict(inherited)
    for key in ('fill', 'stroke', 'stroke-width', 'paint-order', 'opacity', 'display'):
        if el.get(key) is not None:
            s[key] = el.get(key).strip()
    for part in (el.get('style') or '').split(';'):
        if ':' in part:
            k, v = part.split(':', 1)
            s[k.strip()] = v.strip()
    return s


def _stroked(s):
    if s.get('stroke', 'none') in ('none', 'transparent'):
        return False
    try:
        return float(re.findall(NUM, s.get('stroke-width', '1'))[0]) > 0
    except IndexError:
        return True


def _clip_segment(x0, y0, x1, y1, box):
    """Liang-Barsky: the parameter range of the segment inside box, or None."""
    xmin, ymin, xmax, ymax = box
    dx, dy = x1 - x0, y1 - y0
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x0 - xmin), (dx, xmax - x0), (-dy, y0 - ymin), (dy, ymax - y0)):
        if p == 0:
            if q < 0:
                return None
        else:
            t = q / p
            if p < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return None
    return t0, t1


class SvgGeometry:
    """Glyph boxes of every text item and segments of every stroked curve, in
    the SVG user space of the root, with the order in which they are painted.

    Matplotlib SVGs name their groups (text_3, line2d_7). Typst SVGs carry no
    ids: a text run is a <g> holding only glyph <use>s, and every other stroked
    shape counts as a curve."""

    TEXT_ID = re.compile(r'^text_\d+$')
    NOT_CURVE = re.compile(r'^(xtick|ytick|patch)_')

    def __init__(self, path):
        parser = ET.XMLParser(target=ET.TreeBuilder(insert_comments=True))
        self.root = ET.parse(path, parser).getroot()
        self.ids = {el.get('id'): el for el in self.root.iter() if el.get('id')}
        self.texts = {}       # key -> {'label', 'glyphs': [box], 'order', 'halo'}
        self.curves = {}      # key -> {'segments': [(x0, y0, x1, y1)], 'order'}
        self.order = 0
        self.typst = not any((el.get('id') or '').startswith('figure_') for el in self.root.iter())
        self._walk(self.root, IDENT, {}, None, 'shape' if self.typst else None, None, False)

    def _clip_box(self, el, m):
        ref = re.match(r'url\(#([^)]+)\)', el.get('clip-path') or '')
        clip = self.ids.get(ref.group(1)) if ref else None
        if clip is None:
            return None
        pts = []
        for child in clip.iter():
            tag = child.tag.replace(SVG_NS, '')
            cm = _mul(m, _transform(child.get('transform')))
            if tag == 'rect':
                x, y = float(child.get('x', 0)), float(child.get('y', 0))
                w, h = float(child.get('width', 0)), float(child.get('height', 0))
                pts += [_apply(cm, px, py) for px, py in ((x, y), (x + w, y), (x, y + h), (x + w, y + h))]
            elif tag == 'path':
                pts += [_apply(cm, *p) for poly in _path_polys(child.get('d')) for p in poly]
        if not pts:
            return None
        xs, ys = zip(*pts)
        return (min(xs), min(ys), max(xs), max(ys))

    def _walk(self, el, m, style, text_key, curve_key, clip, excluded):
        if el.tag is ET.Comment:
            if text_key and self.texts[text_key]['label'] is None:
                self.texts[text_key]['label'] = (el.text or '').strip()
            return
        tag = el.tag.replace(SVG_NS, '') if isinstance(el.tag, str) else ''
        if tag in SKIP:
            return
        style = _style(el, style)
        if style.get('display') == 'none':
            return
        m = _mul(m, _transform(el.get('transform')))
        box = self._clip_box(el, m)
        if box is not None:
            clip = box if clip is None else (max(clip[0], box[0]), max(clip[1], box[1]),
                                             min(clip[2], box[2]), min(clip[3], box[3]))
        gid = el.get('id') or ''
        typst_run = self.typst and tag == 'g' and len(el) > 0 and all(c.tag == SVG_NS + 'use' for c in el)
        if text_key is None and (self.TEXT_ID.match(gid) or tag == 'text' or typst_run):
            text_key = gid or f'text@{self.order}'
            self.order += 1
            self.texts[text_key] = {'label': None, 'glyphs': [], 'order': self.order, 'halo': False}
            if 'stroke' in style.get('paint-order', '') and _stroked(style):
                self.texts[text_key]['halo'] = True
            if tag == 'text':
                self._text_element(el, m, text_key)
                return
        elif text_key is None and gid:
            if self.NOT_CURVE.match(gid):
                excluded = True
            elif re.match(r'^(line2d|LineCollection|PathCollection|PolyCollection|QuadMesh)', gid) \
                    or curve_key is None:
                curve_key = gid
        if tag == 'use':
            ref = self.ids.get((el.get(XLINK) or el.get('href') or '').lstrip('#'))
            if ref is None:
                return
            um = _mul(m, (1, 0, 0, 1, float(el.get('x', 0)), float(el.get('y', 0))))
            if ref.tag.replace(SVG_NS, '') in SHAPES:
                self._shape(ref, _mul(um, _transform(ref.get('transform'))), _style(ref, style),
                            text_key, curve_key, clip, excluded)
            else:
                for child in ref:
                    self._walk(child, um, style, text_key, curve_key, clip, excluded)
            return
        if tag in SHAPES:
            self._shape(el, m, style, text_key, curve_key, clip, excluded)
            return
        for child in el:
            self._walk(child, m, style, text_key, curve_key, clip, excluded)

    def _polys(self, el):
        tag = el.tag.replace(SVG_NS, '')
        if tag == 'path':
            return _path_polys(el.get('d'))
        if tag in ('polyline', 'polygon'):
            v = [float(t) for t in re.findall(NUM, el.get('points', ''))]
            pts = list(zip(v[0::2], v[1::2]))
            return [pts + pts[:1]] if tag == 'polygon' else [pts]
        if tag == 'line':
            return [[(float(el.get('x1', 0)), float(el.get('y1', 0))),
                     (float(el.get('x2', 0)), float(el.get('y2', 0)))]]
        if tag == 'rect':
            x, y = float(el.get('x', 0)), float(el.get('y', 0))
            w, h = float(el.get('width', 0)), float(el.get('height', 0))
            return [[(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]]
        cx, cy = float(el.get('cx', 0)), float(el.get('cy', 0))
        rx = float(el.get('r', el.get('rx', 0)))
        ry = float(el.get('r', el.get('ry', 0)))
        return [[(cx + rx * math.cos(k * math.pi / 8), cy + ry * math.sin(k * math.pi / 8))
                 for k in range(17)]]

    def _shape(self, el, m, style, text_key, curve_key, clip, excluded):
        polys = [[_apply(m, *p) for p in poly] for poly in self._polys(el)]
        if text_key is not None:
            entry = self.texts[text_key]
            if el.tag.replace(SVG_NS, '') == 'rect' and style.get('fill', 'black') != 'none':
                entry['halo'] = True           # text drawn on a box
            if _stroked(style):
                entry['halo'] = True           # stroked copy of the glyphs (path effect)
            pts = [p for poly in polys for p in poly]
            if pts:
                xs, ys = zip(*pts)
                entry['glyphs'].append((min(xs), min(ys), max(xs), max(ys)))
            return
        if excluded or not _stroked(style) or curve_key is None:
            return
        self.order += 1
        segs = []
        for poly in polys:
            for (x0, y0), (x1, y1) in zip(poly, poly[1:]):
                if clip is not None:
                    t = _clip_segment(x0, y0, x1, y1, clip)
                    if t is None:
                        continue
                    dx, dy = x1 - x0, y1 - y0
                    x0, y0, x1, y1 = x0 + t[0] * dx, y0 + t[0] * dy, x0 + t[1] * dx, y0 + t[1] * dy
                segs.append((x0, y0, x1, y1))
        if segs:
            entry = self.curves.setdefault(f'{curve_key}#{self.order}', {'segments': [], 'order': self.order,
                                                                         'stroke': style.get('stroke')})
            entry['segments'] += segs

    def _text_element(self, el, m, key):
        size = float(re.findall(NUM, _style(el, {}).get('font-size', el.get('font-size', '10')) or '10')[0])
        x, y = float(el.get('x', 0)), float(el.get('y', 0))
        content = ''.join(el.itertext()).strip()
        w = 0.55 * size * max(len(content), 1)
        anchor = el.get('text-anchor', '')
        x0 = x - w / 2 if anchor == 'middle' else x - w if anchor == 'end' else x
        pts = [_apply(m, px, py) for px, py in ((x0, y - 0.75 * size), (x0 + w, y - 0.75 * size),
                                                (x0, y + 0.25 * size), (x0 + w, y + 0.25 * size))]
        xs, ys = zip(*pts)
        self.texts[key]['label'] = content
        self.texts[key]['glyphs'].append((min(xs), min(ys), max(xs), max(ys)))


def _shrink(box, d):
    return (box[0] + d, box[1] + d, box[2] - d, box[3] - d)


def _union(boxes):
    return (min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes))


def _overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def collisions(svg_path, inset=0.3):
    """Curve segments crossing a glyph and glyphs of two texts overlapping.

    A curve painted after a text covers it; one painted before it lies under it
    and counts only when the text has no halo (stroked glyph copy, paint-order
    stroke, or a box behind it)."""
    geo = SvgGeometry(svg_path)
    texts = {k: t for k, t in geo.texts.items() if t['glyphs']}
    found = []
    for tk, t in texts.items():
        glyphs = [_shrink(g, inset) for g in t['glyphs'] if g[2] - g[0] > 2 * inset and g[3] - g[1] > 2 * inset]
        if not glyphs:
            continue
        tbox = _union(glyphs)
        for ck, c in geo.curves.items():
            over = c['order'] > t['order']
            if not over and t['halo']:
                continue
            hit = None
            for x0, y0, x1, y1 in c['segments']:
                if not _overlap((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), tbox) \
                        and not (x0 == x1 or y0 == y1):
                    continue
                if _clip_segment(x0, y0, x1, y1, tbox) is None:
                    continue
                for g in glyphs:
                    r = _clip_segment(x0, y0, x1, y1, g)
                    if r is not None:
                        hit = (x0 + r[0] * (x1 - x0), y0 + r[0] * (y1 - y0))
                        break
                if hit:
                    break
            if hit:
                stroke = c.get('stroke') or ''
                found.append(('over' if over else 'under', tk, t['label'],
                              f'{COLOUR_NAMES.get(stroke.lower(), "")} {stroke} curve {ck.split("#")[0]}'.strip(), hit))
    keys = sorted(texts)
    for i, a in enumerate(keys):
        ga = [_shrink(g, inset) for g in texts[a]['glyphs']]
        ba = _union(ga)
        for b in keys[i + 1:]:
            gb = [_shrink(g, inset) for g in texts[b]['glyphs']]
            if not _overlap(ba, _union(gb)):
                continue
            hit = next(((max(p[0], q[0]), max(p[1], q[1])) for p in ga for q in gb if _overlap(p, q)), None)
            if hit:
                found.append(('text', a, texts[a]['label'], f'{b} "{(texts[b]["label"] or "")[:20]}"', hit))
    n_glyphs = sum(len(t['glyphs']) for t in texts.values())
    return found, n_glyphs, len(geo.curves)


def missing_slide_images():
    """assets/diagrams/*.svg files that index.html references but that do not exist."""
    if not os.path.exists(INDEX):
        return []
    with open(INDEX) as f:
        refs = set(re.findall(r'assets/diagrams/[\w.-]+\.svg', f.read()))
    return sorted(r for r in refs if not os.path.exists(os.path.join(ROOT, r)))


def _svg_for(fig_id):
    _, entries = resolve(fig_id)
    if entries:
        return [os.path.join(ROOT, e['svg_path']) for e in entries], entries
    path = os.path.join(FIGS, f'{fig_id}.svg')
    return ([path] if os.path.exists(path) else []), []


KIND = {'over': 'line drawn over the text', 'under': 'line under the text (no halo)',
        'text': 'labels overlap'}


def _svg_size(path):
    with open(path) as f:
        head = f.read(2000)
    m = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"', head)
    return (float(m.group(1)), float(m.group(2))) if m else (1.0, 1.0)


def check(fig_id, limit=8):
    """Collisions, and slide references to missing SVGs. Each collision names
    the SVG, the label (matplotlib) or text run (Typst), what it hits, and the
    point in SVG pt (origin top-left) and in figure fractions (origin
    bottom-left), so a fix can be placed without opening the SVG."""
    paths, entries = _svg_for(fig_id)
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return f'[FAIL] check {fig_id}\nno SVG at assets/diagrams/{fig_id}.svg and no manifest entry; run it first'
    found, glyphs, curves = [], 0, 0
    for p in paths:
        f, g, c = collisions(p)
        w, h = _svg_size(p)
        stem = os.path.splitext(os.path.basename(p))[0]
        found += [(stem, w, h) + x for x in f]
        glyphs, curves = glyphs + g, curves + c
    missing = missing_slide_images()
    slides = sorted({e['slide'] for e in entries if e.get('slide')})
    sources = sorted({e['source'] for e in entries if e.get('source')})
    status = '[OK]' if not found and not missing else '[FAIL]'
    head = (f'{status} check {fig_id}: {len(found)} collisions in {len(paths)} SVG '
            f'({glyphs} glyphs, {curves} lines)')
    where = (f'source {", ".join(sources) or "unknown"}; '
             f'slide {", ".join(slides) or "none (not placed in index.html yet)"}')
    lines = [head, where]
    if missing:
        lines.append(f'index.html references missing SVG: {", ".join(missing[:5])}')
    for stem, w, h, kind, tk, label, other, (x, y) in found[:limit]:
        prefix = f'{stem}: ' if len(paths) > 1 else ''
        lines.append(f'- {prefix}"{(label or tk)[:60]}" x {other}: {KIND[kind]} '
                     f'at ({x:.1f}, {y:.1f}) pt = figure ({x / w:.2f}, {1 - y / h:.2f})')
    if len(found) > limit:
        lines.append(f'- +{len(found) - limit} more')
    if found:
        lines.append('Fix: move the label into free space (label-side/offset/anchor, or the legend outside the axes); no halos.')
    return '\n'.join(lines)


# ------------------------------------------------------------------ review

REVIEW_SYSTEM = """You inspect one figure for a projected 16:9 presentation slide on a near-black background (#0B0F19), shown to students at a recruiting talk. Report only definite defects a viewer in the room would notice. Ignore matters of taste.
Rules:
- Chart series use the fixed categorical order indigo #6366F1, pink #EC4899, sky #0C9EE2, orange #EA580C, emerald #059669, red #EF4444, teal #0D9488, amber #D97706; indigo is the rendering-engines line, pink Neural Rendering, sky light. Diagrams draw light and rays in cyan #38BDF8 and use light indigo #818CF8 for other quantities. Text is #F8FAFC, secondary text and reference lines #94A3B8, surfaces #151E2E. Colours keep their meaning across slides: never ask to reorder or swap them. Every pair of series must stay distinguishable under deuteranopia and protanopia; a pair whose measured CVD distance is below 8 needs a second cue (dash, marker or direct label). A chart with more than 4 coloured series needs that second cue on every series.
- Every text and line must stand out from the dark background; nothing dark-on-dark, no leftover white background or black text.
- Text is legible from the back of a room: no label smaller than the rest of the figure's text, no clipped or cut text. No label is occluded by a line, arrow, marker or another label.
- Legends sit outside the plotted data, or series carry direct labels. No title inside the figure; the slide heading names it.
- Diagrams: arrows start and end on the element they connect; nothing floats detached or overlaps by accident.
Answer in the given JSON schema: status OK with no fixes, or FAIL with at most 3 fixes. In each fix, name the element by its colour, label text or position; keep each field under 25 words."""

# Machado et al. 2009, severity 1.
CVD = {
    'deutan': ((0.367322, 0.860646, -0.227968), (0.280085, 0.672501, 0.047413), (-0.011820, 0.042940, 0.968881)),
    'protan': ((0.152286, 1.052583, -0.204868), (0.114503, 0.786281, 0.099216), (-0.003882, -0.048116, 1.051998)),
    'tritan': ((1.255528, -0.076749, -0.178779), (-0.078411, 0.930809, 0.147602), (0.004733, 0.691367, 0.303900)),
}


def _lin(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _oklab(rgb):
    r, g, b = rgb
    l = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b) ** (1 / 3)
    m = (0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b) ** (1 / 3)
    s = (0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b) ** (1 / 3)
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def _series_colours(chunk):
    """Distinct chromatic stroke colours of the plotted curves in an SVG fragment
    (for a Typst diagram, which has no curve ids, of every stroked shape)."""
    colours = []
    blocks = re.findall(r'<g id="(?:line2d|PathCollection|LineCollection)_\d+">(.*?)</g>', chunk, re.S)
    if not blocks and 'id="figure_' not in chunk:
        blocks = [' '.join(f'stroke: {c}' for c in re.findall(r'stroke="(#[0-9a-fA-F]{6})"', chunk))]
    for block in blocks:
        for hexc in re.findall(r'stroke:\s*(#[0-9a-fA-F]{6})', block):
            rgb = tuple(int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5))
            if max(rgb) - min(rgb) > 0.2 and hexc.lower() not in colours:   # the deck's slate greys reach 0.14
                colours.append(hexc.lower())
    return colours


def _closest_pair(colours):
    """The worst-separated pair of colours over normal vision and the protan
    and deutan simulations, as (distance x100 in OKLab, vision, colour, colour)."""
    lin = {c: tuple(_lin(int(c[i:i + 2], 16) / 255) for i in (1, 3, 5)) for c in colours}
    worst = (1e9, '', '', '')
    # Gated like the dataviz validator: protan and deutan; tritan is too rare to constrain a qualitative palette.
    for name, mat in [('normal', None), ('deutan', CVD['deutan']), ('protan', CVD['protan'])]:
        for i, a in enumerate(colours):
            for b in colours[i + 1:]:
                pa, pb = lin[a], lin[b]
                if mat:
                    pa = tuple(max(0.0, min(1.0, sum(r[k] * pa[k] for k in range(3)))) for r in mat)
                    pb = tuple(max(0.0, min(1.0, sum(r[k] * pb[k] for k in range(3)))) for r in mat)
                worst = min(worst, (100 * math.dist(_oklab(pa), _oklab(pb)), name, a, b))
    return worst


def palette_report(svg_path):
    """Per panel (matplotlib axes, in drawing order), the series colours and
    the worst-separated pair among them over normal vision and each CVD. Only
    series within one panel are compared."""
    with open(svg_path) as f:
        text = f.read()
    starts = [m.start() for m in re.finditer(r'<g id="axes_\d+">', text)] or [0]
    parts = []
    for k, start in enumerate(starts):
        end = starts[k + 1] if k + 1 < len(starts) else len(text)
        colours = _series_colours(text[start:end])
        if len(colours) < 2:
            continue
        d, vision, a, b = _closest_pair(colours)
        parts.append(f'panel {k + 1}: {", ".join(colours[:6])}; closest pair {a}/{b} at {d:.0f} ({vision})')
    return '; '.join(parts) if parts else 'no panel with two chromatic series'


# Gemini vision model of the review; any current flash model with structured
# output works. Authentication: GEMINI_API_KEY (or GOOGLE_API_KEY), else the key
# in REVIEW_KEY_FILE (outside the repository), else Vertex AI with application
# default credentials when GOOGLE_CLOUD_PROJECT is set.
REVIEW_KEY_FILE = os.path.expanduser(os.environ.get('FIGURE_PIPELINE_KEY_FILE',
                                                    '~/.config/figure_pipeline/gemini_key'))
REVIEW_MODEL = os.environ.get('FIGURE_PIPELINE_REVIEW_MODEL', 'gemini-3.8-flash')
REVIEW_MAX_SIDE = 1000          # px, longest side of the preview: one or two vision tiles


_CLIENT = []


def _gemini():
    """The Gemini client, created once per process: a client that goes out of
    scope closes its HTTP connection."""
    if _CLIENT:
        return _CLIENT[0]
    from google import genai
    key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not key and os.path.exists(REVIEW_KEY_FILE):
        with open(REVIEW_KEY_FILE) as f:
            key = f.read().strip()
    if key:
        _CLIENT.append(genai.Client(api_key=key))
    elif os.environ.get('GOOGLE_CLOUD_PROJECT'):
        _CLIENT.append(genai.Client(vertexai=True, project=os.environ['GOOGLE_CLOUD_PROJECT'],
                                    location=os.environ.get('GOOGLE_CLOUD_LOCATION', 'us-central1')))
    if _CLIENT:
        return _CLIENT[0]
    raise RuntimeError(f'no Gemini credentials: set GEMINI_API_KEY, write the key to {REVIEW_KEY_FILE}, '
                       'or set GOOGLE_CLOUD_PROJECT with application default credentials')


def _audit_schema():
    from typing import Literal
    from pydantic import BaseModel, Field

    class FigureFix(BaseModel):
        defect: str = Field(description='what is wrong and where (panel letter, series colour or legend text)')
        fix: str = Field(description='imperative fix')

    class FigureAudit(BaseModel):
        status: Literal['OK', 'FAIL']
        fixes: list[FigureFix] = Field(max_length=3)

    return FigureAudit


def _preview(svg, png):
    """PNG of the SVG on the slide background whose longest side is REVIEW_MAX_SIDE px."""
    from PIL import Image
    w, h = _svg_size(svg)
    side = ['-w', str(REVIEW_MAX_SIDE)] if w >= h else ['-h', str(REVIEW_MAX_SIDE)]
    subprocess.run(['rsvg-convert', *side, '-b', SLIDE_BG, svg, '-o', png], check=True, capture_output=True)
    with Image.open(png) as im:
        if max(im.size) > REVIEW_MAX_SIDE:
            im.thumbnail((REVIEW_MAX_SIDE, REVIEW_MAX_SIDE))
            im.save(png)
    return png


def _words(text, n=25):
    return ' '.join(str(text).split()[:n])


def _no_thinking(types):
    """The least thinking the model accepts: Gemini 2.x takes a token budget of
    0; later lite models take the level MINIMAL, the other later models LOW."""
    if REVIEW_MODEL.startswith('gemini-2'):
        return types.ThinkingConfig(thinking_budget=0)
    return types.ThinkingConfig(thinking_level='MINIMAL' if 'lite' in REVIEW_MODEL else 'LOW')


def review_one(svg, timeout=120):
    """Gemini's audit of the PNG preview of one SVG, as {'status', 'fixes'},
    or None, and the path of the log that keeps the raw reply and its token
    usage."""
    stem = os.path.splitext(os.path.basename(svg))[0]
    os.makedirs(WORK, exist_ok=True)
    png = _preview(svg, os.path.join(WORK, f'{stem}.png'))
    log = os.path.join(WORK, f'{stem}.review.log')
    record = {'model': REVIEW_MODEL, 'png': png}
    t0 = time.time()
    try:
        from google.genai import types
        with open(png, 'rb') as f:
            image = types.Part.from_bytes(data=f.read(), mime_type='image/png')
        reply = _gemini().models.generate_content(
            model=REVIEW_MODEL,
            contents=[image, f'Measured series colours per panel (panels numbered in drawing order) and the '
                             f'closest pair within each panel, as OKLab distance x100 under normal vision or '
                             f'the worst CVD: {palette_report(svg)}.'],
            config=types.GenerateContentConfig(
                system_instruction=REVIEW_SYSTEM,
                response_mime_type='application/json',
                response_schema=_audit_schema(),
                temperature=0.0,
                thinking_config=_no_thinking(types),
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                http_options=types.HttpOptions(timeout=timeout * 1000)))
        u = reply.usage_metadata
        record.update(seconds=round(time.time() - t0, 2), text=reply.text,
                      usage={'input': u.prompt_token_count, 'output': u.candidates_token_count,
                             'thinking': u.thoughts_token_count, 'total': u.total_token_count})
        parsed = reply.parsed
        verdict = parsed.model_dump() if parsed is not None else None
    except Exception as e:                       # the report names the log; the error stays in it
        record.update(seconds=round(time.time() - t0, 2), error=f'{type(e).__name__}: {e}')
        verdict = None
    with open(log, 'w') as f:
        json.dump(record, f, indent=1)
    return verdict, log

def review(fig_id, timeout=120):
    paths, entries = _svg_for(fig_id)
    paths = [p for p in paths if os.path.exists(p)]
    if not paths:
        return f'[FAIL] review {fig_id}\nno SVG at assets/diagrams/{fig_id}.svg and no manifest entry; run it first'
    sources = sorted({e['source'] for e in entries if e.get('source')})
    blocks, failed = [], False
    for svg in paths:
        stem = os.path.splitext(os.path.basename(svg))[0]
        verdict, log = review_one(svg, timeout)
        if verdict is None:
            failed = True
            blocks.append(f'[FAIL] {stem}: reviewer gave no verdict (log {log})')
            continue
        fixes = verdict.get('fixes') or []
        if verdict.get('status') == 'OK' and not fixes:
            blocks.append(f'[OK] {stem}: Visual audit passed.')
            continue
        failed = True
        lines = [f'[FAIL] {stem}:']
        for x in fixes[:3]:
            lines.append(f'- {_words(x.get("defect", ""))}')
            lines.append(f'- Fix: {_words(x.get("fix", ""))}')
        blocks.append('\n'.join(lines))
    status = '[FAIL]' if failed else '[OK]'
    return (f'{status} review {fig_id} ({len(paths)} SVG); source {", ".join(sources) or "unknown"}\n'
            + '\n'.join(blocks))


# --------------------------------------------------------------------- CLI

def main(argv=None):
    p = argparse.ArgumentParser(description=(__doc__ or '').split('\n\n')[0])
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('run', 'check', 'review'):
        s = sub.add_parser(name)
        s.add_argument('--id', required=True)
        if name == 'run':
            s.add_argument('--timeout', type=int, default=3600)
    a = p.parse_args(argv)
    if a.cmd == 'run':
        report = run(a.id, a.timeout)
    elif a.cmd == 'check':
        report = check(a.id)
    else:
        report = review(a.id)
    print(report)
    return 0 if report.startswith('[OK]') else 1


if __name__ == '__main__':
    sys.exit(main())
