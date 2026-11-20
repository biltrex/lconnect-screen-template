# Shared loader for L-Connect 3 assemblies (dot-source this).
$dir = "C:\Program Files\Lian-Li\L-Connect 3"
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName WindowsBase
# Pre-load every assembly we may need, then resolve by simple name from the loaded set
# (avoids re-entrant LoadFrom inside the resolve handler).
$global:LCAsm = @{}
foreach ($f in 'lianli.ThemeEngine.dll', 'lianli.lcd207.dll', 'Newtonsoft.Json.dll', 'SkiaSharp.dll') {
    $p = Join-Path $dir $f
    if (Test-Path $p) {
        try { $a = [Reflection.Assembly]::LoadFrom($p); $global:LCAsm[$a.GetName().Name] = $a } catch {}
    }
}
$global:LCAsm['lcd207'] = $global:LCAsm['lianli.lcd207']
$global:LCAsm['ThemeEngine'] = $global:LCAsm['lianli.ThemeEngine']
[AppDomain]::CurrentDomain.add_AssemblyResolve([ResolveEventHandler] {
    param($s, $e)
    $n = $e.Name.Split(',')[0]
    if ($global:LCAsm.ContainsKey($n)) { return $global:LCAsm[$n] }
    return $null
})
$asm = $global:LCAsm['lianli.ThemeEngine']
