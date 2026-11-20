# Lists the font families GDI can see, split by who can see them.
#   machine : installed for all users -> visible to the L-Connect service (runs as LocalSystem)
#   user    : installed for the current user only -> NOT visible to the service (renders as Arial)
# Output: JSON {"machine": [...], "user": [...]}
Add-Type -AssemblyName System.Drawing
$all = (New-Object System.Drawing.Text.InstalledFontCollection).Families | ForEach-Object { $_.Name }
$userFamilies = @()
$key = 'HKCU:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
if (Test-Path $key) {
    $pfc = New-Object System.Drawing.Text.PrivateFontCollection
    (Get-ItemProperty $key).PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object {
        $f = [string]$_.Value
        if (-not [IO.Path]::IsPathRooted($f)) { $f = Join-Path "$env:LOCALAPPDATA\Microsoft\Windows\Fonts" $f }
        if (Test-Path $f) { try { $pfc.AddFontFile($f) } catch {} }
    }
    $userFamilies = $pfc.Families | ForEach-Object { $_.Name }
}
# A family that also exists in C:\Windows\Fonts is machine-visible even if a user copy exists.
$machineFiles = New-Object System.Drawing.Text.PrivateFontCollection
$hk = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts'
$machineNames = @{}
foreach ($fam in $userFamilies) { $machineNames[$fam] = $false }
if ($userFamilies.Count) {
    (Get-ItemProperty $hk).PSObject.Properties | Where-Object { $_.Name -notmatch '^PS' } | ForEach-Object {
        $n = $_.Name
        foreach ($fam in $userFamilies) {
            if ($n -like "$($fam.Split(' ')[0])*") {
                $f = [string]$_.Value
                if (-not [IO.Path]::IsPathRooted($f)) { $f = Join-Path "$env:WINDIR\Fonts" $f }
                if (Test-Path $f) { try { $machineFiles.AddFontFile($f) } catch {} }
            }
        }
    }
    foreach ($fam in $machineFiles.Families) { $machineNames[$fam.Name] = $true }
}
$userOnly = @($userFamilies | Where-Object { -not $machineNames[$_] } | Sort-Object -Unique)
$machine = @($all | Where-Object { $userOnly -notcontains $_ } | Sort-Object -Unique)
[pscustomobject]@{ machine = $machine; user = $userOnly } | ConvertTo-Json -Compress
