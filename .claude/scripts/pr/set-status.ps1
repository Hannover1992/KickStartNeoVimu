<#
.SYNOPSIS
    Setzt den Status einer PR-Gruppe manuell
.EXAMPLE
    .\set-status.ps1 -GroupNr 1 -Status done
#>
param(
    [Parameter(Position=0)]
    [int]$PrId = 0,
    [Parameter(Position=1)]
    [int]$GroupNr,
    [Parameter(Position=2)]
    [ValidateSet("pending", "in_progress", "done", "waiting", "wontfix")]
    [string]$Status
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$StateFile = Get-StateFile -PrId $PrId

if (-not (Test-Path $StateFile)) {
    Write-Error "State-Datei nicht gefunden"
    exit 1
}

if ($GroupNr -eq 0 -or -not $Status) {
    Write-Error "Verwendung: .\set-status.ps1 <GroupNr> <Status>"
    Write-Host "Status-Optionen: pending, in_progress, done, waiting, wontfix" -ForegroundColor Yellow
    exit 1
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

if (-not $group) {
    Write-Error "Gruppe $GroupNr nicht gefunden"
    exit 1
}

$oldStatus = $group.Status
$group.Status = $Status

$state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8

Write-Host "Gruppe $($GroupNr): $($oldStatus) -> $($Status)" -ForegroundColor Green
