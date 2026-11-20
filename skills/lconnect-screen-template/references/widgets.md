# L-Connect 3 widget reference (Universal Screen 8.8")

Every layer type the ThemeEngine can draw, with the fields that matter and what they actually do.
"Verified" means rendered with L-Connect's own `GraphItem.Render` (tools: `scripts/build_template.ps1`,
spec items of `"type": "widget"`). On-device status is tracked in the project's Widget-Test checklist.

Sources: the engine itself (`lianli.ThemeEngine.dll` reflection), Lian Li's 34 official presets in
`C:\ProgramData\Lian-Li\L-Connect 3\universal-screen-8.8-inch\modulars\Landscape\*.modular`, the community
LianliThemeEditor (ozgurce) source, and 186 community templates.

## Device status (2026-11-20, Widget-Test on a real Universal Screen 8.8")
Verified live on the screen: text (bold, italic, gradient, multi-line static, model names, clock/date/day/APM),
bars (all four directions, segmented, gradient, outline, rounded), slider (DynamicBar), arcs (donut, 270-degree blocks,
gradient, pie + border, half), charts (history builds on the device), needle and analog clock (GraphClock),
image layers, and sensor styles Ring1–Ring5. `FPS` showed 800, a placeholder until L-Connect's FPS monitoring has
data, so warn users. Not usable: GIF/Animation overlays (skipped by the device loop) and sensor styles
SENSOR_6/SENSOR_7/Pic (they crash the frame).

## The device render rule (read first)
The 8.8" screen is drawn every frame by `lcd207.LEDController.RenderItem`, which renders layers in order with
**no per-layer error handling**. If any one layer throws, the whole frame is dropped: the screen stays blank and
nothing is logged (the service log still says "Template applied"). So:
- `scripts/build_template.ps1` refuses to save when any layer throws (override: `-AllowRenderErrors`).
- `scripts/make_template.py` finishes by running `scripts/device_render.ps1`, which calls that exact device routine on
  the saved file. Run it yourself on any template: `powershell -File device_render.ps1 <file.template> <out.png>`.
- `RenderItem` **skips layers whose TypeName is `Animation`**, so GIF/video layers never draw as overlays.

## Building any widget

A spec item `{"type":"widget","class":"<Graph…>", "x":…, "y":…, "data":"<sensor key>", "sub":"<format>",
"fields":{…}, "mdata":{…}, "font":{…}, "image":"path", "imageWidth":N, "sample":"…", "history":[…]}`:
- `fields` sets any engine field by name. Colours are `#RRGGBB` / `#AARRGGBB`, enums by name, `Point` as "x,y".
- `mdata` sets fields of the widget's `M_Data` (e.g. `queueLen`, `content`).
- `font` builds a `FontConfig`: `{font, size (pt), bold, italic, color, gradient, gradientDir, interval, align}`.
- The builder applies neutral defaults first, because the engine constructors switch on segments, blocks
  and gradients by default: bars → solid with the track filled; arcs → solid with the track shown, no gradient.

## Text: `GraphItem` (TypeName `Data` / `Text`)
- Draws `m_data.Value` with `DrawString` at (posX, posY); `fontConfig.alignment.index` 0/1/2 = left/centre/right anchor.
- `fontConfig.size` is in points (×4/3 = px). `isBold`, `IsItalic` both work.
- **Gradient text**: set the item's `useGradient=true`, `fontConfig.color` = start, `GrColor` = end,
  `GrDirection` 1/2/3 = gradient directions; 0 = solid. Verified.
- `interval` = per-character spacing, but it uses per-character drawing (bad with `:` and `.`; fine for digits).
- **Multi-line static text**: put `\r\n` in the value/content and set `LineHeight` (px). Without it, lines overlap.
- `m_data.ShowUnit` has no visible effect (Render draws `Value` only). Put units in static art or a static text layer.
- Static text: `data: "StaticText"`, with the text in `Value` **and** `ValueWithUnit` (and `content`). Never call
  `ResetValue()` on static text before saving: it turns the text into "0" (verified on the device routine).

## Bar: `GraphStatuBar` (TypeName `StatuBar`)
| Field | Effect (verified) |
|---|---|
| `width`, `height` | box size. **For direction 2/3, `width` is the bar's length (vertical) and `height` its thickness.** |
| `direction` | 0 fills left→right, 1 right→left, 2 top→down, 3 bottom→up |
| `FrontColor` / `BackColor` | fill / track colour; `FrontAlpha`/`BackAlpha` 0 = opaque, else alpha |
| `fillBack` | true = solid track; false = track drawn as an outline `lineWidth` px thick (in BackColor) |
| `trBack` | true = transparent track (none drawn) |
| `radius` | rounds the track and fill ends (pill bars: radius = height/2) |
| `useSubsection` + `SplitBlockWidth`/`SplitBlankWidth` | segmented bar (lit + unlit blocks) |
| `useGradient` + `GradientColor` | horizontal gradient from FrontColor to GradientColor |
Value scale: `m_data.Rate` = value ÷ max (100 default; temperature keys 110; network 100 KB/s).

## Slider: `GraphDynamicBar` (TypeName `DynamicBar`)
A `GraphStatuBar` with a round knob at the value position. `InnerCircleRadius` = knob diameter. Usually
a thin bar (height 8–12) with a matching `radius`. Segments work too. Verified.

## Arc / ring / pie: `GraphArchBar` (TypeName `ArchBar`)
| Field | Effect (verified) |
|---|---|
| `posX,posY` | top-left of the ring's **centre-line** circle (measured); the outer box starts `archWidth/2` further up-left; outer size = `diameter + archWidth` |
| `diameter` | diameter of the ring's centre line |
| `archWidth` | stroke thickness. `archWidth = diameter` gives a full pie |
| `startPer` | where the arc starts, as % of a full turn clockwise from 12 o'clock (50 = 6 o'clock; 62 = 7:30 for a gauge open at the bottom) |
| `totalAngel` | sweep in degrees at 100 % (360 ring, 270 gauge, 180 half) |
| `trBack` | **false = track drawn** in BackColor; true = no track |
| `round` | rounded stroke ends |
| `useBlock` + `SplitBlockWidth`/`SplitBlankWidth` | segmented arc |
| `useGradient` (base GraphItem) + `GradientColor` | colour blends along the sweep |
| `HasRingBorder` + `lineWidth` | thin outline rings in BackColor |
| `revert` | sweep counter-clockwise |
| `fillBack` | no visible effect |

## History chart: `GraphLine` (TypeName `Chart`)
| Field | Effect (verified) |
|---|---|
| `_height` | chart height; `coefficient` = px per unit (the builder sets `_height / maxValue`) |
| `columnWidth` | px between samples. **Drawn width = `columnWidth × m_data.queueLen`** (`_width` doesn't constrain it) |
| `m_data.queueLen` | number of samples kept. The queue (`DataQueue`) is serialised: clear it before saving or the device shows stale samples; a fresh M_Data starts with a stray `0` |
| `LineColor`, `lineWidth` | the line |
| `FillColor` | area under the line. **Drawn much stronger than its alpha** (measured, independent of step: alpha 0.125 shows as 0.39, 0.25 as 0.54, 0.5 as 0.74), so the builder converts the intended opacity. `#00000000` = none |
| `BorderColor`, `borderWidth` | frame around the chart (0 = none) |
| `rollDirection` | true = newest sample anchored at the right edge |
| `maxValue` | value at the top (100 default) |

## Needle / clock hand: `GraphClock` (TypeName `Clock`)
A `GraphImage` that rotates about (`centerX`, `centerY`). In the spec, `x,y` is the rotation centre,
and the builder centres the image on it (posX/posY = −w/2, −h/2). Draw needle images pointing **up**,
with the pivot at the image centre.
- Angle = `angle + rate × endAngle` (degrees clockwise from 12 o'clock). **`endAngle` is the sweep, not
  the end.** A 270° gauge is `angle -135, endAngle 270`. `revert` mirrors the direction.
- Sensor needles: any key (rate = value ÷ max).
- Analog clock: `data TIME`, `sub` `h_12` (hour), `h_24`, `m`, `s`, with `angle 0, endAngle 360`, one layer per hand.

## Image: `GraphImage` (TypeName `Image`)
`bitmap` = the image as drawn, `O_bitmap` = original, `zoom_rate` = drawn ÷ original width; `ImgName`.
Draw order = layer order. The design's flattened background is one of these.

## Animation: `GraphAnimation` (TypeName `Animation`)
**Not drawn as an overlay on the 8.8" device**: `RenderItem` skips it. Animation only plays as the theme's background
video (`Theme.videoPath` / H.264 via `PlayH264`), which is how video templates work. This background-video path is
still to be explored. What follows describes the layer itself:
A GIF / MP4 / MOV / H.264 layer. `FilePath` must point at the media file. Keep the media in L-Connect's
`…\universal-screen-8.8-inch\video\` folder, copied there at install time. `videoName`, `direction`,
`zoom_rate`, `ration`. The first frame is embedded as `bitmap` for previews. Full-screen video
backgrounds are this same class at 0,0 (most community templates use one).

## Lian Li sensor styles: `GraphSensor` (TypeName `Sensor`)
Prebuilt gauge widgets: `styleType` `Ring1`–`Ring5` (verified on the device routine). **`SENSOR_6`, `SENSOR_7` and `Pic` crash**
(`KeyNotFoundException` in `DrawStyle.GetFontShapeInfos`: the engine has no layout for them), which blanks the whole
screen. Never use them (`video` is untested) × `senSorType` (`CPULoad`, `CPUTemperature`, `CPUTemperatureF`,
`GPULoad`, `GPUTemperature`, `GPUTemperatureF`, `FanRPM`). Colours and font come from `styleInfo`
(`Color1`, `Color2` = arc gradient, `BgColor` = track, `MainFontColor`, `FontTopColor`, `FontBottomColor`,
`FontFamily`). Size comes from `ZoomRate` (0.5 ≈ 190 px; 0.3 ≈ 115 px). They draw their own labels
("CPU", "LOAD"). Good for quick, polished gauges; less flexible than ArchBar + text.

## Theme-level options (untested)
`RenderMode` D3 (3D text caches), `ThemeList` (nested modular themes), `AnimationSetting`
(Circular/Rotate/Bounce/Collision), `_SplitType` (dual/triple). Not used by templates built so far.

## Fonts
The service runs as LocalSystem and resolves fonts by family name from the machine-wide font list,
then L-Connect's few built-in fonts, then Arial. L-Connect never loads fonts from its own folder.
Install fonts for all users. The community editor does the same: it copies to `C:\Windows\Fonts` and adds an HKLM registry entry.
