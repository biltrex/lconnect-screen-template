"""Describe the layers of .template files.  summary.py [--compact] file...  (--compact = one line per layer)"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
import nrbf

def scal(o, skip=()):
    out = {}
    for n, x in o.members:
        k = n.replace('k__BackingField', '').replace('GraphItem+', '').strip('<>')
        if k in skip: continue
        if isinstance(x, nrbf.Prim): out[k] = x.value
        elif isinstance(x, str): out[k] = x if len(x) < 60 else x[:60] + '…'
        elif x is None: out[k] = None
        elif isinstance(x, nrbf.Obj):
            if x.cls[1] == 'System.Drawing.Color':
                v = x.get('value').value; kc = x.get('knownColor').value; st = x.get('state').value
                out[k] = f'#{v & 0xffffffff:08X}' if st == 2 else f'known{kc}' if kc else 'empty'
            elif x.cls[1] == 'System.Drawing.Bitmap':
                out[k] = f'bmp{len(x.get("Data").items)}'
            elif x.has('value__'):
                out[k] = f'enum{x.get("value__").value}'
            else:
                out[k] = f'<{x.cls[1].split(".")[-1]}>'
        elif isinstance(x, nrbf.Arr): out[k] = f'<arr{len(x.items)}>'
    return out

sys.stdout.reconfigure(encoding='utf-8')
compact = '--compact' in sys.argv
if compact:   # one line per layer: class, sensor/format, position
    for path in [x for x in sys.argv[1:] if x != '--compact']:
        root = nrbf.load(path)
        items = root.get('<GraphList>k__BackingField').get('Collection`1+items')
        print('==', os.path.basename(path))
        for i, it in enumerate(items.get('_items').items[:items.get('_size').value]):
            sc = scal(it, skip=('AcceptDataList',))
            md = next((x for n, x in it.members if 'm_data' in n and isinstance(x, nrbf.Obj)), None)
            dn = scal(md).get('DataName') if md else None; sb = scal(md).get('SubName') if md else None
            print(f"{i:3d} {it.cls[1].split('.')[-1]:16s} {str(dn or ''):12s} {str(sb or ''):7s} pos=({sc.get('posX')},{sc.get('posY')}) {sc.get('DisplayName') or ''}")
    sys.exit(0)
for path in sys.argv[1:]:
    root = nrbf.load(path)
    print('=' * 10, os.path.basename(path))
    print('THEME', {k: v for k, v in scal(root).items() if k not in ('themePath',)})
    items = root.get('<GraphList>k__BackingField').get('Collection`1+items')
    lst = items.get('_items').items[:items.get('_size').value]
    for it in lst:
        print('--', it.cls[1].split('.')[-1])
        print('  ', scal(it, skip=('AcceptDataList',)))
        for sub in ('m_data', 'fontConfig', 'GraphItem+<m_data>k__BackingField'):
            pass
        for n, x in it.members:
            if isinstance(x, nrbf.Obj) and x.cls[1].split('.')[-1] in ('M_Data', 'FontConfig', 'AnimationSettings', 'TransFormInfo', 'SensorInfo', 'StyleInfo', 'ShapeInfo'):
                print('    ', x.cls[1].split('.')[-1], scal(x))
                for n2, y in x.members:
                    if isinstance(y, nrbf.Obj) and not y.cls[1].startswith('System.Drawing.Color') and not y.has('value__'):
                        print('       ', n2, y.cls[1].split('.')[-1], scal(y))
