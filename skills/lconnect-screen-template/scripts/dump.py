"""Dump an L-Connect .template as an indented tree. Usage: python dump.py file.template [maxdepth]"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import nrbf

seen = {}

def show(v, ind, depth, maxd, out):
    pad = '  ' * ind
    if isinstance(v, nrbf.Obj):
        if id(v) in seen:
            out.append(f'{pad}-> {v.cls[1]} #{seen[id(v)]}'); return
        seen[id(v)] = len(seen)
        out.append(f'{pad}{v.cls[1]} #{seen[id(v)]}  [{v.cls[0] or "sys"}]')
        if depth >= maxd: return
        for (n, x), (bt, ex) in zip(v.members, v.mtypes):
            n = n.replace('k__BackingField', '').strip('<>')
            if isinstance(x, (nrbf.Obj, nrbf.Arr)):
                out.append(f'{pad}  .{n}:'); show(x, ind + 2, depth + 1, maxd, out)
            else:
                val = x.value if isinstance(x, nrbf.Prim) else x
                if isinstance(val, str) and len(val) > 120: val = val[:120] + '...'
                out.append(f'{pad}  .{n} = {val!r}')
    elif isinstance(v, nrbf.Arr):
        if v.kind == 'prim' and v.ptype == 2:
            data = bytes(v.items)
            sig = 'PNG' if data[:4] == b'\x89PNG' else 'JPG' if data[:2] == b'\xff\xd8' else data[:8].hex()
            out.append(f'{pad}byte[{len(data)}] {sig}'); return
        out.append(f'{pad}{v.kind}[{len(v.items)}] {v.binfo[4:] if v.binfo else ""}')
        if depth >= maxd: return
        for i, x in enumerate(v.items[:400]):
            if isinstance(x, (nrbf.Obj, nrbf.Arr)): show(x, ind + 1, depth + 1, maxd, out)
            else: out.append(f'{pad}  [{i}] {x.value if isinstance(x, nrbf.Prim) else x!r}')
    else:
        out.append(f'{pad}{v!r}')

if __name__ == '__main__':
    root = nrbf.load(sys.argv[1])
    out = []
    show(root, 0, 0, int(sys.argv[2]) if len(sys.argv) > 2 else 99, out)
    sys.stdout.reconfigure(encoding='utf-8')
    print('\n'.join(out))
