from __future__ import annotations
import csv, json, hashlib
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[3]
PUB = ROOT / 'publication' / 'v0.1'
OUT = PUB / 'rendered'
TABLES = OUT / 'tables'
FIGURES = OUT / 'figures'

def read_json(rel):
    return json.loads((ROOT / rel).read_text(encoding='utf-8'))

def read_csv(rel):
    with (ROOT / rel).open('r', encoding='utf-8', newline='') as h:
        return list(csv.DictReader(h))

def write_csv(path, fields, rows):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', encoding='utf-8', newline='') as h:
        w = csv.DictWriter(h, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, '') for k in fields})

def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):
            h.update(chunk)
    return h.hexdigest()

def fmt(v, digits=4):
    try: f=float(v)
    except (TypeError, ValueError): return str(v)
    return f'{f:.{digits}f}'.rstrip('0').rstrip('.')

def svg_open(w,h,title):
    return [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">', f'<title>{escape(title)}</title>', '<rect width="100%" height="100%" fill="white"/>', '<g font-family="Arial, Helvetica, sans-serif" fill="#111">']

def svg_close(lines,path):
    lines += ['</g>','</svg>']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(lines)+'\n', encoding='utf-8')

def text(lines,x,y,s,size=13,weight='normal',anchor='start',rotate=None):
    tr=f' transform="rotate({rotate} {x} {y})"' if rotate is not None else ''
    lines.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}"{tr}>{escape(str(s))}</text>')

def rect(lines,x,y,w,h,fill='white',stroke='#111',sw=1,rx=0):
    lines.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" rx="{rx}"/>')

def line(lines,x1,y1,x2,y2,stroke='#111',sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    lines.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>')

def polyline(lines,pts,stroke='#111',sw=1.5):
    p=' '.join(f'{x:.1f},{y:.1f}' for x,y in pts)
    lines.append(f'<polyline points="{p}" fill="none" stroke="{stroke}" stroke-width="{sw}"/>')
