# Copy a built .template into L-Connect 3's Universal Screen 8.8" template folder.
#   powershell -File install.ps1 -Template <file.template> [-Force]
# Never overwrites an existing template unless -Force is given. Restarting the L-Connect service
# needs admin rights, so this script only tells you to do it.
param([Parameter(Mandatory)][string]$Template, [switch]$Force)
$ErrorActionPreference = 'Stop'
$dest = 'C:\ProgramData\Lian-Li\L-Connect 3\universal-screen-8.8-inch\template'
if (-not (Test-Path $dest)) { throw "L-Connect 8.8in template folder not found: $dest" }
$target = Join-Path $dest ([IO.Path]::GetFileName($Template))
if ((Test-Path $target) -and -not $Force) { throw "Already exists: $target  (re-run with -Force to replace it)" }
Copy-Item -LiteralPath $Template -Destination $target -Force:$Force
Write-Host "installed -> $target"
Write-Host 'Next: restart L-Connect 3, and in an Administrator PowerShell run: Restart-Service LConnectService'
