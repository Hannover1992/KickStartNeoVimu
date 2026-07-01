<#
.SYNOPSIS
    Oeffnet alle Kommentare einer PR-Gruppe im Browser
.EXAMPLE
    .\findings.ps1 -GroupNr 1
#>
param(
    [Parameter(Position=0)]
    [int]$PrId = 0,
    [Parameter(Position=1)]
    [int]$GroupNr
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$StateFile = Get-StateFile -PrId $PrId

if (-not (Test-Path $StateFile)) {
    Write-Error "State-Datei nicht gefunden. Erst /pr-init ausfuehren"
    exit 1
}

if ($GroupNr -eq 0) {
    Write-Error "Bitte Gruppen-Nummer angeben: .\findings.ps1 1"
    exit 1
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

if (-not $group) {
    Write-Error "Gruppe $GroupNr nicht gefunden"
    exit 1
}

$threadIds = ($group.Threads | ForEach-Object { $_.Id }) -join ","

Write-Host ""
Write-Host "Gruppe $($GroupNr): $($group.Theme)" -ForegroundColor Magenta
Write-Host "Oeffne $($group.Threads.Count) Kommentar(e)..." -ForegroundColor Cyan
Write-Host ""

# open.ps1 aufrufen
$openScript = Join-Path $PSScriptRoot "open.ps1"
& $openScript -Ids $threadIds -PrId $PrId

# Status auf in_progress setzen falls pending
if ($group.Status -eq "pending") {
    $group.Status = "in_progress"
    $state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8
    Write-Host ""
    Write-Host "Status: pending -> in_progress" -ForegroundColor Yellow
}
