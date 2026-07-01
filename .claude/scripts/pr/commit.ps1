<#
.SYNOPSIS
    Erstellt Commit und verknuepft ihn mit einer PR-Gruppe in der State-Datei
.EXAMPLE
    .\commit.ps1 -GroupNr 1 -Message "TestBase<T> in allen Tests verwendet"
#>
param(
    [Parameter(Position=0)]
    [int]$PrId = 0,
    [Parameter(Position=1)]
    [int]$GroupNr,
    [Parameter(Position=2)]
    [string]$Message
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$StateFile = Get-StateFile -PrId $PrId

if (-not (Test-Path $StateFile)) {
    Write-Error "State-Datei nicht gefunden: $StateFile"
    exit 1
}

if ($GroupNr -eq 0) {
    Write-Error "Bitte Gruppen-Nummer angeben"
    exit 1
}

$state = Get-Content $StateFile -Raw | ConvertFrom-Json
$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

if (-not $group) {
    Write-Error "Gruppe $GroupNr nicht gefunden"
    exit 1
}

# Pruefe auf staged changes
$gitStatus = git status --porcelain
if (-not $gitStatus) {
    Write-Error "Keine Aenderungen zum Committen. Erst 'git add' ausfuehren."
    exit 1
}

# Message generieren falls nicht angegeben
if (-not $Message) {
    $Message = $group.Theme
}

# Ticket-Prefix aus Branch extrahieren
$branch = ""
if (Test-Path $script:ActivePrFile) {
    $activePr = Get-Content $script:ActivePrFile -Raw | ConvertFrom-Json
    $branch = $activePr.branch
}
$ticketId = if ($branch -match '(DCSRE-\d+)') { $Matches[1] } else { "DCSRE" }
$fullMessage = "${ticketId}: $Message"

Write-Host ""
Write-Host "Commit fuer Gruppe $GroupNr" -ForegroundColor Magenta
Write-Host ""
Write-Host "Message: $fullMessage" -ForegroundColor Cyan
Write-Host ""
Write-Host "Staged Aenderungen:" -ForegroundColor White
git status --short
Write-Host ""

# Commit ausfuehren
Write-Host "Erstelle Commit..." -ForegroundColor Yellow
$commitOutput = git commit -m "$fullMessage`n`nPR #$PrId Gruppe $GroupNr`nThread-IDs: $(($group.Threads | ForEach-Object { $_.Id }) -join ', ')`n`nGenerated with Claude Code" 2>&1

if ($LASTEXITCODE -eq 0) {
    $hash = git rev-parse HEAD
    $shortHash = git rev-parse --short HEAD

    Write-Host "Commit erfolgreich: $shortHash" -ForegroundColor Green
    Write-Host ""

    $newCommit = @{
        Hash = $hash
        ShortHash = $shortHash
        Message = $fullMessage
        Date = (Get-Date).ToString("o")
    }

    if ($group.Commits -eq $null) {
        $group.Commits = @($newCommit)
    }
    else {
        $group.Commits = @($group.Commits) + $newCommit
    }

    $oldStatus = $group.Status
    $group.Status = "done"

    $state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8

    Write-Host "State aktualisiert:" -ForegroundColor Green
    Write-Host "  Gruppe $GroupNr: $oldStatus -> done" -ForegroundColor Cyan
    Write-Host ""

    $commitUrl = Get-CommitWebUrl -Hash $hash -Branch $branch

    Write-Host "Commit-URL (fuer PR-Antwort):" -ForegroundColor Yellow
    Write-Host $commitUrl -ForegroundColor Cyan
    Write-Host ""

    # JSON-Output
    $output = @{
        success = $true
        hash = $hash
        shortHash = $shortHash
        message = $fullMessage
        groupNr = $GroupNr
        commitUrl = $commitUrl
        threadIds = ($group.Threads | ForEach-Object { $_.Id }) -join ","
    }
    Write-Host "=== JSON ===" -ForegroundColor DarkGray
    $output | ConvertTo-Json
}
else {
    Write-Error "Commit fehlgeschlagen:"
    Write-Host $commitOutput -ForegroundColor Red
    exit 1
}
