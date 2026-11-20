"""Turn a 1920x480 design HTML (with data-lc slots) into a native L-Connect 3 .template.

  python -I make_template.py <design.html> --name My-Screen [--out <dir>] [--build <dir>]

Steps: export (screenshots + slot manifest) -> font resolution -> spec -> render each layer with
L-Connect's own ThemeEngine -> nudge positions / letter-spacing until glyphs match the design ->
write <out>/<name>.template plus preview PNGs. Exit code 0 = template written.
"""
import argparse, json, os, re, subprocess, sys, shutil, glob
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LC_DIR = r'C:\Program Files\Lian-Li\L-Connect 3'
TPL_DIR = r'C:\ProgramData\Lian-Li\L-Connect 3\universal-screen-8.8-inch\template'
W, H = 1920, 480

ap = argparse.ArgumentParser()
ap.add_argument('design', help='the design HTML (1920x480, with data-lc slots)')
ap.add_argument('--name', required=True, help='template name (also the file name)')
ap.add_argument('--out', help='output folder (default: <design dir>/dist)')
ap.add_argument('--build', help='work folder (default: <design dir>/build)')
ap.add_argument('--seed', help='a stock 1920x480 .template to inherit theme settings from (auto-found)')
ap.add_argument('--passes', type=int, default=6, help='max calibration passes (stops early at <=1px)')
ap.add_argument('--skip-export', action='store_true', help='reuse build/ screenshots + manifest from the last run')
a = ap.parse_args()
ddir = os.path.dirname(os.path.abspath(a.design))
OUT = a.out or os.path.join(ddir, 'dist')
BUILD = a.build or os.path.join(ddir, 'build')
os.makedirs(OUT, exist_ok=True); os.makedirs(BUILD, exist_ok=True)
problems = []
notes = []

if not os.path.exists(os.path.join(LC_DIR, 'lianli.ThemeEngine.dll')):
    sys.exit(f'L-Connect 3 not found ({LC_DIR}). It must be installed: its engine builds the template.')

# ---------------------------------------------------------------- 1. export
if not a.skip_export:
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'export_design.py'), a.design, BUILD], check=True)
man = json.load(open(os.path.join(BUILD, 'manifest.json')))
if man['errors']:
    sys.exit('Fix the design markup first:\n  ' + '\n  '.join(man['errors']))
if not man['texts'] and not man['slots']:
    sys.exit('No [data-lc] slots found. See references/design-contract.md.')

# ---------------------------------------------------------------- 2. seed template
def find_seed():
    import nrbf
    cands = []
    if a.seed: return a.seed
    pref = os.path.join(TPL_DIR, '88012.template')
    files = ([pref] if os.path.exists(pref) else []) + sorted(glob.glob(os.path.join(TPL_DIR, '*.template')), key=os.path.getsize)
    for f in files:
        try:
            with open(f, 'rb') as fh:
                if b'lianli.ThemeEngine' not in fh.read(600): continue
            root = nrbf.load(f)
            g = lambda n: root.get(f'<{n}>k__BackingField').value
            if g('width') == W and g('height') == H: return f
        except Exception:
            continue
    return None
SEED = find_seed()
if not SEED:
    sys.exit(f'No 1920x480 L-Connect template found to use as a seed in {TPL_DIR}. Pass --seed <file>.')

# ---------------------------------------------------------------- 3. fonts
fc = json.loads(subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File',
                                os.path.join(HERE, 'fontcheck.ps1')], capture_output=True, text=True).stdout)
machine, useronly = set(fc['machine']), set(fc['user'])
SUFFIX = {100: 'Thin', 200: 'ExtraLight', 300: 'Light', 350: 'SemiLight', 500: 'Medium', 600: 'SemiBold',
          800: 'ExtraBold', 900: 'Black'}

def resolve_font(t):
    """CSS family + weight -> (GDI family name, bold flag). Variable fonts expose each weight as a family."""
    if t['font']:
        fam, bold = t['font'], t['weight'] >= 700 and not any(s in t['font'] for s in SUFFIX.values())
    else:
        w = min(SUFFIX, key=lambda k: abs(k - t['weight'])) if t['weight'] not in (400, 700) else t['weight']
        named = f"{t['family']} {SUFFIX[w]}" if w in SUFFIX else None
        if named and (named in machine or named in useronly):
            fam, bold = named, False
        else:
            fam, bold = t['family'], t['weight'] >= 600
    if fam in useronly:
        problems.append(f"Font '{fam}' is installed for this Windows user only. The L-Connect service runs as "
                        f"LocalSystem and will draw it as Arial. Install the font for ALL users, then restart LConnectService.")
    elif fam not in machine:
        problems.append(f"Font '{fam}' is not installed (slot {t['id']}). L-Connect will fall back to Arial.")
    return fam, bold

# ---------------------------------------------------------------- 4. spec
def css_hex(c):
    if c.startswith('#'):
        h = c.lstrip('#'); h = ''.join(ch * 2 for ch in h) if len(h) in (3, 4) else h
        return '#' + (h[6:8] + h[:6] if len(h) == 8 else h).upper()
    v = [float(x) for x in c[c.index('(') + 1:c.index(')')].replace('/', ',').split(',')]
    al = round(v[3] * 255) if len(v) > 3 else 255
    return '#{:02X}{:02X}{:02X}{:02X}'.format(al, *[int(round(x)) for x in v[:3]])

ALIGN = {'left': 0, 'center': 1, 'centre': 1, 'right': 2}
items = [dict(type='image', path=os.path.join(BUILD, 'background.png').replace('\\', '/'), x=0, y=0, label='Background')]
texts = []
for t in man['texts']:
    fam, bold = resolve_font(t)
    al = ALIGN.get(t['align'], 2)
    ink = t['ink']
    x = {0: ink['x'], 1: ink['x'] + ink['w'] / 2, 2: ink['x'] + ink['w']}[al]
    digits = t['text'].isdigit() and len(t['text']) > 1
    if t['spacing'] > 0 and not digits:
        notes.append(f"{t['id']}: letter-spacing {t['spacing']:g}px dropped (only digit-only values keep it); "
                     f"set letter-spacing:0 on this slot in the design so the preview matches")
    if t['transform'] not in ('none', '') and not t['text'].isdigit():
        problems.append(f"{t['id']}: CSS text-transform '{t['transform']}' can't be reproduced natively; "
                        f"L-Connect shows the sensor's own casing (e.g. DAY -> 'Thu').")
    it = dict(type='text', data=t['sensor'], sub=t['sub'], label=t['label'], font=fam, bold=bold, italic=t.get('italic', False),
              gradient=css_hex(t['gradient']) if t.get('gradient') else None, gradientDir=t.get('gradientDir', 1),
              size=max(1, round(t['size'] * 0.75)),            # CSS px -> GDI pt at 96 dpi
              interval=(-4.0 if t['spacing'] > 0 and digits else 0), color=css_hex(t['color']), align=al,
              x=round(x), y=round(ink['y']), sample=t['text'] or '0',
              _box=[min(t['box']['x'], ink['x']), min(t['box']['y'], ink['y']),
                    max(t['box']['w'], ink['w']), max(t['box']['h'], ink['h'])], _id=t['id'])
    items.append(it); texts.append(it)

# ---------------------------------------------------------------- non-text slots -> engine widgets
from PIL import ImageDraw
from urllib.parse import urlparse, unquote


def num(d, k, default):
    v = d.get(k)
    try:
        return float(v) if v not in (None, '') else default
    except ValueError:
        return default


def flag(d, k):
    return k in d and str(d.get(k, '')).lower() in ('true', '1', 'yes', '')


def col(v, default='#FFFFFF'):
    return css_hex(v) if v else default


def W_(cls, x, y, slot, **k):
    return dict(type='widget', **{'class': cls}, x=int(round(x)), y=int(round(y)), label=slot['label'], **k)


def rgba(hexstr):
    h = css_hex(hexstr)
    a_ = int(h[1:3], 16) if len(h) == 9 else 255
    h6 = h[-6:]
    return (int(h6[0:2], 16), int(h6[2:4], 16), int(h6[4:6], 16), a_)


FILL = {'ltr': 0, 'rtl': 1, 'ttb': 2, 'btt': 3}
RING_TYPE = {'CPULOAD': 'CPULoad', 'CPUTEMP': 'CPUTemperature', 'CPUTEMP_F': 'CPUTemperatureF', 'GPULOAD': 'GPULoad',
             'GPUTEMP': 'GPUTemperature', 'GPUTEMP_F': 'GPUTemperatureF', 'CPUFAN': 'FanRPM'}
rings = []
for sl in man['slots']:
    d, bx, kind = sl['data'], sl['box'], sl['kind']
    sensor, sub, sample = d.get('sensor'), d.get('sub') or None, d.get('sample', '50')

    if kind in ('bar', 'slider'):
        # direction 0 ltr, 1 rtl, 2 ttb, 3 btt; for vertical bars the engine's width is the LENGTH
        fill = d.get('fill') or ('btt' if bx['h'] > bx['w'] else 'ltr')
        if fill not in FILL:
            problems.append(f"{sl['id']}: data-fill must be ltr, rtl, ttb or btt"); fill = 'ltr'
        vertical = fill in ('ttb', 'btt')
        length, thick = (bx['h'], bx['w']) if vertical else (bx['w'], bx['h'])
        n, gap = int(num(d, 'segments', 0)), int(num(d, 'gap', 0))
        if n > 1:
            block = max(1, round((length - (n - 1) * gap) / n)); length2 = n * block + (n - 1) * gap
        else:
            block, length2 = 0, round(length)
        off = (length - length2) / 2
        x, y = (bx['x'], bx['y'] + off) if vertical else (bx['x'] + off, bx['y'])
        track = d.get('track', 'solid')
        f = dict(width=int(length2), height=int(round(thick)), direction=FILL[fill], radius=int(num(d, 'radius', 0)),
                 FrontColor=col(d.get('on')), BackColor=col(d.get('off'), '#00000000'),
                 fillBack=track != 'outline', trBack=track == 'none', lineWidth=int(num(d, 'lineWidth', 2)),
                 useSubsection=n > 1, SplitBlockWidth=block, SplitBlankWidth=gap if n > 1 else 0)
        if d.get('gradient'):
            f.update(useGradient=True, GradientColor=col(d['gradient']))
        if kind == 'slider':
            if vertical:
                problems.append(f"{sl['id']}: sliders are horizontal only (data-fill ltr or rtl)")
            f.update(InnerCircleRadius=int(num(d, 'knob', thick * 2)), radius=int(num(d, 'radius', thick / 2)))
        items.append(W_('GraphDynamicBar' if kind == 'slider' else 'GraphStatuBar', x, y, sl, data=sensor, sub=sub, sample=sample, fields=f))

    elif kind == 'arc':
        # posX/posY = top-left of the ring's CENTRE-LINE circle (measured); outer size = diameter + archWidth
        size = min(bx['w'], bx['h']); t = num(d, 'thickness', size * 0.1)
        start = num(d, 'start', 0) % 360
        f = dict(diameter=int(round(size - t)), archWidth=int(round(t)), startPer=int(round(start / 3.6)) % 100,
                 totalAngel=int(num(d, 'sweep', 360)), round=flag(d, 'round'), revert=flag(d, 'reverse'),
                 FrontColor=col(d.get('on')), BackColor=col(d.get('off'), '#00000000'),
                 trBack=d.get('track') == 'none' or not d.get('off'))
        if num(d, 'block', 0) > 0:
            f.update(useBlock=True, SplitBlockWidth=int(num(d, 'block', 0)), SplitBlankWidth=int(num(d, 'gap', 4)))
        if d.get('gradient'):
            f.update(useGradient=True, GradientColor=col(d['gradient']))
        if num(d, 'border', 0) > 0:
            f.update(HasRingBorder=True, lineWidth=int(num(d, 'border', 2)))
        if abs(start / 3.6 - round(start / 3.6)) > 0.01:
            notes.append(f"{sl['id']}: arc start rounded to {round(start / 3.6) * 3.6:g} deg (L-Connect stores whole percent)")
        items.append(W_('GraphArchBar', bx['x'] + (bx['w'] - size) / 2 + t / 2, bx['y'] + (bx['h'] - size) / 2 + t / 2, sl,
                        data=sensor, sub=sub, sample=sample, fields=f))

    elif kind == 'chart':
        # drawn width = columnWidth x queueLen; coefficient (px per unit) is set by the builder
        step = max(1, int(num(d, 'step', 8)))
        qlen = max(2, int(round(bx['w'] / step)))
        hist = [float(v) for v in d.get('history', '').split(',') if v.strip()] or \
               [45 + 25 * np.sin(i / 3) + 12 * np.sin(i * 1.7) for i in range(qlen)]
        # L-Connect draws chart fills much stronger than their alpha (measured: alpha 0.125 shows as 0.39,
        # 0.5 as 0.74, independent of step). Convert the design's intended opacity into the alpha that shows it.
        fillc = col(d.get('fillColor'), '#00000000')
        if len(fillc) == 9 and fillc[1:3] not in ('00', 'FF'):
            A_ = [0, .031, .063, .094, .125, .188, .251, .376, .502, .627, .753, .878, 1.0]
            E_ = [0, .196, .278, .337, .388, .471, .537, .647, .737, .816, .882, .941, 1.0]
            want = int(fillc[1:3], 16) / 255
            fillc = '#{:02X}'.format(max(1, round(float(np.interp(want, E_, A_)) * 255))) + fillc[3:]
        f = dict(_width=int(round(bx['w'])), _height=int(round(bx['h'])), columnWidth=step, maxValue=num(d, 'max', 100),
                 LineColor=col(d.get('color')), FillColor=fillc, lineWidth=int(num(d, 'lineWidth', 2)),
                 BorderColor=col(d.get('frame') or d.get('color'), '#00000000'), borderWidth=int(num(d, 'frameWidth', 0)),
                 rollDirection=d.get('anchor') == 'right')
        if round(bx['w']) % step:
            notes.append(f"{sl['id']}: chart width {bx['w']:g} isn't a multiple of data-step {step}; drawn width will be {qlen * step}px")
        items.append(W_('GraphLine', bx['x'], bx['y'], sl, data=sensor, sub=sub, history=[round(float(v), 1) for v in hist[-qlen:]],
                        mdata=dict(queueLen=qlen), fields=f))

    elif kind == 'needle':
        # GraphClock: rotates an up-pointing image about the box centre; angle = start + rate x sweep
        size = int(round(min(bx['w'], bx['h'])))
        cx, cy = bx['x'] + bx['w'] / 2, bx['y'] + bx['h'] / 2
        if d.get('image'):
            img = os.path.normpath(os.path.join(ddir, d['image']))
            if not os.path.exists(img):
                problems.append(f"{sl['id']}: needle image not found: {img}"); continue
            iw = Image.open(img).width
        else:
            L = num(d, 'length', size * 0.42); wd = num(d, 'width', max(2, L * 0.06)); tail = num(d, 'tail', L * 0.18)
            im = Image.new('RGBA', (size, size), (0, 0, 0, 0)); g = ImageDraw.Draw(im); c = size / 2
            g.rounded_rectangle([c - wd / 2, c - L, c + wd / 2, c + tail], radius=wd / 2, fill=rgba(d.get('color', '#FF4444')))
            if d.get('cap') != 'none':
                r_ = max(3, wd)
                g.ellipse([c - r_, c - r_, c + r_, c + r_], fill=rgba(d.get('cap', '#FFFFFF')))
            img = os.path.join(BUILD, f"needle-{sl['id']}.png"); im.save(img); iw = size
        is_time = sensor == 'TIME'
        f = dict(angle=int(num(d, 'start', 0 if is_time else -135)), endAngle=int(num(d, 'sweep', 360 if is_time else 270)),
                 revert=flag(d, 'reverse'))
        items.append(W_('GraphClock', cx, cy, sl, data=sensor, sub=sub or ('h_12' if is_time else None),
                        sample=None if is_time else sample, image=img.replace('\\', '/'), imageWidth=iw, fields=f))

    elif kind == 'image':
        u = urlparse(sl.get('src') or '')
        path = unquote(u.path.lstrip('/')) if u.scheme == 'file' else os.path.join(ddir, sl.get('src') or '')
        if not os.path.exists(path):
            problems.append(f"{sl['id']}: image not found ({sl.get('src')})"); continue
        items.append(W_('GraphImage', bx['x'], bx['y'], sl, image=path.replace('\\', '/'), imageWidth=int(round(bx['w']))))

    elif kind == 'ring':
        style = d.get('style', 'Ring1')
        if style not in ('Ring1', 'Ring2', 'Ring3', 'Ring4', 'Ring5'):
            problems.append(f"{sl['id']}: ring style '{style}' isn't usable (SENSOR_6/SENSOR_7/Pic crash the screen); use Ring1..Ring5"); continue
        stype = d.get('type') or RING_TYPE.get((sensor or 'CPULOAD').upper())
        if not stype:
            problems.append(f"{sl['id']}: ring data-sensor must be one of {', '.join(RING_TYPE)}"); continue
        fam, _ = resolve_font(dict(id=sl['id'], font=d.get('font'), family=d.get('font') or 'Bahnschrift', weight=400))
        si = dict(Color1=col(d.get('color1'), '#2A00FF'), Color2=col(d.get('color2'), '#00FFEE'), BgColor=col(d.get('bg'), '#00454D'),
                  MainFontColor=col(d.get('textColor')), FontTopColor=col(d.get('textColor')), FontBottomColor=col(d.get('textColor')),
                  FontFamily=fam, ZoomRate=0.5)
        it = W_('GraphSensor', bx['x'], bx['y'], sl, sensorStyle=style, sensorType=stype, sample=sample, styleInfo=si,
                fields=dict(ZoomRate=0.5))
        it['_box'] = bx; it['_id'] = sl['id']
        items.append(it); rings.append(it)

spec_path = os.path.join(BUILD, 'spec.json')
def write_spec():
    json.dump(dict(name=a.name, seed=SEED, width=W, height=H,
                   items=[{k: v for k, v in i.items() if not k.startswith('_')} for i in items]),
              open(spec_path, 'w', encoding='utf-8'), indent=1)

def build(out, preview, sample, save, isolate=None):
    cmd = ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'build_template.ps1'),
           '-Spec', spec_path, '-Out', out, '-Preview', preview]
    if sample: cmd.append('-Sample')
    if not save: cmd.append('-NoSave')
    if isolate: cmd += ['-IsolateDir', isolate]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit('build_template.ps1 failed:\n' + r.stdout + r.stderr)
    return r.stdout

# ---------------------------------------------------------------- 5. calibrate against the design
bg = np.asarray(Image.open(os.path.join(BUILD, 'background.png')).convert('RGB')).astype(int)
ref = np.asarray(Image.open(os.path.join(BUILD, 'ref-text.png')).convert('RGB')).astype(int)   # text slots only

# every slot's own area, so a slot's reference ink can't pick up a neighbouring slot
slot_rects = [(t['id'], t['ink']) for t in man['texts']]   # only other text can appear in the text-only reference

def ref_ink(box, m=3, own=None):
    x, y, w, h = box
    x0, y0, x1, y1 = max(0, int(x - m)), max(0, int(y - m)), min(W, int(x + w + m + 1)), min(H, int(y + h + m + 1))
    d = np.abs(ref[y0:y1, x0:x1] - bg[y0:y1, x0:x1]).sum(axis=2) > 90
    for sid, r in slot_rects:
        if sid == own: continue
        ax0, ay0 = max(x0, int(r['x'])), max(y0, int(r['y']))
        ax1, ay1 = min(x1, int(np.ceil(r['x'] + r['w']))), min(y1, int(np.ceil(r['y'] + r['h'])))
        if ax0 < ax1 and ay0 < ay1:
            d[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0] = False
    ys, xs = np.nonzero(d)
    return (x0 + xs.min(), y0 + ys.min(), x0 + xs.max(), y0 + ys.max()) if len(xs) else None

iso = os.path.join(BUILD, 'isolate')
for p in range(a.passes):
    write_spec()
    shutil.rmtree(iso, ignore_errors=True)
    build(os.path.join(BUILD, 'cal.template'), os.path.join(BUILD, 'calibrate.png'), True, False, iso)
    worst = 0
    for it in texts:
        al = np.asarray(Image.open(os.path.join(iso, f'{items.index(it)}.png')).convert('RGBA'))[:, :, 3]
        ys, xs = np.nonzero(al > 60)
        r = ref_ink(it['_box'], own=it['_id'])
        if not len(xs) or not r:
            if p == 0: problems.append(f"{it['_id']}: nothing visible to calibrate (empty sample or same colour as background)")
            continue
        q = (xs.min(), ys.min(), xs.max(), ys.max())
        dx = {2: r[2] - q[2], 1: (r[0] + r[2]) / 2 - (q[0] + q[2]) / 2, 0: r[0] - q[0]}[it['align']]
        dy = r[3] - q[3]                                   # baselines (bottom of ink)
        it['x'] = int(it['x'] + round(dx)); it['y'] = int(it['y'] + round(dy))
        if it['interval']:
            dw = ((r[2] - r[0]) - (q[2] - q[0])) / (len(it['sample']) - 1)
            it['interval'] = round(it['interval'] + dw, 2) or 0.01
            worst = max(worst, abs(dw) * (len(it['sample']) - 1))
        it['_h'] = (int(r[3] - r[1]), int(q[3] - q[1]))
        worst = max(worst, abs(dx), abs(dy))
    for it in rings:
        al = np.asarray(Image.open(os.path.join(iso, f'{items.index(it)}.png')).convert('RGBA'))[:, :, 3]
        ys, xs = np.nonzero(al > 60)
        if not len(xs): continue
        bx = it['_box']; inkw = xs.max() - xs.min() + 1
        z = round(it['fields']['ZoomRate'] * min(bx['w'], bx['h']) / inkw, 4)
        dz = abs(z - it['fields']['ZoomRate']) * inkw / max(it['fields']['ZoomRate'], 1e-3)
        it['fields']['ZoomRate'] = z; it['styleInfo']['ZoomRate'] = z
        dx = bx['x'] + (bx['w'] - inkw) / 2 - xs.min(); dy = bx['y'] + (bx['h'] - (ys.max() - ys.min() + 1)) / 2 - ys.min()
        it['x'] = int(round(it['x'] + dx)); it['y'] = int(round(it['y'] + dy))
        worst = max(worst, abs(dx), abs(dy), dz)
    print(f'calibration pass {p + 1}: worst offset {worst:.0f}px' + (' (aligning native text to the design; normally converges to <=1px in 2-3 passes)' if p == 0 else ''))
    if worst <= 1: break
else:
    problems.append(f'calibration did not fully converge (last worst offset {worst:.0f}px)')
for it in texts:
    hr, hq = it.pop('_h', (0, 0))
    if hr and abs(hr - hq) > max(3, hr * 0.12):
        problems.append(f"{it['_id']}: glyph height differs (design {hr}px vs native {hq}px). Usually the font isn't "
                        f"resolving, or the sample text has characters the live value won't.")

# ---------------------------------------------------------------- 6. outputs
write_spec()
tpl = os.path.join(OUT, a.name + '.template')
build(os.path.join(BUILD, 'cal.template'), os.path.join(OUT, a.name + '-preview-sample.png'), True, False)
log = build(tpl, os.path.join(OUT, a.name + '-preview.png'), False, True)
# Final gate: draw the saved file through L-Connect's own device routine (lcd207 LEDController.RenderItem).
# Any exception there means a blank screen on the device.
dr = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', os.path.join(HERE, 'device_render.ps1'),
                     tpl, os.path.join(BUILD, 'device-render.png')], capture_output=True, text=True)
FRAME_LIMIT_KB = 1024        # lcd207 LEDController.UpdateLCD drops frames over 1048576 bytes
FRAME_WARN_KB = 870          # ~85 %: live values, needles and clock hands add a little on top of the sample frame
fm = re.search(r'FRAME bytes=(\d+) landscape=(\d+) portrait=(\d+)', dr.stdout)
frame_kb = int(fm.group(1)) // 1024 if fm else None
if dr.returncode == 5:
    problems.append(f'frame too large for the device: {frame_kb} KB as PNG, limit {FRAME_LIMIT_KB} KB. The screen will stay '
                    'black ("send data out of limit" in the service log). High-entropy art is the usual cause: noise/grain '
                    'textures, fine stripes, big diagonal or dithered gradients. Smooth vertical gradients, bevels and shadows are cheap.')
elif dr.returncode:
    problems.append('L-Connect device render FAILED (the screen would stay blank): ' + dr.stdout.strip()[:400])
else:
    print('device render: OK (' + os.path.join(BUILD, 'device-render.png') + ')')
if frame_kb is not None:
    print(f'frame size: {frame_kb} KB of {FRAME_LIMIT_KB} KB (PNG, worst of landscape/portrait)')
    if FRAME_WARN_KB < frame_kb <= FRAME_LIMIT_KB:
        problems.append(f'frame size {frame_kb} KB is close to the device limit ({FRAME_LIMIT_KB} KB); live values can push it '
                        'over and blank the screen. Reduce texture/noise in the background art.')
elif dr.returncode in (0, 5):
    notes.append('frame size could not be measured')
shutil.copy(os.path.join(BUILD, 'background.png'), os.path.join(OUT, a.name + '-background.png'))
shutil.copy(spec_path, os.path.join(OUT, a.name + '-spec.json'))
shutil.copy(os.path.join(BUILD, 'ref.png'), os.path.join(OUT, a.name + '-design-reference.png'))
for line in log.splitlines():
    if 'WARNING' in line: problems.append(line.strip())
print(f"\nTEMPLATE {tpl}")
from collections import Counter
print(f"layers: 1 background + {len(texts)} text + " + ', '.join(f'{v} {k}' for k, v in Counter(x['kind'] for x in man['slots']).items()) + f"   (theme settings inherited from stock template {os.path.basename(SEED)})")
print('compare: ' + os.path.join(OUT, a.name + '-preview-sample.png') + '  vs  ' + os.path.join(OUT, a.name + '-design-reference.png'))
for n in dict.fromkeys(notes):
    print('NOTE', n)
for pr in dict.fromkeys(problems):
    print('PROBLEM', pr)
