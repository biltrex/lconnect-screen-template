# L-Connect 3 sensor keys (Universal Screen 8.8")

Values come from the L-Connect service (`UniversalScreen8p8InchController.updateSensorValues`).
The text widget prints the bare value; it never adds the unit, so put units in static art.
"Bar max" is what a bar divides by (`M_Data.MaxVals`, default 100).

| Key | Shows | Sample / format | Unit (static) | Bar max |
|---|---|---|---|---|
| `CPUTEMP` / `GPUTEMP` | temperature | `58` | °C | 110 / 100 |
| `CPUTEMP_F` / `GPUTEMP_F` | temperature | `136` | °F | 230 |
| `CPULOAD` / `GPULOAD` | load | `23` | % | 100 |
| `CPUCLOCK` / `GPUCLOCK` | clock | `4800` | MHz | – |
| `CPUCLOCK_G` / `GPUCLOCK_G` | clock | `4.80` | GHz | – |
| `CPUPWR` / `GPUPWR` | power | `200` | W | – |
| `CPUFAN` / `GPUFAN` | fan | `1888` | RPM | – |
| `CPUVOLTAGE` / `GPUVOLTAGE` | voltage | `1.8` | V | – |
| `CPUMODEL` / `GPUMODEL` | model name | `I9 10900K` | – | – |
| `RAM_GB` | RAM used | `23.4` | GB | – |
| `RAMTOTAL_GB` / `RAMVALID_GB` | RAM total / free | `64.0` | GB | – |
| `RAM` / `RAMTOTAL` / `RAMVALID` | RAM used / total / free | `23960` | MB | – |
| `RAMLOAD` | RAM load | `37` | % | 100 |
| `GPURAM` | VRAM used | `6963` | MB | – |
| `GPURAMTOTAL` | VRAM total | `16303` | MB | – |
| `GPURAMLOAD` | VRAM load | `43` | % | 100 |
| `UPSPEED` / `DOWNSPEED` | network send / receive | `1434` | KB/s (never switches to MB/s) | 100 |
| `HDDTEMP` (`data-sub` = drive index, e.g. `1`) | drive temperature | `38` | °C | 110 |
| `DRVLOAD` (`data-sub` = drive letter, e.g. `C`) | drive used | `61` | % | 100 |
| `HDDUSED` | drive used | `61` | % | 100 |
| `WATERPUMP`, `CASEFAN1`, `CASEFAN2` | pump / fan | `2400` | RPM | – |
| `FPS` | frame rate (needs L-Connect's FPS monitoring; otherwise shows a placeholder such as 800) | `144` | FPS | – |
| `Volume` | system volume | `40` | % | 100 |

## Clock keys (need `data-sub`)

| Key | `data-sub` | Prints |
|---|---|---|
| `TIME` | `h:m:s` | `14:07:23` (24 h) |
| `TIME` | `h:m` | `14:07` |
| `TIME` | `h_24` / `h_12` / `m` / `s` | `14` / `02` / `07` / `23` |
| `APM` | – | `AM` / `PM` |
| `DATE` | `Y-M-D` | `2026-11-19` |
| `DATE` | `Y` / `M` / `D` | `2026` / `11` / `19` |
| `DATE` | `M_en` | `Nov` |
| `DAY` | `Day_en` | `Thu` |
| `DAY` | `Num` | `4` (0 = Sunday) |

Clock values are zero-padded: `TIME` parts and `DATE` `M`/`D` are always two digits (`03`, `09`), `Y` is four.

Other date orders (e.g. `11.19.2026`) are built from separate `M`, `D`, `Y` slots with static
separators between them. Use `data-align="center"` on 2-digit parts so width changes stay balanced.
For a 12-hour clock use `h_12`, a static `:`, `m`, and an `APM` slot.

Placeholders: before live data arrives, sensor values show placeholders (`0`, or `88`/`888` in
L-Connect's editor) while clock values already show the real time. That's normal.
