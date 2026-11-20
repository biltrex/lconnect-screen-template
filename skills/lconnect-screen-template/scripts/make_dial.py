"""Print an SVG dial (ticks + numbers) to sit behind a needle or arc slot as static art.

  python -I make_dial.py --size 300 --start -135 --sweep 270 --min 0 --max 110 --major 11 --minor 4 \
         --color "#6E7F99" --label-color "#E6EDF3" --font Bahnschrift --font-size 20 --red-from 90 > dial.svg

Angles match the needle/arc convention: degrees clockwise from 12 o'clock. Paste the <svg> into the
design at the same left/top/width/height as the needle slot (the pivot is the centre).
"""
import argparse, math

ap = argparse.ArgumentParser()
ap.add_argument('--size', type=float, default=300)
ap.add_argument('--start', type=float, default=-135)
ap.add_argument('--sweep', type=float, default=270)
ap.add_argument('--min', type=float, default=0)
ap.add_argument('--max', type=float, default=100)
ap.add_argument('--major', type=int, default=11, help='number of labelled ticks (incl. both ends)')
ap.add_argument('--minor', type=int, default=4, help='minor ticks between major ticks')
ap.add_argument('--radius', type=float, help='outer tick radius (default 46%% of size)')
ap.add_argument('--color', default='#6E7F99')
ap.add_argument('--label-color', default='#E6EDF3')
ap.add_argument('--red-from', type=float, help='value from which ticks/labels turn red')
ap.add_argument('--red', default='#FF5A5A')
ap.add_argument('--font', default='Bahnschrift')
ap.add_argument('--font-size', type=float, default=20)
ap.add_argument('--no-labels', action='store_true')
a = ap.parse_args()

c = a.size / 2
R = a.radius or a.size * 0.46
out = [f'<svg width="{a.size:g}" height="{a.size:g}" viewBox="0 0 {a.size:g} {a.size:g}" xmlns="http://www.w3.org/2000/svg">']
steps = (a.major - 1) * (a.minor + 1)
for k in range(steps + 1):
    frac = k / steps
    val = a.min + frac * (a.max - a.min)
    ang = math.radians(a.start + frac * a.sweep)
    major = k % (a.minor + 1) == 0
    ln = R * (0.12 if major else 0.06)
    colr = a.red if a.red_from is not None and val >= a.red_from else a.color
    x1, y1 = c + R * math.sin(ang), c - R * math.cos(ang)
    x2, y2 = c + (R - ln) * math.sin(ang), c - (R - ln) * math.cos(ang)
    out.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{colr}" '
               f'stroke-width="{3.5 if major else 1.5}" stroke-linecap="round"/>')
    if major and not a.no_labels:
        lr = R - ln - a.font_size * 0.95
        lx, ly = c + lr * math.sin(ang), c - lr * math.cos(ang)
        lc = a.red if a.red_from is not None and val >= a.red_from else a.label_color
        txt = f'{val:g}'
        out.append(f'<text x="{lx:.1f}" y="{ly:.1f}" fill="{lc}" font-family="{a.font}" font-size="{a.font_size:g}" '
                   f'text-anchor="middle" dominant-baseline="central">{txt}</text>')
out.append('</svg>')
print('\n'.join(out))
