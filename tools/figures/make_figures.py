"""
Matplotlib figures of the presentation. Each figure is one function registered
in FIGURES (here or in a figs_<group>.py module); it writes
assets/diagrams/<name>.svg through save(fig, name) and records every number a
slide quotes through record(key, value) into data/results/<function>.json.

    python3 tools/figures/make_figures.py <function> [<function> ...]
    python3 tools/figures/make_figures.py --list

Build and validate through the pipeline instead of calling this directly:
    python3 tools/figures/pipeline.py run --id <function>
"""
import glob
import importlib
import json
import os
import sys

import matplotlib

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from cycler import cycler  # noqa: E402
from matplotlib import font_manager  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
FIGS = os.path.join(ROOT, 'assets', 'diagrams')
RESULTS = os.path.join(ROOT, 'data', 'results')

# Categorical slots, validated on #0B0F19 with the dataviz validator. The first
# ALL_PAIRS_MAX are safe by colour alone; past that every series also needs a
# direct label or a dash (orange/amber and emerald/teal meet under deutan). All 8
# pass as adjacent pairs, for stacked bars. Slots 1-3 keep their DESIGN.md
# meaning: indigo engines, pink Neural Rendering, sky light.
ENGINES, NEURAL, SKY = '#6366F1', '#EC4899', '#0C9EE2'
ORANGE, EMERALD, RED, TEAL, AMBER = '#EA580C', '#059669', '#EF4444', '#0D9488', '#D97706'
CAT = [ENGINES, NEURAL, SKY, ORANGE, EMERALD, RED, TEAL, AMBER]
ALL_PAIRS_MAX = 4
INK, INK2 = '#F8FAFC', '#94A3B8'
NEUTRAL = '#94A3B8'          # reference lines only: too close to the accents under CVD to carry a series
BORDER, SURFACE, BG = '#334155', '#151E2E', '#0B0F19'
DASHES = ['-', '--', ':', '-.']   # second cue from the 5th series on

for path in glob.glob(os.path.join(ROOT, 'assets', 'fonts', '*.ttf')):
    font_manager.fontManager.addfont(path)

plt.rcParams.update({
    'font.family': 'sans-serif',
    'font.sans-serif': ['Inter', 'DejaVu Sans'],
    'font.monospace': ['Fira Code', 'DejaVu Sans Mono'],
    'mathtext.fontset': 'cm',              # matches the math of the Typst diagrams
    'font.size': 14,                       # read from the back of the room at 1280x720
    'axes.titlesize': 14,
    'axes.labelsize': 14,
    'xtick.labelsize': 12,
    'ytick.labelsize': 12,
    'legend.fontsize': 12,
    'text.color': INK,
    'axes.labelcolor': INK,
    'axes.edgecolor': BORDER,
    'axes.facecolor': 'none',
    'figure.facecolor': 'none',
    'savefig.facecolor': 'none',
    'savefig.transparent': True,
    'xtick.color': INK2,
    'ytick.color': INK2,
    'grid.color': BORDER,
    'grid.linewidth': 0.6,
    'axes.grid': False,
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.prop_cycle': cycler(color=CAT),
    'lines.linewidth': 2.0,
    'legend.frameon': False,
    'svg.fonttype': 'path',                # glyphs as paths: the slide needs no fonts, the checker reads the labels
    'figure.dpi': 100,
})

_RUN = {'outputs': [], 'values': {}}


def save(fig, name):
    """Write assets/diagrams/<name>.svg and list it in the current run's results."""
    os.makedirs(FIGS, exist_ok=True)
    path = os.path.join(FIGS, f'{name}.svg')
    fig.savefig(path, bbox_inches='tight', pad_inches=0.05, metadata={'Date': None})
    plt.close(fig)
    _RUN['outputs'].append(os.path.relpath(path, ROOT))
    return path


def record(key, value):
    """A number a slide quotes, so the slide never carries a hand-typed value."""
    _RUN['values'][key] = value


def legend_above(ax, ncol=3):
    return ax.legend(loc='lower left', bbox_to_anchor=(0, 1.02, 1, 0.2), mode='expand',
                     ncol=ncol, borderaxespad=0, handlelength=1.6)


FIGURES = {}
# figs_*.py modules import save/record from here; run as a script, they must share this module's _RUN.
sys.modules.setdefault('make_figures', sys.modules[__name__])

for _path in sorted(glob.glob(os.path.join(HERE, 'figs_*.py'))):
    FIGURES.update(importlib.import_module(os.path.splitext(os.path.basename(_path))[0]).FIGURES)


def main(argv):
    if not argv or argv == ['--list']:
        print('\n'.join(sorted(FIGURES)) or 'no figures registered yet')
        return 0
    for name in argv:
        if name not in FIGURES:
            print(f'unknown figure {name}; known: {", ".join(sorted(FIGURES)) or "none"}', file=sys.stderr)
            return 2
        _RUN['outputs'], _RUN['values'] = [], {}
        FIGURES[name]()
        os.makedirs(RESULTS, exist_ok=True)
        with open(os.path.join(RESULTS, f'{name}.json'), 'w') as f:
            json.dump({'outputs': _RUN['outputs'], 'values': _RUN['values']}, f, indent=2)
            f.write('\n')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
