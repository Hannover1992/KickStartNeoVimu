<#
.SYNOPSIS
    Startet Arbeit an einer PR-Gruppe - trackt welche Gruppe aktiv ist
.EXAMPLE
    .\work.ps1 -GroupNr 1
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
    Write-Error "State-Datei nicht gefunden"
    exit 1
}

if ($GroupNr -eq 0) {
    Write-Error "Bitte Gruppen-Nummer angeben: .\work.ps1 1"
    exit 1
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

if (-not $group) {
    Write-Error "Gruppe $GroupNr nicht gefunden"
    exit 1
}

$lastCommitHash = git rev-parse HEAD 2>$null
$lastCommitShort = git rev-parse --short HEAD 2>$null

if (-not $state.ActiveWork) {
    $state | Add-Member -NotePropertyName "ActiveWork" -NotePropertyValue @{} -Force
}

$state.ActiveWork = @{
    GroupNr = $GroupNr
    StartedAt = (Get-Date).ToString("o")
    StartCommit = $lastCommitHash
    StartCommitShort = $lastCommitShort
}

$oldStatus = $group.Status
$group.Status = "in_progress"

$state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Arbeit gestartet: Gruppe $GroupNr" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Thema: $($group.Theme)" -ForegroundColor White
Write-Host "Status: $oldStatus -> in_progress" -ForegroundColor Yellow
Write-Host ""
Write-Host "Start-Commit: $lastCommitShort" -ForegroundColor DarkGray
Write-Host "Alle neuen Commits gehoeren zu Gruppe $GroupNr" -ForegroundColor Cyan
Write-Host ""
Write-Host "Wenn fertig: /pr-work-done" -ForegroundColor Yellow
Write-Host ""

$output = @{
    groupNr = $GroupNr
    theme = $group.Theme
    status = "in_progress"
    startCommit = $lastCommitShort
    startedAt = $state.ActiveWork.StartedAt
}
$output | ConvertTo-Json
