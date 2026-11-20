# Design contract: HTML that converts to a native L-Connect template

A design is one static HTML page. Everything that never changes becomes a single background
image. Every element marked `data-lc` becomes a native, live L-Connect widget placed exactly where
it sits in the page. The page doubles as the preview, so it should look finished with sample values.

There are eight slot kinds: `text`, `bar`, `slider`, `arc`, `chart`, `needle`, `ring` and `image`.
`assets/starter.html` shows text and bars, and `assets/starter-gauges.html` shows every kind.

This file is also the brief to give Claude Design: paste the "Brief for Claude Design" section
at the end into a Claude Design prompt along with the look you want.

## Canvas

- `html, body { margin:0; width:1920px; height:480px; overflow:hidden; background:#000 }` for the
  landscape 8.8" screen. Lay everything out in absolute pixels; the export screenshots at exactly 1920×480.
- Everything outside `data-lc` slots is static art. It can use any CSS, SVG, images or gradients,
  because it is flattened to one PNG. Dials, tick marks, scales and clock faces belong here.
- **Keep the art compressible.** Each frame goes to the screen as a PNG under 1 MB; bigger frames are
  dropped and the screen stays black. Avoid noise/grain (`feTurbulence`), fine stripe patterns and large
  diagonal gradients. Smooth vertical gradients, bevels, shadows and glass highlights are fine. The build
  reports the frame size.
- No JavaScript is needed. `scripts/lc-preview.js` draws the browser preview of bars, sliders, arcs,
  charts, needles and rings from their attributes. The exporter injects it automatically; include it in
  the page too (`<script src>` or inline) so the design previews correctly when opened in a browser.
  It only draws into slots that are empty, so hand-made preview art inside a slot wins.
- Any other script must show the sample values by the `load` event; the exporter freezes all timers at load.
- Mockups that build their widgets in JS from a manifest: run `scripts/snapshot_dom.py` to freeze the
  rendered DOM into static HTML first, then tag that.
- Avoid CSS 3D transforms (`perspective`, `rotateX`) underneath panels: Chrome composites them above
  later siblings, so they can show through. Use them only where nothing should cover them, or flatten them
  into an image.

## Common attributes

| Attribute | Meaning |
|---|---|
| `data-lc` | slot kind |
| `data-sensor` | L-Connect sensor key (`sensors.md`); `data-sub` = format variant for clock keys |
| `data-sample` | preview value. For meters it's the sensor **value** read on L-Connect's own scale (load 0–100 %; CPU temperature against 110 °C; network against 100 KB/s), so the preview matches the screen |
| `data-on` / `data-off` | lit / unlit (track) colour, `#RRGGBB` or CSS `#RRGGBBAA` |
| `data-label` | layer name shown in L-Connect |

Slots are positioned boxes (`position:absolute` with left/top/width/height). The box is the widget.

## `text`: live value

```html
<span data-lc="text" data-sensor="CPUTEMP" data-align="right" data-label="CPU temp"
      style="position:absolute; left:1400px; top:180px; width:120px; text-align:right;
             font:600 54px 'Antonio'; color:#FF9966">58</span><span class="unit">°C</span>
```

- **Contents = the sample value, exactly as L-Connect will print it** (see `sensors.md`: `58`,
  `14:07:23`, `23.4`, `1434`, `Thu`). No units and no child elements: one plain string.
- One colour, one font family/weight and one size per slot. Bold and italic work. Units, labels and
  separators are separate static elements.
- `data-align`: `right` (default; the number grows leftward, unit on its right), `left`, or
  `center`. Pick the side that stays fixed when the value gets longer.
- **Gradient text:** `data-gradient="#00E5FF"` blends from the CSS `color` to that colour, and
  `data-gradient-dir` 1 (horizontal, default), 2 or 3 sets the direction.
- Leave room for the widest real value (`100`, `12902`); native text is never clipped or shrunk.
- Don't use `text-transform`; type the real casing. Designs often inherit it from a container, so add
  `[data-lc="text"] { text-transform: none }`. `letter-spacing` is reproduced only on digit-only values,
  so set `letter-spacing: 0` on other live slots and the preview shows what the screen will. To keep
  tracking on a clock, split it into `h_24`, `m` and `s` slots with static colons.
- Optional `data-font="Family Name"` forces the exact Windows font family name.
- A number inside a gauge (centred in an arc, under a needle) is fine; text is calibrated on its own.
- **Units next to values** (mockups usually glue them together, like `61<span>°C</span>`): split them into a live
  value slot and a static unit element. `python -I scripts/measure.py <page> --selector "<css>"` prints the exact
  boxes of the original value and unit spans, so both can be placed exactly where the mockup had them. Static
  units keep the container's `text-transform`, which is usually what preserves the look (`GHZ`, `KB/S`); only the
  live slot needs `text-transform: none`.
- **Values whose width changes** (`7.4` → `12.8`, `640` → `12902`): anchor the value on the side where the unit sits.
  With the unit after the number, use `data-align="right"` and put the unit just to the right of the value box, so
  longer values grow leftward, away from the unit. If the value must stay left-aligned (the left edge lines up
  with other text), put the unit above or below it, or leave room for the widest value before the unit.

## `bar`: linear meter

```html
<div data-lc="bar" data-sensor="RAMLOAD" data-segments="48" data-gap="4"
     data-on="#FF9900" data-off="#3D2500" data-sample="37"
     style="position:absolute; left:258px; top:234px; width:762px; height:62px"></div>
```

| Attribute | Meaning |
|---|---|
| `data-fill` | `ltr` (default for wide boxes), `rtl`, `btt` (default for tall boxes: vertical, fills upward), `ttb` |
| `data-segments`, `data-gap` | number of blocks and the gap between them in px (0 = solid bar). Block size is rounded, so the bar may shift ±1–2 px |
| `data-radius` | rounded ends (solid bars) |
| `data-gradient` | the fill blends from `data-on` to this colour |
| `data-track` | `solid` (default: track filled with `data-off`), `outline` (a `data-line-width` px border), `none` |

## `slider`: bar with a knob

Like a horizontal `bar` (`data-fill` `ltr`/`rtl`), plus a round knob at the value: `data-knob` is the
knob diameter in px (default 2 × the bar height). Make the box the thin track (8–12 px tall); the knob
overhangs it.

## `arc`: ring, gauge, half-arc, pie

```html
<div data-lc="arc" data-sensor="CPULOAD" data-start="226.8" data-sweep="270" data-thickness="26" data-round
     data-on="#2F81F7" data-gradient="#00E5FF" data-off="#132235" data-sample="64"
     style="position:absolute; left:66px; top:76px; width:260px; height:260px"></div>
```

| Attribute | Meaning |
|---|---|
| box | a square; the arc's **outer** edge touches it |
| `data-thickness` | stroke width in px. Thickness = half the box width gives a full pie |
| `data-start` | where 0 % sits, in degrees clockwise from 12 o'clock. Stored as whole percent of a turn, so use multiples of 3.6° to avoid a rounding NOTE: **226.8** for a 270° gauge open at the bottom, 270 for a half arc over the top, 0 for a ring |
| `data-sweep` | degrees at 100 % (360 ring, 270 gauge, 180 half) |
| `data-round` | rounded ends |
| `data-block`, `data-gap` | segmented arc: block and gap length in px |
| `data-gradient` | colour blends along the sweep |
| `data-off` / `data-track="none"` | track colour / no track |
| `data-border` | thin outline rings, px |
| `data-reverse` | counter-clockwise |

Put the number in the middle as a separate `text` slot.

## `chart`: scrolling history

```html
<div data-lc="chart" data-sensor="CPULOAD" data-step="8" data-color="#00E5FF" data-fill-color="#00E5FF30"
     style="position:absolute; left:480px; top:80px; width:544px; height:120px"></div>
```

| Attribute | Meaning |
|---|---|
| `data-step` | px between samples. Make the width a multiple of it (samples kept = width ÷ step) |
| `data-color`, `data-line-width` | the line |
| `data-fill-color` | area under the line, with alpha as the opacity you want to see (the build compensates for L-Connect drawing fills stronger) |
| `data-frame`, `data-frame-width` | border around the chart |
| `data-anchor="right"` | newest sample at the right edge |
| `data-max` | value at the top (100) |
| `data-history` | comma list of preview samples (optional) |

The device starts empty and fills as data arrives. Dials, scales and numbered ticks are static art:
`python -I scripts/make_dial.py` prints an SVG with numbered ticks for a given start/sweep/range.

## `needle`: needle gauge or clock hand

```html
<div data-lc="needle" data-sensor="CPUTEMP" data-start="-135" data-sweep="270" data-color="#FF5A5A"
     data-sample="55" style="position:absolute; left:1118px; top:80px; width:300px; height:300px"></div>
```

- The box centre is the pivot. The needle points at `data-start + value × data-sweep` degrees
  (clockwise from 12 o'clock): `-135` / `270` makes a classic gauge.
- The needle is generated from `data-color`, `data-length` (default 42 % of the box), `data-width`
  (default 6 % of the length, min 2 px), `data-tail` (default 18 % of the length), all in px, and `data-cap`
  (pivot dot colour, default white, or `none`). Or use `data-image="needle.png"` (path relative to the HTML): an image that
  points **up** with the pivot at its centre.
- **Analog clock:** three needle slots on the same box with `data-sensor="TIME"` and `data-sub` set to
  `h_12`, `m` and `s` (start 0, sweep 360 are the defaults for TIME). Draw the dial as static art.

## `ring`: Lian Li sensor style

`data-style` is `Ring1`–`Ring5`. `data-sensor` is one of `CPULOAD`, `CPUTEMP`, `GPULOAD`, `GPUTEMP`
or `CPUFAN` (`CPUTEMP_F`/`GPUTEMP_F` for °F). Colours: `data-color1`, `data-color2` (arc gradient),
`data-bg` (track), `data-text-color`, and optionally `data-font`. The widget is scaled to fit the box.
These are Lian Li's own polished gauges; they draw their own "CPU"/"LOAD" labels, and the browser
preview only approximates them. Other styles (SENSOR_6, SENSOR_7, Pic) crash the screen and are rejected.

## `image`: separate image layer

`<img data-lc="image" src="logo.png" style="position:absolute; left:…; top:…; width:…">`: kept as its own
layer above the background (e.g. art that must sit on top of a live widget). Otherwise images are just
static art.

## Fonts

- The L-Connect service runs as LocalSystem, so **every font must be installed for all users**
  (C:\Windows\Fonts). A font installed only for the current user renders as Arial on the screen,
  and every position drifts because it was calibrated on the real font.
- Embed the same font in the page (`@font-face`, a local file next to the HTML, or base64) so the
  browser preview matches.
- Variable fonts work. Windows exposes each named weight as its own family (`Antonio SemiBold`,
  `Bahnschrift Light`); the tool maps CSS `font-weight` to those names automatically.
- Safe fonts present on every Windows 10/11 PC: Bahnschrift (condensed-friendly variable font,
  good for dashboards), Segoe UI, Segoe UI Variable, Consolas, Cascadia Mono/Code (Windows 11), Arial, Impact.

## Not possible natively (design around it)

- Colours that change with the value (no alert-red at thresholds).
- Mixed styles inside one value, smaller units glued to a number, or custom number formats.
- Text transforms (DAY gives `Thu`, not `THURSDAY`). Network is KB/s only, VRAM is MB only.
- Animated overlays: GIF/video layers aren't drawn by the 8.8" device loop. Animation only exists
  as a full background video, which this tool doesn't build yet.
- `FPS` only has data when L-Connect's FPS monitoring is running.

## Brief for Claude Design

> Design a 1920×480 px landscape dashboard for a PC case screen (Lian Li Universal Screen 8.8").
> Deliver one self-contained HTML file: body exactly 1920×480, dark background, all elements absolutely
> positioned, fonts embedded, realistic sample values, no animation. Static art (panels, labels, units,
> dials, ticks, clock faces) is drawn normally. Every LIVE element is an empty, absolutely positioned box
> (or, for text, a plain-text element) with these attributes:
> - Number/text: `data-lc="text" data-sensor="<KEY>" data-align="left|right|center"`; the content is only the
>   sample value; one colour, font and size; optional `data-gradient="<hex>"`.
> - Linear meter: `data-lc="bar" data-sensor data-on data-off data-sample [data-fill="ltr|rtl|btt|ttb"]
>   [data-segments data-gap] [data-radius] [data-gradient] [data-track="solid|outline|none"]`.
> - Slider: `data-lc="slider"`, as a bar plus `data-knob="<px>"`.
> - Ring/gauge: `data-lc="arc"` on a square box, with `data-thickness data-start="<deg from 12 o'clock>"
>   data-sweep="<deg>" data-on data-off data-sample [data-round] [data-gradient] [data-block data-gap]`.
> - History chart: `data-lc="chart" data-step="<px>" data-color [data-fill-color] [data-anchor="right"]`.
> - Needle: `data-lc="needle"` on a square box (pivot = centre), with `data-start data-sweep data-color data-sample`.
>   Clock hands: `data-sensor="TIME" data-sub="h_12|m|s"`.
>
> Keep the art compressible: no noise/grain textures (feTurbulence), fine stripe patterns or big diagonal
> gradients, because every frame must encode to a PNG under 1 MB or the screen goes black. Smooth vertical
> gradients, bevels, shadows and glass highlights are fine. Colours can't change with the value, and there's no text-transform on live text. Leave room for the widest
> value. Sensor keys: CPUTEMP CPULOAD CPUCLOCK_G CPUPWR CPUFAN GPUTEMP GPULOAD GPUCLOCK_G GPUPWR GPUFAN
> GPURAM(MB) GPURAMLOAD RAM_GB RAMLOAD UPSPEED DOWNSPEED(KB/s); clock: TIME(h:m:s|h:m), DATE(Y-M-D|Y|M|D|M_en),
> DAY(Day_en → "Thu").
