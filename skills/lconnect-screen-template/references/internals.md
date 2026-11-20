# How L-Connect 3 templates work (read when debugging)

## File format
- `*.template` is a .NET BinaryFormatter serialization of `ThemeEngine.Theme` from
  `C:\Program Files\Lian-Li\L-Connect 3\lianli.ThemeEngine.dll`. Older stock files name the
  assembly `lcd207, Version=1.2.0.52`; current ones `lianli.ThemeEngine, Version=1.2.0.61`.
- `Theme.GraphList` holds the layers, drawn in order:
  - `GraphImage`: `bitmap` (embedded PNG), `posX/posY`, `zoom_rate`.
  - `GraphItem` with `TypeName` `Data` (sensor) or `Text` (static, `DataName = StaticText`): `m_data` (an `M_Data`
    with `DataName`, `SubName`) and `fontConfig` (`name`, `size` in points, `isBold`, `color`,
    `interval` = per-char spacing, `alignment.index` 0/1/2).
  - `GraphStatuBar`: `width/height/radius`, `FrontColor/BackColor`, `useSubsection` + `SplitBlockWidth/SplitBlankWidth`.
  - `GraphArchBar` (arc gauge), `GraphLine` (chart), `GraphDynamicBar`, `GraphAnimation` (video).
- Theme-level: `width/height` 1920×480, `isLanscape`, `themePic` (thumbnail), `needFontList`, video paths.
- `scripts/build_template.ps1` builds all of this from L-Connect's own classes (`M_Data.GetDataFromList`,
  `GraphStatuBar(M_Data)`, …), seeded from a stock 1920×480 template so theme-level fields match
  what L-Connect writes. `Theme.Save` itself is just `BinaryFormatter.Serialize`.

## Rendering facts the calibration relies on
- Text: `Graphics.DrawString(Value, new Font(family, size_pt), brush, (posX,posY), StringFormat{Alignment=index})`.
  With right alignment, `posX` is the right anchor (GDI padding included, so anchors can sit a few px past the edge).
  Only `Value` is drawn, never a unit.
- `interval != 0` switches to per-character drawing, advancing by `MeasureString(char)` + interval. That's fine
  for digits and bad for `:` and `.`, which is why spacing is only applied to digit-only slots.
- Fonts: the `_font` field isn't serialized. On load, `FontConfig.LoadFont()` enumerates installed fonts and
  `Theme.LoadFont()` matches each layer's `name`. If there's no match, it uses L-Connect's bundled fonts, then Arial.
  The service runs as **LocalSystem**, so per-user fonts are invisible to it.
- CSS px → GDI pt is ×0.75. The exact position comes from comparing ink boxes: the browser
  reference minus the background, against each layer rendered alone by `GraphItem.Render`.

## Troubleshooting
| Symptom on the screen | Cause / fix |
|---|---|
| Numbers in Arial, layout drifts | Font not installed for all users → install for all users, `Restart-Service LConnectService` (admin) |
| Black screen, service log repeats `SDK Log: send data out of limit` | Frame over 1 MB. `lcd207 LEDController.UpdateLCD` resizes the frame to the panel, encodes it with GDI+ (PNG, or JPEG q95) and drops it above 1048576 bytes. Remove noise/grain textures, fine stripes and big diagonal gradients; the build's `frame size` line (worst of landscape/portrait PNG) must stay under 1024 KB |
| Template not in L-Connect's list | Restart L-Connect 3 and the service; or use L-Connect's own Import on the `dist` file |
| Values show `88` | No live data yet, or you're looking at the editor; normal |
| Network bars always full | L-Connect's bar max for network is 100 KB/s; use them as activity lights or drop them |
| `build_template.ps1` errors about a ReadOnly property | Use `Set-Field` (reflection) for that member; some have no public setter |
| Calibration doesn't converge | Overlapping slots, or a sample with characters the font lacks; check `build/isolate/<n>.png` |

Inspection: `python -I scripts/summary.py <file.template>` lists every layer (no L-Connect needed);
`powershell -File scripts/render.ps1 <file.template> out.png` renders it with L-Connect's engine.
