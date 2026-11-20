# Build a native L-Connect 3 .template (Universal Screen 8.8") from a JSON spec, using
# L-Connect's own ThemeEngine classes, and render a preview with L-Connect's own renderer.
#
#   powershell -File build_template.ps1 -Spec spec.json -Out My-Screen.template -Preview preview.png [-Sample]
#
# -Sample renders every widget with the fixed sample value from the spec (for calibration);
# the saved .template always keeps the live sensor bindings.
param([string]$Spec, [string]$Out, [string]$Preview, [switch]$Sample, [switch]$NoSave, [string]$IsolateDir, [switch]$AllowRenderErrors)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lconnect.ps1"
$T = { param($n) $asm.GetType("ThemeEngine.$n") }
$cfg = Get-Content $Spec -Raw -Encoding UTF8 | ConvertFrom-Json

function New-Color([string]$hex) {
    $h = $hex.TrimStart('#')
    if ($h.Length -eq 6) { $h = 'FF' + $h }
    return [System.Drawing.Color]::FromArgb([Convert]::ToInt32($h, 16))
}
function New-MData([string]$name, $sub) {
    $md = (& $T 'M_Data')::GetDataFromList($name, $(if ($sub) { [string]$sub } else { $null }))
    if (-not $md) { $md = [Activator]::CreateInstance((& $T 'M_Data'), @($name)) }
    $md.DataName = $name
    if ($sub) { $md.SubName = [string]$sub }
    $md.ShowUnit = $false
    return $md
}
function Set-Field($obj, [string]$name, $value) {
    # Sets a property, or its compiler backing field / plain field when no public setter exists.
    $bfl = [Reflection.BindingFlags]'Public,NonPublic,Instance'
    for ($t = $obj.GetType(); $t; $t = $t.BaseType) {
        $p = $t.GetProperty($name, $bfl)
        if ($p -and $p.CanWrite) { $p.SetValue($obj, $value, $null); return }
        foreach ($fn in @("<$name>k__BackingField", $name)) {
            $f = $t.GetField($fn, $bfl)
            if ($f) { $f.SetValue($obj, $value); return }
        }
    }
    throw "no member $name on $($obj.GetType().Name)"
}
function Get-MemberType($obj, [string]$name) {
    $bfl = [Reflection.BindingFlags]'Public,NonPublic,Instance'
    for ($t = $obj.GetType(); $t; $t = $t.BaseType) {
        $p = $t.GetProperty($name, $bfl); if ($p) { return $p.PropertyType }
        foreach ($fn in @("<$name>k__BackingField", $name)) { $f = $t.GetField($fn, $bfl); if ($f) { return $f.FieldType } }
    }
    throw "no member $name on $($obj.GetType().Name)"
}
function Get-FieldValue($obj, [string]$name) {
    $bfl = [Reflection.BindingFlags]'Public,NonPublic,Instance'
    for ($t = $obj.GetType(); $t; $t = $t.BaseType) {
        $p = $t.GetProperty($name, $bfl); if ($p -and $p.CanRead) { return $p.GetValue($obj, $null) }
        foreach ($fn in @("<$name>k__BackingField", $name)) { $f = $t.GetField($fn, $bfl); if ($f) { return $f.GetValue($obj) } }
    }
    throw "no member $name on $($obj.GetType().Name)"
}
function Convert-To([Type]$type, $v) {
    # JSON value -> the engine field's type (colours as #RRGGBB / #AARRGGBB, enums by name, Point as "x,y").
    if ($null -eq $v) { return $null }
    if ($type -eq [System.Drawing.Color]) { return New-Color ([string]$v) }
    if ($type.IsEnum) { return [Enum]::Parse($type, [string]$v, $true) }
    if ($type -eq [System.Drawing.Point]) { $p = ([string]$v).Split(','); return New-Object System.Drawing.Point([int]$p[0], [int]$p[1]) }
    if ($type -eq [bool]) { return [bool]$v }
    if ($type -eq [byte]) { return [byte]$v }
    if ($type -eq [int]) { return [int]$v }
    if ($type -eq [single]) { return [single]$v }
    if ($type -eq [double]) { return [double]$v }
    if ($type -eq [string]) { return [string]$v }
    return $v
}
function Set-Fields($obj, $fields) {
    if (-not $fields) { return }
    foreach ($p in $fields.PSObject.Properties) { Set-Field $obj $p.Name (Convert-To (Get-MemberType $obj $p.Name) $p.Value) }
}
function New-FontConfig($f) {
    # f: {font, size (pt), bold, italic, color, gradient (2nd colour), gradientDir, interval, align}
    $fc = New-Object -TypeName ((& $T 'FontConfig').AssemblyQualifiedName)
    Set-Field $fc 'name' ([string]$f.font); Set-Field $fc 'size' ([int]$f.size); Set-Field $fc 'orgSize' ([int]$f.size)
    Set-Field $fc 'isBold' ([bool]$f.bold); Set-Field $fc 'IsItalic' ([bool]$f.italic)
    Set-Field $fc 'interval' ([single]$f.interval)
    Set-Field $fc 'color' (New-Color $f.color)
    Set-Field $fc 'GrColor' (New-Color $(if ($f.gradient) { $f.gradient } else { $f.color }))
    Set-Field $fc 'GrDirection' ([int]$f.gradientDir)
    Set-Field $fc 'alignment' ([Activator]::CreateInstance((& $T 'TextAlignment'), @([int]$f.align)))
    return $fc
}
function Set-Images($it, [string]$path, $width) {
    # Embed an image the way L-Connect does: bitmap = as drawn, O_bitmap = original, zoom_rate = ratio.
    $src = Load-Bitmap $path
    $w = if ($width) { [int]$width } else { $src.Width }
    $h = [Math]::Max(1, [int][Math]::Round($w * $src.Height / [double]$src.Width))
    $scaled = New-Object System.Drawing.Bitmap($w, $h, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($scaled); $g.InterpolationMode = 'HighQualityBicubic'; $g.DrawImage($src, 0, 0, $w, $h); $g.Dispose()
    Set-Field $it 'bitmap' $scaled
    foreach ($n in 'O_bitmap', 'S_bitmap') { try { Set-Field $it $n $src } catch {} }
    try { Set-Field $it 'zoom_rate' ([double]$w / $src.Width) } catch {}
    try { Set-Field $it 'ImgName' ([IO.Path]::GetFileName($path)) } catch {}
    return @($w, $h)
}
function Load-Bitmap([string]$path) {
    # Copy into a fresh 32bpp bitmap so the file isn't locked and the format serialises cleanly.
    $img = [System.Drawing.Image]::FromFile($path)
    $bmp = New-Object System.Drawing.Bitmap($img.Width, $img.Height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp); $g.DrawImage($img, 0, 0, $img.Width, $img.Height); $g.Dispose(); $img.Dispose()
    return $bmp
}

# Start from a stock Lian Li 8.8" template so every theme-level field has the values L-Connect
# itself writes, then strip its layers and video so only our layers remain.
$bf = New-Object System.Runtime.Serialization.Formatters.Binary.BinaryFormatter
$fs = [IO.File]::OpenRead($cfg.seed)
try { $theme = $bf.Deserialize($fs) } finally { $fs.Close() }
if ($theme.width -ne [int]$cfg.width -or $theme.height -ne [int]$cfg.height) { throw 'seed template size mismatch' }
$theme.name = $cfg.name
$theme.isLanscape = $true
foreach ($f in 'videoPath', 'videoPath2', 'videoPath3', 'videoPathAlpha', 'o_videoPath', 'videoName', 'VideoPic', 'BgImg', 'ImgH264Bytes', 'Gid') { Set-Field $theme $f $null }
Set-Field $theme 'VideoDuration' 0; Set-Field $theme 'VideoFrameRate' 0
$items = $theme.GraphList
if ($null -eq $items) { throw 'Theme.GraphList is null' }
$items.Clear()
$fonts = New-Object 'System.Collections.Generic.List[string]'

foreach ($s in $cfg.items) {
    switch ($s.type) {
        'image' {
            $it = New-Object -TypeName ((& $T 'GraphImage').AssemblyQualifiedName)
            Set-Field $it 'bitmap' (Load-Bitmap $s.path)
            Set-Field $it 'ImgName' ([IO.Path]::GetFileName($s.path))
            Set-Field $it 'zoom_rate' (1.0)
        }
        'bar' {
            $md = New-MData $s.data $s.sub
            $it = [Activator]::CreateInstance((& $T 'GraphStatuBar'), @($md))
            Set-Field $it 'width' ([int]$s.w); Set-Field $it 'height' ([int]$s.h); Set-Field $it 'radius' ([int]$s.radius)
            Set-Field $it 'direction' (0)
            Set-Field $it 'FrontColor' (New-Color $s.front); Set-Field $it 'BackColor' (New-Color $s.back)
            Set-Field $it 'fillBack' ($true); Set-Field $it 'trBack' ($false); Set-Field $it 'useGradient' ($false)
            Set-Field $it 'useSubsection' ([bool]$s.block)
            if ($s.block) { Set-Field $it 'SplitBlockWidth' ([int]$s.block); Set-Field $it 'SplitBlankWidth' ([int]$s.blank)}
            if ($Sample) { $it.m_data.Value = [string]$s.sample }
        }
        'text' {
            $it = [Activator]::CreateInstance((& $T 'GraphItem'), @($(if ($s.data -eq 'StaticText') { 'Text' } else { 'Data' })))
            $it.SetMData((New-MData $s.data $s.sub))
            $fc = New-Object -TypeName ((& $T 'FontConfig').AssemblyQualifiedName)
            Set-Field $fc 'name' ($s.font); Set-Field $fc 'size' ([int]$s.size); Set-Field $fc 'orgSize' ([int]$s.size)
            Set-Field $fc 'isBold' ([bool]$s.bold); Set-Field $fc 'IsItalic' ([bool]$s.italic)
            Set-Field $fc 'interval' ([single]$s.interval)
            Set-Field $fc 'color' (New-Color $s.color)
            if ($s.gradient) {   # gradient text: item.useGradient + fontConfig GrColor/GrDirection (1..3)
                Set-Field $fc 'GrColor' (New-Color $s.gradient); Set-Field $fc 'GrDirection' ([int]$(if ($s.gradientDir) { $s.gradientDir } else { 1 }))
            } else { Set-Field $fc 'GrColor' (New-Color $s.color); Set-Field $fc 'GrDirection' (0) }
            Set-Field $fc 'alignment' ([Activator]::CreateInstance((& $T 'TextAlignment'), @([int]$s.align)))
            Set-Field $it 'fontConfig' ($fc)
            if ($s.gradient) { Set-Field $it 'useGradient' $true }
            if ($s.data -eq 'StaticText') { $it.m_data.Value = [string]$s.text; $it.m_data.content = [string]$s.text; Set-Field $it.m_data 'ValueWithUnit' ([string]$s.text) }
            elseif ($Sample) { $it.m_data.Value = [string]$s.sample }
            if (-not $fonts.Contains($s.font)) { $fonts.Add($s.font) }
        }
        'widget' {
            # Any ThemeEngine widget: {class, data, sub, fields{}, mdata{}, font{}, image, imageWidth,
            #   sensorStyle, sensorType, styleInfo{}, history[], sample}
            $cls = [string]$s.class
            if ($cls -eq 'GraphSensor') {
                $eng = & $T 'ThemeEngine'; try { [void]$eng.GetMethod('Init').Invoke($null, @()) } catch {}
                $si = New-Object -TypeName ((& $T 'Contr.StyleInfo').AssemblyQualifiedName)
                Set-Fields $si $s.styleInfo
                $st = [Enum]::Parse((& $T 'Contr.StyleTypes'), [string]$s.sensorStyle, $true)
                $sn = [Enum]::Parse((& $T 'Contr.SenSorTypes'), [string]$s.sensorType, $true)
                $ctor = (& $T 'GraphSensor').GetConstructors() | Where-Object { $_.GetParameters().Count -eq 3 } | Select-Object -First 1
                $it = $ctor.Invoke([object[]]@($st, $sn, $si.psobject.BaseObject))
                if ($it.styleInfo) { Set-Fields $it.styleInfo $s.styleInfo }
                Set-Field $it 'TypeName' 'Sensor'; Set-Field $it 'SubTypeName' ([string]$s.sensorStyle)
                $key = @{ CPULOAD = 'CPULOAD'; CPUTEMPERATURE = 'CPUTEMP'; CPUTEMPERATUREF = 'CPUTEMP_F'; GPULOAD = 'GPULOAD'
                          GPUTEMPERATURE = 'GPUTEMP'; GPUTEMPERATUREF = 'GPUTEMP_F'; FANRPM = 'CPUFAN' }[([string]$s.sensorType).ToUpper()]
                $md = New-MData $(if ($s.data) { $s.data } else { $key }) $s.sub
                Set-Field $it 'm_data' $md
            } else {
                $md = New-MData $(if ($s.data) { $s.data } else { 'StaticText' }) $s.sub
                $type = & $T $cls
                if (-not $type) { throw "unknown widget class $cls" }
                if ($cls -eq 'GraphItem') {
                    $it = [Activator]::CreateInstance($type, @($(if ($md.DataName -eq 'StaticText') { 'Text' } else { 'Data' })))
                    $it.SetMData($md)
                } else {
                    $it = [Activator]::CreateInstance($type, [object[]]@($md.psobject.BaseObject))
                }
                $tn = @{ GraphArchBar = 'ArchBar'; GraphLine = 'Chart'; GraphDynamicBar = 'DynamicBar'; GraphStatuBar = 'StatuBar'
                         GraphClock = 'Clock'; GraphImage = 'Image'; GraphAnimation = 'Animation' }[$cls]
                if ($tn) { Set-Field $it 'TypeName' $tn }
            }
            # Neutral defaults: the engine constructors switch on segments/blocks/gradients, so start every
            # flag from a known state and let the spec's fields override.
            $defaults = @{
                GraphStatuBar   = @{ direction = 0; useSubsection = $false; SplitBlockWidth = 0; SplitBlankWidth = 0; fillBack = $true; trBack = $false; useGradient = $false; radius = 0; lineWidth = 1 }
                GraphDynamicBar = @{ direction = 0; useSubsection = $false; SplitBlockWidth = 0; SplitBlankWidth = 0; fillBack = $true; trBack = $false; useGradient = $false; radius = 0; lineWidth = 1 }
                GraphArchBar    = @{ useBlock = $false; useGradient = $false; trBack = $false; fillBack = $false; round = $false; revert = $false; HasRingBorder = $false; SplitBlockWidth = 0; SplitBlankWidth = 0; startPer = 0; totalAngel = 360; lineWidth = 1 }
                GraphLine       = @{ rollDirection = $false; borderWidth = 0; lineWidth = 2; maxValue = [single]100 }
                GraphClock      = @{ angle = 0; endAngle = 360; revert = $false }
            }[$cls]
            if ($defaults) { foreach ($k in $defaults.Keys) { try { Set-Field $it $k (Convert-To (Get-MemberType $it $k) $defaults[$k]) } catch {} } }
            Set-Fields $it.m_data $s.mdata
            if ($s.font) { Set-Field $it 'fontConfig' (New-FontConfig $s.font); if (-not $fonts.Contains($s.font.font)) { $fonts.Add($s.font.font) } }
            if ($s.image) { [void](Set-Images $it $s.image $s.imageWidth) }
            try { Set-Field $it 'enabled' $true } catch {}
            Set-Fields $it $s.fields
            if ($cls -eq 'GraphLine' -and -not ($s.fields -and $s.fields.PSObject.Properties['coefficient'])) {
                # vertical scale = pixels per unit, so the max value reaches the top of the chart
                Set-Field $it 'coefficient' ([single]((Get-FieldValue $it '_height') / [Math]::Max(1.0, [double](Get-FieldValue $it 'maxValue'))))
            }
            if ($s.history) {
                $it.m_data.DataQueue.Clear()   # the queue starts with a stray "0" (drew a ramp from 0)
                foreach ($v in $s.history) { $it.m_data.Value = [string]$v }
            }
            if ($it.m_data.DataName -eq 'StaticText') {
                # Static text lives in Value + ValueWithUnit (what L-Connect and the community editor read back).
                $txt = if ($null -ne $s.sample) { [string]$s.sample } elseif ($s.mdata -and $s.mdata.content) { [string]$s.mdata.content } else { '' }
                $it.m_data.Value = $txt; Set-Field $it.m_data 'ValueWithUnit' $txt; Set-Field $it.m_data 'content' $txt
                if ($txt.Contains("`n") -and -not ($s.fields -and $s.fields.PSObject.Properties['LineHeight'])) {
                    Set-Field $it 'LineHeight' ([int][Math]::Ceiling([double]$s.font.size * 4 / 3 * 1.25))
                }
            }
            if ($Sample -and $null -ne $s.sample) { $it.m_data.Value = [string]$s.sample }
        }
    }
    if ($s.type -eq 'widget' -and $s.class -eq 'GraphClock') {
        # x,y = rotation centre for clocks/needles
        Set-Field $it 'centerX' ([int]$s.x); Set-Field $it 'centerY' ([int]$s.y)
        if (-not ($s.fields -and $s.fields.PSObject.Properties['posX'])) {
            Set-Field $it 'posX' (-[int]($it.bitmap.Width / 2)); Set-Field $it 'posY' (-[int]($it.bitmap.Height / 2))
        }
        if ($s.label) { Set-Field $it 'DisplayName' ($s.label) }
        $items.Add($it); continue
    }
    Set-Field $it 'posX' ([int]$s.x); Set-Field $it 'posY' ([int]$s.y)
    if ($s.label) { Set-Field $it 'DisplayName' ($s.label)}
    $items.Add($it)
}
Set-Field $theme 'needFontList' $fonts

# ---- render preview with L-Connect's own item renderers
function Render-Theme($theme, [string]$path, [bool]$sample) {
    $bmp = New-Object System.Drawing.Bitmap([int]$theme.width, [int]$theme.height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.Clear([System.Drawing.Color]::Black)
    $g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAlias'
    foreach ($it in $theme.GraphList) {
        $saved = $null
        if ($sample -and $it.m_data -and @('TIME', 'DATE', 'DAY') -contains $it.m_data.DataName) {
            $saved = $it.m_data.DataName; $it.m_data.DataName = 'StaticText'
        }
        if ($it.TypeName -ne 'Animation') {   # L-Connect's device loop skips Animation layers too
            try { $it.Render($g, $false, $false, $false) }
            catch { [void]$script:renderErrors.Add("layer $($theme.GraphList.IndexOf($it)) '$($it.DisplayName)' ($($it.GetType().Name)/$($it.TypeName)): $($_.Exception.InnerException.Message)$($_.Exception.Message)") }
        }
        if ($saved) { $it.m_data.DataName = $saved }
    }
    $g.Dispose()
    return $bmp
}
if ($Sample) {
    foreach ($idx in 0..($items.Count - 1)) {
        $s = $cfg.items[$idx]; $it = $items[$idx]
        if ($s.type -eq 'text' -and $s.data -ne 'StaticText') { $it.m_data.Value = [string]$s.sample }
    }
}
$asm.GetType('ThemeEngine.FontConfig').GetMethod('LoadFont').Invoke($null, @())
try { $theme.LoadFont() } catch { Write-Host "LoadFont: $($_.Exception.InnerException.Message)" }
foreach ($it in $items) {
    if ($it.fontConfig -and -not $it.fontConfig.font) { Write-Host "WARNING: font '$($it.fontConfig.name)' not resolved (not installed?)" }
}
if ($IsolateDir) {
    # One transparent PNG per layer (index-named), for per-widget calibration.
    New-Item -ItemType Directory -Force $IsolateDir | Out-Null
    for ($idx = 0; $idx -lt $items.Count; $idx++) {
        $it = $items[$idx]
        if ($cfg.items[$idx].type -eq 'image') { continue }
        $bmp = New-Object System.Drawing.Bitmap([int]$theme.width, [int]$theme.height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.Clear([System.Drawing.Color]::Transparent); $g.SmoothingMode = 'AntiAlias'; $g.TextRenderingHint = 'AntiAlias'
        $saved = $null
        if ($it.m_data -and @('TIME', 'DATE', 'DAY') -contains $it.m_data.DataName) { $saved = $it.m_data.DataName; $it.m_data.DataName = 'StaticText' }
        try { $it.Render($g, $false, $false, $false) } catch { Write-Host "render $idx : $($_.Exception.Message)" }
        if ($saved) { $it.m_data.DataName = $saved }
        $g.Dispose(); $bmp.Save((Join-Path $IsolateDir "$idx.png"), [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
    }
}
$script:renderErrors = New-Object System.Collections.ArrayList
$pv = Render-Theme $theme $Preview ([bool]$Sample)
foreach ($it in $items) {
    if ($it.TypeName -eq 'Animation') { Write-Host "WARNING: layer '$($it.DisplayName)' is an Animation layer. The 8.8in device loop never draws these as overlays (only the theme background video plays)." }
}
if ($script:renderErrors.Count) {
    # The device render loop (lcd207 LEDController.RenderItem) has no per-layer try/catch:
    # one throwing layer aborts every frame and the screen stays blank, with nothing logged.
    foreach ($e in $script:renderErrors) { Write-Host "FATAL: $e" }
    Write-Host "FATAL: a layer throws while rendering; on the screen this blanks the WHOLE template.$(if (-not $AllowRenderErrors) { ' Not saved.' })"
    if (-not $AllowRenderErrors) { exit 3 }
}
if ($Preview) { $pv.Save($Preview, [System.Drawing.Imaging.ImageFormat]::Png); Write-Host "preview -> $Preview" }

if (-not $NoSave) {
    # Saved file: live bindings, values reset to L-Connect defaults, preview thumbnail embedded.
    # (static text keeps its text: ResetValue would turn it into "0")
    foreach ($it in $items) { if ($it.m_data -and $it.m_data.DataName -ne 'StaticText') { try { $it.m_data.ResetValue() } catch {} } }
    # charts start empty on the device: drop the preview history from the saved file
    foreach ($it in $items) { if ($it.m_data -and $it.m_data.DataQueue) { $it.m_data.DataQueue.Clear() } }
    $theme.themePic = $pv
    $theme.themePath = $Out
    $bf = New-Object System.Runtime.Serialization.Formatters.Binary.BinaryFormatter
    $fs = [IO.File]::Create($Out)
    try { $bf.Serialize($fs, $theme) } finally { $fs.Close() }
    Write-Host "template -> $Out ($((Get-Item $Out).Length) bytes, $($items.Count) layers)"
}
