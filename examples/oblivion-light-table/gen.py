"""Generates oblivion-light-table.html: a system monitor for the 8.8" screen in the style of the
"Light Table" UI from the film Oblivion. Original artwork; static art is SVG, live slots follow the
data-lc contract (skills/lconnect-screen-template/references/design-contract.md).

  python gen.py --name "MY RIG"

CPU and GPU names are live L-Connect sensors, so they follow whatever PC runs the template.
All other text is native label layers, not background art.

Colours, grid strength (GRID, GRID_LINE, GRID_DOT) and network graph scales (NETMAX) are constants below."""
import argparse, math, os

ap = argparse.ArgumentParser(description="Generate the Oblivion Light Table design")
ap.add_argument("--name", default="WORKSTATION", help="machine name shown top left")
ap.add_argument("--preview-js", default="../../skills/lconnect-screen-template/scripts/lc-preview.js", help="path to lc-preview.js for the browser preview")
ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "oblivion-light-table.html"))
args = ap.parse_args()

BG, FAINT, LINE, DIM, ICE, CYAN, CORAL = "#0A0F12", "#1C2A31", "#35505B", "#6F8C96", "#D6ECF1", "#55D2E3", "#F2603F"
CYAN_OFF, CORAL_OFF, ICE_OFF = "#102429", "#2B1814", "#1B2529"
out = []
A = out.append

def ticks(cx, cy, r1, r2, n, a0=0, a1=360, every=None, rlong=None, color=LINE, w=1, skip=None):
    s = []
    for i in range(n + (0 if a1 - a0 >= 360 else 1)):
        a = a0 + (a1 - a0) * i / n
        if skip and skip(a): continue
        ro = rlong if (every and i % every == 0 and rlong) else r2
        t = math.radians(a)
        x1, y1 = cx + r1 * math.sin(t), cy - r1 * math.cos(t)
        x2, y2 = cx + ro * math.sin(t), cy - ro * math.cos(t)
        s.append(f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}"/>')
    return f'<g stroke="{color}" stroke-width="{w}">' + "".join(s) + "</g>"

def arcpath(cx, cy, r, a0, a1):
    p = lambda a: (cx + r * math.sin(math.radians(a)), cy - r * math.cos(math.radians(a)))
    (x0, y0), (x1, y1) = p(a0), p(a1)
    return f'M{x0:.1f},{y0:.1f} A{r},{r} 0 {1 if a1 - a0 > 180 else 0} 1 {x1:.1f},{y1:.1f}'

def bracket(x, y, w, h, l=14, c=DIM):
    return (f'<path d="M{x},{y+l} V{y} H{x+l} M{x+w-l},{y} H{x+w} V{y+l} M{x+w},{y+h-l} V{y+h} H{x+w-l} '
            f'M{x+l},{y+h} H{x} V{y+h-l}" fill="none" stroke="{c}" stroke-width="1.5"/>')

def cross(x, y, s=6, c=DIM):
    return f'<path d="M{x-s},{y} H{x+s} M{x},{y-s} V{y+s}" stroke="{c}" stroke-width="1"/>'

LBL = []   # static text: native L-Connect label layers, never baked into the background art
def label(x, y, t, c=DIM, size=13, sp=3, anchor="start", w=400):
    """A label whose baseline sits at y (like SVG text). Returns '' so S(label(...)) still reads naturally."""
    BW = 600                                    # box width for centred / right-anchored labels
    left = {"start": x, "middle": x - BW / 2, "end": x - BW}[anchor]
    al = {"start": "left", "middle": "center", "end": "right"}[anchor]
    width = "" if anchor == "start" else f"width:{BW}px;"
    LBL.append(f'<div class="s" data-lc="label" data-align="{al}" style="left:{left:g}px;top:{y - 0.79 * size:g}px;{width}'
               f'text-align:{al};font-size:{size}px;font-weight:{w};letter-spacing:{sp}px;color:{c}">{t}</div>')
    return ""

# ---------------------------------------------------------------- static art (one full-size SVG)
svg = []
S = svg.append
# faint map grid with brighter dots at the intersections (Light Table style)
GRID, GRID_LINE, GRID_DOT = 32, "#121D23", "#2B3D45"
S(f'<defs><pattern id="grid" x="24" y="28" width="{GRID}" height="{GRID}" patternUnits="userSpaceOnUse">'
  f'<path d="M0,0.5 H{GRID} M0.5,0 V{GRID}" stroke="{GRID_LINE}" stroke-width="1" fill="none"/>'
  f'<rect x="0" y="0" width="2" height="2" fill="{GRID_DOT}"/></pattern></defs>')
S(f'<rect x="24" y="28" width="1873" height="425" fill="url(#grid)"/>')
# a few plotted markers, like the map's tagged contacts
for gx, gy, tag in ((13, 1, "26 016"), (25, 12, "26 018"), (25, 1, "04 049")):
    x, y = 24 + gx * GRID, 28 + gy * GRID
    S(f'<rect x="{x-4}" y="{y-4}" width="9" height="9" fill="none" stroke="#4E8C99" stroke-width="1"/>'
      f'<rect x="{x-1}" y="{y-1}" width="3" height="3" fill="#4E8C99"/>')
    S(label(x + 10, y + 4, tag, "#3E5A66", 10, 1))
# outer frame: hairline rule top and bottom with registration marks
S(f'<path d="M24,28 H1896 M24,452 H1896" stroke="{FAINT}" stroke-width="1"/>')
for x in range(24, 1897, 48):
    S(f'<line x1="{x}" y1="24" x2="{x}" y2="28" stroke="{LINE}"/><line x1="{x}" y1="452" x2="{x}" y2="456" stroke="{LINE}"/>')
for x, y in [(24, 28), (1896, 28), (24, 452), (1896, 452), (436, 28), (1236, 28), (1616, 28), (436, 452), (1236, 452), (1616, 452)]:
    S(cross(x, y, 7, DIM))
# column dividers
for x in (436, 1236, 1616):
    S(f'<line x1="{x}" y1="44" x2="{x}" y2="436" stroke="{FAINT}" stroke-width="1"/>')
    S(ticks(0, 0, 0, 0, 0))
    for y in range(60, 430, 24):
        S(f'<line x1="{x-3}" y1="{y}" x2="{x+3}" y2="{y}" stroke="{LINE}"/>')
# coral accent marks (the Light Table's red tabs)
S(f'<rect x="24" y="456" width="40" height="4" fill="{CORAL}"/><rect x="1856" y="20" width="40" height="4" fill="{CORAL}"/>')

# ---- left column: identity, hardware, clock
S(bracket(40, 44, 380, 392, 16, LINE))
# logo: inverted triangle mark
S(f'<path d="M58,62 H110 L84,104 Z M70,70 H98 L84,93 Z" fill="none" stroke="{ICE}" stroke-width="2.5"/>')
S(label(124, 74, "DESIGNATION", DIM, 12, 4))
S(f'<circle cx="398" cy="69" r="5" fill="{CYAN}"/>')
S(label(386, 74, "ONLINE", CYAN, 13, 3, "end"))
S(f'<line x1="56" y1="126" x2="404" y2="126" stroke="{FAINT}"/>')
# hardware rows: boxed tags
for y, tag in ((140, "CPU"), (184, "GPU")):
    S(f'<rect x="56" y="{y}" width="58" height="26" fill="none" stroke="{CYAN}" stroke-width="1.2"/>')
    S(label(85, y + 18, tag, CYAN, 13, 3, "middle", 600))
S(f'<line x1="56" y1="226" x2="404" y2="226" stroke="{FAINT}"/>')
S(label(56, 254, "LOCAL TIME", DIM, 12, 4))
S(label(404, 254, "24H", DIM, 12, 4, "end"))
S(f'<line x1="56" y1="358" x2="404" y2="358" stroke="{FAINT}"/>')
S(label(56, 384, "STARDATE", DIM, 12, 4))
# mini signal strip (static decoration)
for i in range(36):
    h = 4 + int(14 * abs(math.sin(i * 1.7) * math.cos(i * 0.6)))
    S(f'<rect x="{56 + i * 6}" y="{424 - h}" width="3" height="{h}" fill="{LINE}"/>')
S(label(404, 424, "SIG 04 / 49", DIM, 12, 3, "end"))

# ---- CPU and GPU concentric gauges
def gauge(L, T, name, sub):
    cx, cy = L + 180, T + 180
    S(f'<circle cx="{cx}" cy="{cy}" r="178" fill="none" stroke="{FAINT}" stroke-width="1"/>')
    S(ticks(cx, cy, 166, 172, 72, every=6, rlong=176, color=LINE))
    S(f'<circle cx="{cx}" cy="{cy}" r="104" fill="none" stroke="{FAINT}" stroke-width="1"/>')
    S(f'<circle cx="{cx}" cy="{cy}" r="96" fill="none" stroke="{LINE}" stroke-width="1" stroke-dasharray="2 6"/>')
    S(f'<path d="{arcpath(cx, cy, 116, -135, 135)}" fill="none" stroke="{FAINT}" stroke-width="1"/>')
    S(ticks(cx, cy, 112, 120, 10, -135, 135, color=DIM))
    # crosshair arms outside the ring
    S(f'<path d="M{L-6},{cy} H{L+14} M{L+346},{cy} H{L+366} M{cx},{T-6} V{T+12}" stroke="{DIM}" stroke-width="1"/>')
    S(label(cx - 104, cy + 140, "0", DIM, 12, 1, "middle"))
    S(label(cx + 104, cy + 140, "100", DIM, 12, 1, "middle"))
    S(label(cx, cy - 74, f"{name} LOAD  %", DIM, 13, 4, "middle"))
    S(label(cx, cy + 118, "TEMP  °C", CORAL, 11, 4, "middle"))
    S(label(cx, T + 348, name, ICE, 22, 8, "middle", 300))
    S(label(cx, T + 372, sub, DIM, 11, 4, "middle"))
gauge(456, 40, "CPU", "PROCESSOR CORE")
gauge(856, 40, "GPU", "GRAPHICS CORE")

# ---- memory: concentric full rings
mx, my = 1426, 196
S(f'<circle cx="{mx}" cy="{my}" r="152" fill="none" stroke="{FAINT}"/>')
S(ticks(mx, my, 146, 150, 100, every=10, rlong=156, color=LINE))
S(f'<circle cx="{mx}" cy="{my}" r="82" fill="none" stroke="{FAINT}"/>')
S(cross(mx, my - 120, 5, DIM))
S(label(mx, my - 54, "MEMORY  %", DIM, 12, 4, "middle"))
S(f'<line x1="{mx-40}" y1="{my+6}" x2="{mx+40}" y2="{my+6}" stroke="{FAINT}"/>')
S(label(1256, 382, "RAM", ICE, 14, 4, "start", 600))
S(label(1256, 426, "VRAM", CYAN, 14, 4, "start", 600))
S(label(1596, 382, "GB", DIM, 13, 2, "end"))
S(label(1596, 426, "MB", DIM, 13, 2, "end"))
S(f'<line x1="1256" y1="396" x2="1596" y2="396" stroke="{FAINT}"/>')

# ---- network: two history plots
for top, name, tag in ((44, "UPLINK", "SEND"), (244, "DOWNLINK", "RECV")):
    S(label(1636, top + 20, name, DIM, 12, 4))
    S(f'<rect x="1636" y="{top + 30}" width="54" height="22" fill="none" stroke="{CORAL if tag == "SEND" else CYAN}" stroke-width="1.2"/>')
    S(label(1663, top + 46, tag, CORAL if tag == "SEND" else CYAN, 12, 3, "middle", 600))
    S(label(1880, top + 20, "KB/S", DIM, 12, 3, "end"))
    S(bracket(1636, top + 96, 256, 84, 8, LINE))
    S(label(1892, top + 91, f"SCALE 0-{(250, 1000)[top > 100]}", DIM, 10, 2, "end"))
    for gy in (top + 117, top + 138, top + 159):
        S(f'<line x1="1644" y1="{gy}" x2="1884" y2="{gy}" stroke="{FAINT}" stroke-dasharray="1 5"/>')

svg_html = (f'<svg class="abs" style="left:0;top:0" width="1920" height="480" viewBox="0 0 1920 480" '
            f'font-family="Bahnschrift">' + "".join(svg) + "</svg>")

# ---------------------------------------------------------------- live slots
L = []
def text(sensor, x, y, w, size, color, sample, align="right", weight=300, sub=None, label=None, extra=""):
    s = f' data-sub="{sub}"' if sub else ""
    L.append(f'<div class="v" data-lc="text" data-sensor="{sensor}"{s} data-align="{align}" data-label="{label or sensor}" '
             f'style="left:{x}px;top:{y}px;width:{w}px;font-size:{size}px;font-weight:{weight};color:{color};text-align:{align};{extra}">{sample}</div>')
def unit(x, y, t, size=20, color=DIM):
    L.append(f'<div class="u" data-lc="label" data-align="left" style="left:{x}px;top:{y}px;font-size:{size}px;color:{color}">{t}</div>')
def arc(sensor, x, y, size, th, on, off, sample, label, start=226.8, sweep=270, extra=""):
    L.append(f'<div data-lc="arc" data-sensor="{sensor}" data-start="{start}" data-sweep="{sweep}" data-thickness="{th}" '
             f'data-on="{on}" data-off="{off}" data-sample="{sample}" data-label="{label}" {extra} '
             f'style="position:absolute;left:{x}px;top:{y}px;width:{size}px;height:{size}px"></div>')

# left column: machine name is a label; CPU / GPU names are live sensors, so the template adapts to any PC
L.append(f'<div class="s" data-lc="label" data-align="left" data-label="Machine name" style="left:124px;top:84px;font-size:32px;font-weight:300;letter-spacing:6px;color:{ICE}">{args.name}</div>')
text("CPUMODEL", 128, 145, 276, 19, ICE, "AMD Ryzen 7 7800X3D", "left", 300, label="CPU model", extra="letter-spacing:0")
text("GPUMODEL", 128, 189, 276, 19, ICE, "NVIDIA GeForce RTX 4080", "left", 300, label="GPU model", extra="letter-spacing:0")
# clock 14 : 07 : 23 as three tracked slots with static colons
for i, (sub, smp) in enumerate((("h_24", "14"), ("m", "07"), ("s", "23"))):
    text("TIME", 54 + i * 124, 262, 104, 84, ICE if i < 2 else CYAN, smp, "center", 300, sub, f"Time {sub}")
for x in (160, 284):
    L.append(f'<div class="s" data-lc="label" data-align="left" style="left:{x}px;top:270px;font-size:70px;font-weight:300;color:{DIM}">:</div>')
# date: Thu  11 . 19 . 2026
text("DAY", 160, 368, 70, 28, CYAN, "Thu", "left", 400, "Day_en", "Weekday", "letter-spacing:0")
text("DATE", 232, 368, 36, 28, ICE, "11", "center", 300, "M", "Month")
text("DATE", 278, 368, 36, 28, ICE, "19", "center", 300, "D", "Day")
text("DATE", 326, 368, 80, 28, ICE, "2026", "left", 300, "Y", "Year")
for x in (268, 314):
    L.append(f'<div class="s" data-lc="label" data-align="left" style="left:{x}px;top:368px;font-size:28px;font-weight:300;color:{DIM}">.</div>')

# CPU / GPU gauges: outer segmented load arc, inner thin temperature arc
for L0, p, load, temp, tmax in ((456, "CPU", 23, 58, 110), (856, "GPU", 34, 51, 100)):
    arc(f"{p}LOAD", L0 + 22, 62, 316, 14, CYAN, CYAN_OFF, load, f"{p} load arc", extra='data-block="3" data-gap="3"')
    arc(f"{p}TEMP", L0 + 52, 92, 256, 4, CORAL, CORAL_OFF, temp, f"{p} temp arc", extra="data-round")
    text(f"{p}LOAD", L0 + 80, 168, 200, 100, ICE, load, "center", 300, label=f"{p} load")
    text(f"{p}TEMP", L0 + 120, 280, 120, 40, CORAL, temp, "center", 300, label=f"{p} temp")

# memory: RAM outer ring, VRAM inner ring
arc("RAMLOAD", 1426 - 138, 196 - 138, 276, 12, ICE, ICE_OFF, 37, "RAM ring", start=0, sweep=360, extra="data-round")
arc("GPURAMLOAD", 1426 - 112, 196 - 112, 224, 12, CYAN, CYAN_OFF, 43, "VRAM ring", start=0, sweep=360, extra="data-round")
text("RAMLOAD", 1346, 150, 160, 48, ICE, 37, "center", 300, label="RAM %")
text("GPURAMLOAD", 1346, 212, 160, 48, CYAN, 43, "center", 300, label="VRAM %")
text("RAM_GB", 1344, 358, 96, 35, ICE, "23.4", "right", 300, label="RAM used")
unit(1446, 361, "/", 31)
text("RAMTOTAL_GB", 1458, 358, 104, 35, DIM, "64.0", "right", 300, label="RAM total")
text("GPURAM", 1344, 402, 96, 35, CYAN, "6963", "right", 300, label="VRAM used")
unit(1446, 405, "/", 31)
text("GPURAMTOTAL", 1458, 402, 104, 35, DIM, "16303", "right", 300, label="VRAM total")

# network
NETMAX = {"UPSPEED": 250, "DOWNSPEED": 1000}
for top, key, col, smp, hist in ((44, "UPSPEED", CORAL, 52, "40,44,52,61,48,39,45,58,70,52,47,41,55,63,58,49,44,52,66,250,250,180,72,55,48,51,46,52,60,57,49,52"),
                                 (244, "DOWNSPEED", CYAN, 348, "330,342,355,348,361,337,350,344,358,370,352,341,349,356,348,360,345,1000,1000,1000,640,380,352,347,355,349,342,361,350,346,353,348")):
    text(key, 1700, top + 30, 140, 46, ICE, smp, "right", 300, label=f"{key.title()} value")
    L.append(f'<div data-lc="chart" data-sensor="{key}" data-step="8" data-max="{NETMAX[key]}" data-color="{col}" data-fill-color="{col}26" '
             f'data-line-width="1.5" data-anchor="right" data-history="{hist}" data-label="{key.title()} history" '
             f'style="position:absolute;left:1636px;top:{top + 96}px;width:256px;height:84px"></div>')

html = f"""<!DOCTYPE html>
<!-- Oblivion Light Table style system monitor for the Lian Li Universal Screen 8.8".
     Inspired by the look of GMUNK's Oblivion GFX; original artwork. Generated by gen.py. -->
<html lang="en"><head><meta charset="utf-8"><title>Oblivion Light Table monitor</title>
<style>
  html,body{{margin:0;padding:0;width:1920px;height:480px;overflow:hidden;background:{BG}}}
  body{{position:relative;font-family:'Bahnschrift',sans-serif;color:{ICE}}}
  .abs{{position:absolute}}
  .v,.u,.s{{position:absolute;line-height:1;white-space:nowrap}}
  .u{{font-weight:300;letter-spacing:1px}}
  [data-lc="text"]{{text-transform:none}}
</style></head>
<body>
{svg_html}
{chr(10).join(LBL)}
{chr(10).join(L)}
<script src="{args.preview_js}"></script>
</body></html>
"""
open(args.out, "w", encoding="utf-8").write(html)
print("wrote", args.out)
