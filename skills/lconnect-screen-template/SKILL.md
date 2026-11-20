---
name: lconnect-screen-template
description: Design and build native Lian Li L-Connect 3 templates (.template files) for the Lian Li Universal Screen 8.8" (1920x480 landscape LCD), with live sensor widgets (numbers, bars, sliders, arc/ring gauges, history charts, needle gauges, analog clocks, Lian Li sensor rings for CPU/GPU temps and loads, RAM, VRAM, network and time) placed over a designed background. Turns a Claude Design HTML mockup, or just a description of the look the user wants, into a working template, previews it with L-Connect's own renderer, and installs it. Use this whenever someone mentions L-Connect, Lian Li screens or LCDs, the Universal Screen, a .template file, a PC case display or sensor-panel dashboard, or wants to turn an HTML or Claude Design mockup into something their Lian Li screen can run, even if they don't say "template".
---

# L-Connect screen templates

Turn a design into a native L-Connect 3 template for the Lian Li Universal Screen 8.8" (1920×480).
The static art is flattened into one background image. Every live value becomes a real L-Connect
widget: text, bar, slider, arc gauge, history chart, needle or analog clock hand, Lian Li sensor ring,
or image layer. Text is positioned by rendering it with L-Connect's own engine and nudging it until
its glyphs line up with the design to within a pixel. The other widgets map their box geometry
exactly onto the engine's (measured) fields. Every build ends by replaying L-Connect's own per-frame
device render on the saved file.

The user should be able to get from an idea to a template running on their screen just by prompting.
So do the work yourself: write or adapt the HTML, build, look at the previews, fix, and install.
Only stop to ask about taste (look, layout, which stats to show) or before touching their system.

## Requirements (check once, up front)

This runs on the user's Windows PC, because it uses L-Connect's installed engine:
- L-Connect 3 at `C:\Program Files\Lian-Li\L-Connect 3` (`lianli.ThemeEngine.dll`)
- Python 3 with Pillow and numpy (`python -I -c "import PIL, numpy"`)
- Chrome or Edge (headless screenshots)
- Fonts used for live values installed **for all users** (see Fonts below)

If something is missing, say what and how to get it; don't try to work around L-Connect being absent.

`SKILL` below means this skill's folder. Scripts live in `SKILL/scripts`.

## Workflow

### 1. Get a design that follows the contract

Read `references/design-contract.md` first. It defines the markup the build reads: positioned boxes
marked `data-lc="text|bar|slider|arc|chart|needle|ring|image"` with a `data-sensor` key and a few
attributes. `references/sensors.md` lists the keys and exactly what each one prints.
`references/widgets.md` is the deep reference for what the engine can do (read it for unusual requests).

Where the design comes from:
- **The user describes what they want.** Write the HTML yourself, starting from a working example:
  `assets/starter.html` (numbers and bars) or `assets/starter-gauges.html` (every widget kind: arc gauge,
  slider, vertical bar, charts, needle gauge, analog clock, sensor ring, gradient text). Aim for something
  that looks designed: a clear hierarchy, large numerals, restrained colour. Ask about theme and which
  stats matter if they haven't said; otherwise make sensible choices (CPU/GPU temp + load, RAM, clock is a
  good default). Use the gauge kinds when they suit the look; they're native, not pictures.
  Dials, ticks and clock faces are static art behind the live needle/arc slots.
  Include `SKILL/scripts/lc-preview.js` in the page (inline its contents before `</body>`, or copy the file
  next to the HTML and use `<script src="lc-preview.js">`) so the gauges preview in a browser. The starter
  points at `../scripts/lc-preview.js` only because it lives inside the skill; fix that path when you copy it.
  The build injects the script anyway, so the template itself never depends on it.
- **They have a Claude Design (or other) HTML mockup.** Keep their file untouched and write an adapted
  copy (`<name>.lc.html`):
  - Mark each live element with `data-lc` and a sensor key.
  - Make its content the sample value in L-Connect's format (`1434` KB/s, not `1.4 MB/s`; `Thu`, not `THURSDAY`).
  - Move units and labels into separate static elements, and remove `text-transform` from live slots.
  - Replace JS-generated widgets with static markup showing sample values.

  If the mockup builds its widgets in JavaScript (common in Claude Design), first freeze it:
  `python -I SKILL/scripts/snapshot_dom.py <design.html> <name>.lc.html --query "demo=0"` (use whatever
  query stops its demo animation). That gives real elements to tag, and it beats regenerating the markup.
  `python -I SKILL/scripts/measure.py <page> --selector "<css>"` reports where the mockup's values and units
  sit, so split-out static units land exactly where they were.
  Tell the user plainly about each behaviour that can't be native (alert colours, unit switching, uppercase
  weekdays). Don't silently drop them.
- **They want widgets added to a design you (or they) already built.** Work on a copy (`<name>-v2.html`);
  the original stays untouched. Make room deliberately: shrink or move secondary elements, or replace a
  plain bar or number with the richer widget that shows the same sensor. Say what you moved. If the page has
  its own old preview script for bars (`.track` segments), replace it with `lc-preview.js` (which only draws
  into empty slots). Leave intentional look-and-feel quirks alone unless asked.
- **They want to use Claude Design themselves.** Give them the "Brief for Claude Design" section of
  `references/design-contract.md` to paste in with their style request, then continue from their HTML.

Preview the design before building if the look hasn't been agreed:
`python -I SKILL/scripts/export_design.py <design.html> <build_dir>`, then view `<build_dir>/ref.png`.

### 2. Build

```
python -I SKILL/scripts/make_template.py <design.html> --name <Template-Name> [--out <dir>] [--build <dir>]
```

This takes from a few seconds to a minute.  `--build` sets the work folder (default `<design dir>/build`). It writes into `<design dir>/dist/` (or `--out`):

| File | Contents |
|---|---|
| `<name>.template` | The template file |
| `<name>-preview-sample.png` | L-Connect's renderer drawing the template with the sample values |
| `<name>-design-reference.png` | The HTML, for comparison |
| `<name>-background.png` | The flattened static layer |
| `<name>-preview.png` | The template as it looks before live data arrives (sensor placeholders, real clock) |
| `<name>-spec.json` | Every layer's sensor, font, size, colour and position |

It ends with `device render: OK`: the saved file went through L-Connect's own per-frame routine
(`scripts/device_render.ps1`). If that fails, the screen would stay blank (one bad layer blanks all);
it's reported as a PROBLEM. Never install a template that fails it.

It also prints `frame size: N KB of 1024 KB`. The device drops any frame whose PNG encoding exceeds 1 MB
(the service logs `send data out of limit` and the screen stays black), and it measures the frame rotated
to portrait as well, since the panel is natively portrait. Over the limit, or within ~15% of it, is a PROBLEM.
The usual cause is high-entropy background art: noise or grain textures, fine stripes, big diagonal gradients.
For a realistic, shaded look, use smooth vertical gradients, bevels, shadows and glass highlights; they're cheap.

Read every `PROBLEM` line it prints. Each one names the slot and the cause: font not installed for all
users, text-transform, glyph height mismatch, calibration not converging, and so on. `NOTE` lines are
smaller mismatches (e.g. dropped letter-spacing); fix them in the design when it's easy, so the
preview tells the truth.

### 3. Check it visually

Open `-preview-sample.png` and `-design-reference.png` and compare them. They should match apart from
known native limits: clock hands sit at 12 in the sample render (live on the device), and the browser only
approximates Lian Li sensor rings. If a value is in the wrong font, the font isn't resolving; if one is misplaced or
missing, look at `build/isolate/<layer>.png`. Fix the HTML (not the spec) and rebuild, so the design
stays the source of truth.

### 4. Install

With the user's go-ahead (it writes into L-Connect's ProgramData folder):

```
powershell -NoProfile -ExecutionPolicy Bypass -File SKILL/scripts/install.ps1 -Template <dist>\<name>.template
```

It refuses to overwrite an existing template unless given `-Force`. Then the user restarts L-Connect 3
and, in an Administrator PowerShell, runs `Restart-Service LConnectService`. Restarting the service needs
admin, so give them the command rather than running it. The template then appears in the 8.8" template list.

### 5. Report

Tell the user:
- where the template is, and that it's installed (or how to import it)
- which live widgets it has
- what differs from the design because of native limits
- what's verified (the preview rendered by L-Connect's own engine) and what isn't (it hasn't been seen
  running on their screen until they look)

## Fonts: the one thing that silently breaks templates

The screen is drawn by the L-Connect **service**, which runs as LocalSystem. A font installed only for
the current Windows user is invisible to it and gets drawn as Arial. Every position then drifts, because
it was calibrated on the real font, and the preview on the user's own account still looks perfect. The
build checks this and prints a PROBLEM line.

The fix belongs to the user, because it needs admin:
- In Explorer, right-click the .ttf and choose **Install for all users**; or copy it into
  `C:\Windows\Fonts` and register it under `HKLM\...\Fonts`.
- Then restart the service.

Fonts that ship with Windows (Bahnschrift, Segoe UI, Consolas, Impact…) avoid the issue entirely.
Bahnschrift is a good default for dashboards.

## When things go wrong

`references/internals.md` explains the .template format, how L-Connect renders text and resolves fonts,
and a symptom → fix table. Read it when a build fails or a widget won't line up. `references/widgets.md`
covers every engine widget, its fields and what was verified on a real screen. Video backgrounds aren't
generated yet (GIF/video overlays never draw on the 8.8" device).

Inspection helpers:
- `python -I SKILL/scripts/summary.py --compact <file.template>` lists every layer: class, sensor binding and
  position. Without `--compact` it dumps all fields; useful to learn how Lian Li built a stock template.
- `python -I SKILL/scripts/make_dial.py --size 300 --start -135 --sweep 270 --max 110 --red-from 90` prints an
  SVG of numbered ticks to use as static dial art behind a needle or arc slot.
- `powershell -File SKILL/scripts/render.ps1 <file.template> <out.png>` renders any template.
- `powershell -File SKILL/scripts/device_render.ps1 <file.template> <out.png>` runs L-Connect's exact
  per-frame device routine. It's the definitive "will it show anything on the screen" check.
