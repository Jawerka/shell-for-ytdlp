# Opens AV false-positive submission pages and prints build hashes.
# Run after: .\scripts\build-windows.ps1
# Fill template: scripts\windows\av-false-positive-submission.txt

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$dist = Join-Path $root 'dist'
$exe = Join-Path $dist 'UI-for-ytdlp\UI-for-ytdlp.exe'
$setup = Get-ChildItem -Path $dist -Filter 'UI-for-ytdlp-*-windows-x64-setup.exe' |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 1

if (-not (Test-Path $exe)) {
    throw "Build not found: $exe"
}

Write-Host 'UI-for-ytdlp false positive submission helpers' -ForegroundColor Cyan
Write-Host ''
Write-Host "SHA256 (exe):  $((Get-FileHash $exe -Algorithm SHA256).Hash)"
if ($setup) {
    Write-Host "SHA256 (setup): $((Get-FileHash $setup.FullName -Algorithm SHA256).Hash)"
    Write-Host "Setup file:     $($setup.FullName)"
}
Write-Host ''
Write-Host "Template: $(Join-Path $PSScriptRoot 'windows\av-false-positive-submission.txt')"
Write-Host ''
Write-Host 'Opening Microsoft Defender submission...'
Start-Process 'https://www.microsoft.com/en-us/wdsi/filesubmission'
Write-Host 'Upload setup.exe (preferred) or zip. Use template text for description.'
Write-Host ''
Write-Host 'VirusTotal: upload setup or exe, then Request re-analysis on the report page.'
