"""
Show every C++ excerpt on the slides as a diff against an upstream version.

Each <pre><code class="language-cpp"> block of index.html, and each
language-diff block written by this script, is traced to the file it quotes in
the source repository; that file is diffed against its upstream counterpart at
the base commit (the same path, the file it was copied from per `counterpart`,
or nothing for a new file), and the block is rewritten as a language-diff block
with data-source naming the file. A <code> with data-diff-base="<slide id>" is
marked against the first excerpt of that slide instead, to show what a later
slide adds to it: '+' for a line this work adds or changes, '-' for the
upstream line it replaces within the quoted stretch, ' ' for an upstream line.
Comments are left out of the diff blocks.

The repository, base commit, source globs and counterparts come from
tools/code/sources.json; RENDER_SOURCE_REPO and RENDER_SOURCE_BASE override it.

    python3 tools/code/cpp_snippet_diff.py           # print the diffs
    python3 tools/code/cpp_snippet_diff.py --write   # rewrite index.html
"""
import re, difflib, subprocess, sys, glob, os, html, json
HERE=os.path.dirname(os.path.abspath(__file__))
INDEX=os.path.join(os.path.dirname(os.path.dirname(HERE)),'index.html')
CONFIG=json.load(open(os.path.join(HERE,'sources.json')))
REPO=os.path.expanduser(os.environ.get('RENDER_SOURCE_REPO') or CONFIG.get('repo') or '')
BASE=os.environ.get('RENDER_SOURCE_BASE') or CONFIG.get('base') or ''
GLOBS=CONFIG.get('globs') or ['**/*.cpp','**/*.cc','**/*.h','**/*.hpp','**/*.cu']
COUNTERPART=CONFIG.get('counterpart') or {}
norm=lambda l: re.sub(r'\s+',' ',re.sub(r'\s*//.*$','',l).strip()) if not l.strip().startswith('//') else re.sub(r'\s+',' ',l.strip())
indent=lambda l: len(l)-len(l.lstrip(' '))
def upstream(f):
    r=subprocess.run(['git','-C',REPO,'show',f'{BASE}:{f}'],capture_output=True,text=True)
    return r.stdout.split('\n') if r.returncode==0 else None

def blocks(T, U):
    sm=difflib.SequenceMatcher(None,[norm(l) for l in T],[norm(l) for l in U],autojunk=False)
    st=['+']*len(T); blk=[None]*len(T); dels={}
    for op in sm.get_opcodes():
        tag,i1,i2,j1,j2=op
        for i in range(i1,i2):
            st[i]=' ' if tag=='equal' else '+'
            blk[i]=op
        if tag=='delete':
            dels[i1]=[l for l in U[j1:j2] if norm(l)]
    return st, blk, dels

def _defines(line, name_in):
    m=re.match(r'^\s*[\w:<>,\s\*&]+?\s+(\w+)\s*=', line)
    return m and re.search(r'\b'+re.escape(m.group(1))+r'\b', name_in)

def pair_block(T, U, op):
    """Greedy pairing of the changed lines of a replaced block with the upstream
    lines they replace, most similar first."""
    tag,i1,i2,j1,j2=op
    sc=[]
    for a in range(i1,i2):
        for b in range(j1,j2):
            if norm(T[a]) and norm(U[b]):
                r=difflib.SequenceMatcher(None,norm(T[a]),norm(U[b])).ratio()
                if r>=0.55: sc.append((r,a,b))
    pa={}; ub=set()
    for r,a,b in sorted(sc, reverse=True):
        if a not in pa and b not in ub: pa[a]=b; ub.add(b)
    return pa

def code_only(line):
    """A C++ line without its comment: None for a comment line, else the code
    with a trailing // comment removed (outside string literals)."""
    body=line.strip()
    if body.startswith(('//', '/*', '*')):
        return None
    quote=False
    for i,c in enumerate(line):
        if c=='"' and (i==0 or line[i-1]!='\\'):
            quote=not quote
        if not quote and line.startswith('//', i):
            return line[:i].rstrip()
    return line.rstrip()


def drop_comments(out):
    """The diff lines without comments, and without the blank lines that
    removing them leaves in a row."""
    kept=[]
    for l in out:
        if not l.strip():
            if kept and kept[-1]!='':
                kept.append('')
            continue
        code=code_only(l[2:])
        if code is not None:
            kept.append(l[:2]+code)
    while kept and kept[-1]=='':
        kept.pop()
    return kept


def diff_snippet(snip, src, base=None):
    """The excerpt `snip` of the file `src`, marked against upstream, or against
    the lines `base` of an earlier excerpt when one is given."""
    if base is None:
        T=open(os.path.join(REPO,src)).read().split('\n')
        up_file=COUNTERPART.get(src, src)
        U=upstream(up_file)
    else:
        T=snip.split('\n'); up_file='the earlier excerpt'; U=base
    lines=snip.split('\n')
    if lines and lines[-1]=='': lines=lines[:-1]
    idx=[]; t=0; tn=[norm(l) for l in T]
    for l in lines:
        n=norm(l)
        if not n: idx.append(None); continue
        k=next((i for i in range(t,len(T)) if tn[i]==n), None)
        if k is None: k=next((i for i in range(len(T)) if tn[i]==n), None)
        idx.append(k)
        if k is not None: t=k+1
    un=set(norm(l) for l in U) if U is not None else set()
    if U is None:
        st=['+']*len(T); blk=[None]*len(T); dels={}
    else:
        st,blk,dels=blocks(T,U)
    pairs={}
    out=[]; prev=None; unmatched=0; last_j={}
    for l,k in zip(lines,idx):
        if not norm(l):
            out.append(''); continue
        if k is None:
            if U is not None and norm(l) in un:
                out.append('  '+l); continue
            unmatched+=1
            out.append(('  ' if norm(l).startswith('//') else '+ ')+l); continue
        if k in dels and prev==k-1 and len(dels[k])<=3:
            off=indent(T[k])-indent(l)
            out+=['- '+u[min(off,indent(u)):] for u in dels[k]]
        op=blk[k]
        if st[k]=='+' and op is not None and op[0]=='replace':
            if op not in pairs: pairs[op]=pair_block(T,U,op)
            j=pairs[op].get(k)
            if j is not None:
                off=indent(U[j])-indent(l)
                cut=lambda u: u[min(off,indent(u)):]
                show=[]
                lj=last_j.get(op)
                if lj is not None and 0 < j-lj-1 <= 3:
                    show+=[q for q in range(lj+1,j) if norm(U[q]) and q not in pairs[op].values()]
                elif lj is None and j-1>=op[3] and _defines(U[j-1], U[j]):
                    show.append(j-1)
                out+=['- '+cut(U[q]) for q in show+[j]]
                last_j[op]=j
        out.append(st[k]+' '+l)
        prev=k
    return '\n'.join(drop_comments(out)), up_file if U is not None else None, unmatched

def source_of(lines, texts):
    """The source file that contains most of the excerpt's lines."""
    keys=[norm(l) for l in lines if len(norm(l))>12]
    best=None
    for f,tn in texts.items():
        hit=sum(k in tn for k in keys)
        if hit and (best is None or hit>best[1]): best=(f,hit)
    return best[0] if best else None


def excerpt(lang, body):
    """The quoted source lines of a block: a diff block loses its markers and
    the upstream lines it shows as removed."""
    if lang != 'diff':
        return body
    return '\n'.join(l[2:] for l in body.split('\n') if not l.startswith('- '))


# The <code> keeps its other attributes (data-line-numbers, data-trim, ...); class and data-source are rewritten.
BLOCK=re.compile(r'<code\b([^>]*?)\bclass="([^"]*\blanguage-(cpp|c\+\+|diff)\b[^"]*)"([^>]*)>(.*?)</code>', re.S)
BASE_ATTR=re.compile(r'\bdata-diff-base="([^"]+)"')
SECTION=re.compile(r'<section\b[^>]*\bid="([^"]+)"')


def parts(m):
    attrs=' '.join(a for a in re.findall(r'[\w:-]+(?:="[^"]*")?', m.group(1)+' '+m.group(4)) if not a.startswith('data-source='))
    body=html.unescape(m.group(5)).strip('\n')
    return attrs, m.group(2), m.group(3), body


def slide_excerpts(txt):
    """The first excerpt shown on each slide."""
    first={}
    for m in BLOCK.finditer(txt):
        ids=SECTION.findall(txt[:m.start()])
        if ids and ids[-1] not in first:
            _,_,lang,body=parts(m)
            first[ids[-1]]=excerpt(lang, body).split('\n')
    return first


if __name__=='__main__':
    write='--write' in sys.argv
    if not REPO or not os.path.isdir(os.path.join(REPO,'.git')):
        sys.exit(f'no git repository at "{REPO}": set "repo" in tools/code/sources.json or RENDER_SOURCE_REPO')
    if not BASE:
        sys.exit('no base commit: set "base" in tools/code/sources.json or RENDER_SOURCE_BASE')
    srcs=sorted({os.path.relpath(f,REPO) for pat in GLOBS for f in glob.glob(os.path.join(REPO,pat),recursive=True)
                 if not re.search(r'(^|/)(build[^/]*|ext|third_party|\.git)/', os.path.relpath(f,REPO))})
    texts={f:set(norm(l) for l in open(os.path.join(REPO,f),errors='replace').read().split('\n')) for f in srcs}
    txt=open(INDEX).read()
    first=slide_excerpts(txt)
    def sub(m):
        attrs, cls, lang, raw = parts(m)
        body=excerpt(lang, raw)
        src=source_of(body.split('\n'), texts)
        line=txt[:m.start()].count('\n')+1
        if src is None:
            print(f'== index.html:{line}  not traced to any file in {REPO}; left as is\n')
            return m.group(0)
        b=BASE_ATTR.search(attrs)
        if b and b.group(1) not in first:
            print(f'== index.html:{line}  data-diff-base="{b.group(1)}" names no slide with an excerpt; left as is\n')
            return m.group(0)
        d,upf,miss=diff_snippet(body, src, base=first[b.group(1)] if b else None)
        if b: upf='#'+b.group(1)
        elif upf is None: upf='nothing (new file at the base commit)'
        print(f'== index.html:{line}  {src} against {upf}  ({miss} lines not in the source)')
        print(d); print()
        cls=re.sub(r'\blanguage-(cpp|c\+\+|diff)\b','language-diff',cls)
        return f'<code{" "+attrs if attrs else ""} class="{cls}" data-source="{src}">\n{html.escape(d, quote=False)}\n</code>'
    new=BLOCK.sub(sub, txt)
    if write and new != txt: open(INDEX,'w').write(new)
