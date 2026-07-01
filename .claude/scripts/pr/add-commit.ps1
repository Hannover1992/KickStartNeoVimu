<#
.SYNOPSIS
    Weist einen existierenden Commit einer PR-Gruppe zu (manuelle Pflege)
.EXAMPLE
    .\add-commit.ps1 -GroupNr 1 -CommitHash "abc123"
#>
param(
    [Parameter(Position=0)]
    [int]$PrId = 0,
    [Parameter(Position=1)]
    [int]$GroupNr,
    [Parameter(Position=2)]
    [string]$CommitHash
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$StateFile = Get-StateFile -PrId $PrId

if (-not (Test-Path $StateFile)) {
    Write-Error "State-Datei nicht gefunden"
    exit 1
}

if ($GroupNr -eq 0 -or -not $CommitHash) {
    Write-Error "Verwendung: .\add-commit.ps1 <GroupNr> <CommitHash>"
    exit 1
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

if (-not $group) {
    Write-Error "Gruppe $GroupNr nicht gefunden"
    exit 1
}

$fullHash = git rev-parse $CommitHash 2>$null
if (-not $fullHash) {
    Write-Error "Commit $CommitHash nicht gefunden"
    exit 1
}

$shortHash = git rev-parse --short $CommitHash
$message = git log -1 --format="%s" $CommitHash

$existing = $group.Commits | Where-Object { $_.Hash -eq $fullHash -or $_.ShortHash -eq $shortHash }
if ($existing) {
    Write-Host "Commit $shortHash ist bereits Gruppe $GroupNr zugewiesen" -ForegroundColor Yellow
    exit 0
}

$newCommit = @{
    Hash = $fullHash
    ShortHash = $shortHash
    Message = $message
    Date = (git log -1 --format="%aI" $CommitHash)
}

if ($group.Commits -eq $null) {
    $group.Commits = @($newCommit)
}
else {
    $group.Commits = @($group.Commits) + $newCommit
}

$state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8

Write-Host ""
Write-Host "Commit zugewiesen:" -ForegroundColor Green
Write-Host "  Gruppe: $GroupNr" -ForegroundColor Cyan
Write-Host "  Commit: $shortHash - $message" -ForegroundColor White
Write-Host "  Commits in Gruppe: $($group.Commits.Count)" -ForegroundColor DarkGray
Write-Host ""

$output = @{
    groupNr = $GroupNr
    commit = $newCommit
    totalCommits = $group.Commits.Count
}
$output | ConvertTo-Json -Depth 3
