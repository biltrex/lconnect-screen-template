# Render an L-Connect 3 .template to PNG using L-Connect's own ThemeEngine.
# Usage: powershell -File render.ps1 <template> <out.png> [background.png]
param([string]$Template, [string]$Out, [string]$Background)
$ErrorActionPreference = 'Stop'
$dir = "C:\Program Files\Lian-Li\L-Connect 3"
. "$PSScriptRoot\lconnect.ps1"
$engT = $asm.GetType('ThemeEngine.ThemeEngine')
try { $eng = [Activator]::CreateInstance($engT, $true); [void]$engT.GetMethod('Init').Invoke($eng, @()) } catch { Write-Host "engine init: $($_.Exception.InnerException.Message)" }

$bf = New-Object System.Runtime.Serialization.Formatters.Binary.BinaryFormatter
$fs = [IO.File]::OpenRead($Template)
try { $theme = $bf.Deserialize($fs) } finally { $fs.Close() }
$asm.GetType('ThemeEngine.FontConfig').GetMethod('LoadFont').Invoke($null, @())
try { $theme.LoadFont() } catch { Write-Host "LoadFont: $($_.Exception.InnerException.Message)" }
$W = $theme.width; $H = $theme.height
$bmp = New-Object System.Drawing.Bitmap($W, $H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.Clear([System.Drawing.Color]::Black)
$g.TextRenderingHint = 'AntiAliasGridFit'
$g.SmoothingMode = 'AntiAlias'
if ($Background) { $bg = [System.Drawing.Image]::FromFile($Background); $g.DrawImage($bg, 0, 0, $W, $H) }
elseif ($theme.themePic) { }
$i = 0
foreach ($it in $theme.GraphList) {
    try {
        if ($it.m_data) { try { $it.m_data.ResetValue() } catch {} }
        $it.Render($g, $false, $false, $false)
    } catch { Write-Host "item $i ($($it.TypeName)): $($_.Exception.Message)" }
    $i++
}
$g.Dispose()
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
Write-Host "rendered $i items -> $Out ($W x $H)"
