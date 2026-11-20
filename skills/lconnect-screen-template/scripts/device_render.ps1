# Render a .template through L-Connect's own 8.8" device routine (lcd207 LEDController.RenderItem),
# the exact code that draws each frame for the screen. If it throws here, the screen shows nothing.
#   powershell -File device_render.ps1 <file.template> <out.png>
param([string]$Template, [string]$Out)
$ErrorActionPreference = 'Stop'
. "$PSScriptRoot\lconnect.ps1"
try { [void]$asm.GetType('ThemeEngine.ThemeEngine').GetMethod('Init').Invoke($null, @()) } catch {}
$bf = New-Object System.Runtime.Serialization.Formatters.Binary.BinaryFormatter
$fs = [IO.File]::OpenRead($Template)
try { $theme = $bf.Deserialize($fs) } finally { $fs.Close() }
$asm.GetType('ThemeEngine.FontConfig').GetMethod('LoadFont').Invoke($null, @())
try { $theme.LoadFont() } catch {}
$bmp = New-Object System.Drawing.Bitmap([int]$theme.width, [int]$theme.height, [System.Drawing.Imaging.PixelFormat]::Format32bppArgb)
$g = [System.Drawing.Graphics]::FromImage($bmp); $g.Clear([System.Drawing.Color]::Black)
$render = $global:LCAsm['lianli.lcd207'].GetType('lcd207.LEDController').GetMethod('RenderItem', [Reflection.BindingFlags]'NonPublic,Public,Static')
$ok = $true
try { [void]$render.Invoke($null, [object[]]@($theme, $g, $true)) }
catch {
    $ok = $false
    $e = $_.Exception; while ($e.InnerException) { $e = $e.InnerException }
    Write-Host "DEVICE RENDER FAILED: $($e.GetType().Name): $($e.Message)"
    Write-Host ($e.StackTrace -split "`n" | Select-Object -First 4 | Out-String)
}
$g.Dispose(); $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
if (-not $ok) { exit 4 }
Write-Host "device render OK -> $Out"

# Frame size gate. LEDController.UpdateLCD encodes every frame with GDI+ (PNG, or JPEG q95) and drops any frame
# over 1048576 bytes ("SDK Log: send data out of limit" in the service log): the screen stays black.
# The panel is natively portrait, so measure the rotated frame too and keep the larger (it matched the device).
function Get-PngBytes($b) { $ms = New-Object IO.MemoryStream; $b.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png); $ms.Length }
$land = Get-PngBytes $bmp
$rot = $bmp.Clone(); $rot.RotateFlip([System.Drawing.RotateFlipType]::Rotate90FlipNone)
$port = Get-PngBytes $rot; $rot.Dispose()
$worst = [Math]::Max($land, $port)
Write-Host ("FRAME bytes={0} landscape={1} portrait={2} limit=1048576" -f $worst, $land, $port)
if ($worst -gt 1048576) {
    Write-Host ("FRAME TOO LARGE: {0:N0} KB as PNG (limit 1024 KB). The device drops every frame and shows black." -f ($worst / 1KB))
    exit 5
}
