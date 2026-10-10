"""
MCP server (stdio, JSON-RPC 2.0, no dependencies) for the figure pipeline.

Tools, each returning the short report of the matching pipeline.py command:
    run_figure_pipeline    build the figure (Typst drawing or matplotlib function), record it in assets/diagrams/manifest.json
    check_figure_geometry  text/line collisions in the SVG, slide references to missing SVGs
    review_figure_visuals  PNG preview on the slide background audited by the Gemini vision API

Registered for this project in .mcp.json.
"""
import contextlib
import json
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pipeline  # noqa: E402

PROTOCOL = '2024-11-05'
MAX_CHARS = 2400           # about 600 tokens: enough for every collision or issue of a figure

ID = {'type': 'string', 'description': 'SVG stem in assets/diagrams/ (diagrams_src/<stem>.typ) or matplotlib figure function name'}
TOOLS = [
    {'name': 'run_figure_pipeline',
     'description': 'Build a presentation figure into assets/diagrams/: compile diagrams_src/<id>.typ with Typst '
                    'and the deck fonts, or run the matplotlib function <id> of tools/figures/make_figures.py. '
                    'Records it in assets/diagrams/manifest.json. Returns [OK] with the SVG names, or [FAIL] with '
                    'the Typst error or the exception and failing line of the figure script.',
     'inputSchema': {'type': 'object', 'required': ['id'],
                     'properties': {'id': ID, 'timeout': {'type': 'integer', 'description': 'seconds, default 3600'}}}},
    {'name': 'check_figure_geometry',
     'description': 'Deterministic SVG check: lines crossing glyphs (drawn over, or under text without a halo), '
                    'overlapping labels, and index.html references to missing SVGs. '
                    'Returns [OK]/[FAIL], the source and the slide that shows it, and per collision the label '
                    '(or Typst text run), what it hits (line colour or other label), and the point in SVG pt and '
                    'in figure fractions.',
     'inputSchema': {'type': 'object', 'required': ['id'], 'properties': {'id': ID}}},
    {'name': 'review_figure_visuals',
     'description': 'Render a PNG (longest side 1000 px) of each SVG on the slide background and have Gemini Flash '
                    'audit it against the deck figure rules (DESIGN.md palette, CVD, contrast on dark, label collisions, '
                    'legend placement, legibility at projection size). First line is the '
                    'overall [OK]/[FAIL] with the source function; then per SVG "[OK] <stem>: Visual audit passed." '
                    'or "[FAIL] <stem>:" with '
                    'at most three "- <defect with location>" / "- Fix: <fix>" pairs. A few seconds per SVG.',
     'inputSchema': {'type': 'object', 'required': ['id'], 'properties': {'id': ID}}},
]


def call(name, args):
    fig_id = str(args.get('id', '')).strip()
    if not fig_id:
        return '[FAIL] missing id'
    with contextlib.redirect_stdout(sys.stderr):      # stdout carries only JSON-RPC
        if name == 'run_figure_pipeline':
            return pipeline.run(fig_id, int(args.get('timeout', 3600)))
        if name == 'check_figure_geometry':
            return pipeline.check(fig_id)
        if name == 'review_figure_visuals':
            return pipeline.review(fig_id)
    raise KeyError(name)


def handle(msg):
    method, mid = msg.get('method'), msg.get('id')
    if method == 'initialize':
        result = {'protocolVersion': msg.get('params', {}).get('protocolVersion', PROTOCOL),
                  'capabilities': {'tools': {}},
                  'serverInfo': {'name': 'figure-pipeline', 'version': '1.0'}}
    elif method == 'tools/list':
        result = {'tools': TOOLS}
    elif method == 'tools/call':
        params = msg.get('params', {})
        try:
            text, error = call(params.get('name'), params.get('arguments') or {}), False
        except KeyError:
            return {'jsonrpc': '2.0', 'id': mid,
                    'error': {'code': -32602, 'message': f'unknown tool {params.get("name")}'}}
        except Exception as e:                              # report, keep serving
            traceback.print_exc(file=sys.stderr)
            text, error = f'[FAIL] {type(e).__name__}: {str(e)[:200]}', True
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS - 1] + '…'
        result = {'content': [{'type': 'text', 'text': text}], 'isError': error}
    elif method == 'ping':
        result = {}
    elif mid is None:                                       # notifications
        return None
    else:
        return {'jsonrpc': '2.0', 'id': mid, 'error': {'code': -32601, 'message': f'no method {method}'}}
    return {'jsonrpc': '2.0', 'id': mid, 'result': result}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            reply = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'parse error'}}
        else:
            reply = handle(msg)
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + '\n')
            sys.stdout.flush()


if __name__ == '__main__':
    main()
