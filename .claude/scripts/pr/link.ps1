<#
.SYNOPSIS
    Zeigt Commit-URLs und oeffnet PR-Kommentare im Browser
.EXAMPLE
    .\link.ps1 -GroupNr 1
    .\link.ps1 1 -NoBrowser
#>
param(
    [Parameter(Position=0)]
    [int]$PrId = 0,
    [Parameter(Position=1)]
    [int]$GroupNr,
    [switch]$NoBrowser
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$StateFile = Get-StateFile -PrId $PrId

if (-not (Test-Path $StateFile)) {
    Write-Error "State-Datei nicht gefunden"
    exit 1
}

if ($GroupNr -eq 0) {
    Write-Error "Bitte Gruppen-Nummer angeben: .\link.ps1 1"
    exit 1
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

if (-not $group) {
    Write-Error "Gruppe $($GroupNr) nicht gefunden"
    exit 1
}

Write-Host "============================================" -ForegroundColor Magenta
Write-Host " Gruppe $($GroupNr) - Commit-Links" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""
Write-Host "Thema: $($group.Theme)" -ForegroundColor White
Write-Host "Thread-IDs: $(($group.Threads | ForEach-Object { $_.Id }) -join ', ')" -ForegroundColor DarkGray
Write-Host ""

if ($group.Commits.Count -eq 0) {
    Write-Host "Keine Commits fuer diese Gruppe vorhanden!" -ForegroundColor Red
    Write-Host "Nutze /pr-commit $($GroupNr) um einen Commit zu erstellen." -ForegroundColor Yellow
    exit 0
}

Write-Host "Commits ($($group.Commits.Count)):" -ForegroundColor Cyan
Write-Host ""

$commitLinks = @()

foreach ($commit in $group.Commits) {
    $hash = $commit.Hash
    if (-not $hash -or $hash.Length -lt 40) {
        $shortHash = if ($commit.ShortHash) { $commit.ShortHash } else { $hash }
        $fullHash = & git rev-parse $shortHash 2>$null
        if ($fullHash) { $hash = $fullHash }
    }

    $url = Get-CommitWebUrl -Hash $hash
    $commitLinks += $url

    Write-Host "  $($commit.ShortHash): $($commit.Message)" -ForegroundColor Green
    Write-Host "  $url" -ForegroundColor Cyan
    Write-Host ""
}

# Browser oeffnen
if (-not $NoBrowser -and $commitLinks.Count -gt 0) {
    Write-Host "Oeffne $($commitLinks.Count) Commit(s) im Browser..." -ForegroundColor Cyan
    $isFirst = $true
    foreach ($url in $commitLinks) {
        if ($isFirst) {
            Start-Process "chrome" -ArgumentList "--new-window", $url
            $isFirst = $false
            Start-Sleep -Milliseconds 1000
        } else {
            Start-Process "chrome" -ArgumentList $url
            Start-Sleep -Milliseconds 300
        }
    }
    Write-Host "1 Fenster mit $($commitLinks.Count) Tab(s) geoeffnet." -ForegroundColor Green
    Write-Host ""
}

# Markdown fuer PR-Antwort generieren
Write-Host "============================================" -ForegroundColor Magenta
Write-Host " Fertige PR-Antwort (Markdown)" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

$prResponse = "Umgesetzt in:`n"
foreach ($commit in $group.Commits) {
    $hash = $commit.Hash
    if (-not $hash -or $hash.Length -lt 40) {
        $shortHash = if ($commit.ShortHash) { $commit.ShortHash } else { $hash }
        $fullHash = & git rev-parse $shortHash 2>$null
        if ($fullHash) { $hash = $fullHash }
    }
    $url = Get-CommitWebUrl -Hash $hash
    $prResponse += "- [$($commit.ShortHash)]($url)`n"
}

Write-Host $prResponse -ForegroundColor Yellow
Write-Host ""

Write-Host "Status: $($group.Status) (keine automatische Aenderung)" -ForegroundColor DarkGray

# JSON Output
Write-Host ""
Write-Host "=== JSON ===" -ForegroundColor DarkGray
$output = @{
    groupNr = $GroupNr
    theme = $group.Theme
    status = $group.Status
    threadIds = ($group.Threads | ForEach-Object { $_.Id }) -join ","
    commits = $group.Commits | ForEach-Object {
        $hash = $_.Hash
        if (-not $hash -or $hash.Length -lt 40) {
            $shortHash = if ($_.ShortHash) { $_.ShortHash } else { $hash }
            $fullHash = & git rev-parse $shortHash 2>$null
            if ($fullHash) { $hash = $fullHash }
        }
        @{
            shortHash = $_.ShortHash
            message = $_.Message
            commitUrl = Get-CommitWebUrl -Hash $hash
        }
    }
    prResponseMarkdown = $prResponse
}
$output | ConvertTo-Json -Depth 5
