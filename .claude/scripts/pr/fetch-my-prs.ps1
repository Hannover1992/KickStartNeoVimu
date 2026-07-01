<#
.SYNOPSIS
    Holt die letzten N Pull-Requests des Users von Azure DevOps.
.EXAMPLE
    .\fetch-my-prs.ps1 -Top 15
    .\fetch-my-prs.ps1 -Top 15 -FetchComments
#>
param(
    [int]$Top = 15,
    [string]$MyTfsId = "ITSG\Patryk.Krzyzanski",
    [switch]$FetchComments
)

. "$PSScriptRoot\_common.ps1"

$headers = Get-AuthHeaders

# ============ PULL REQUESTS ABRUFEN ============
Write-Host "Hole abgeschlossene PRs und filtere auf $MyTfsId..." -ForegroundColor Cyan

$prUrl = Get-PullRequestsApiUrl -Top 150

try {
    $allPrs = Invoke-RestMethod -Uri $prUrl -Headers $headers
    Write-Host "Gesamt PRs geladen: $($allPrs.count)" -ForegroundColor Green

    $myNamePart = ($MyTfsId -split '\\')[-1]
    $prs = @{
        count = 0
        value = $allPrs.value | Where-Object {
            $_.createdBy.uniqueName -match [regex]::Escape($myNamePart)
        } | Select-Object -First $Top
    }
    $prs.count = $prs.value.Count

    Write-Host "Deine PRs (gefiltert): $($prs.count)" -ForegroundColor Yellow
}
catch {
    Write-Error "Fehler beim Abrufen der PRs: $_"
    exit 1
}

# ============ PR-LISTE AUSGEBEN ============
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host " DEINE LETZTEN $($prs.count) PULL-REQUESTS" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

$prList = @()

foreach ($pr in $prs.value) {
    $prInfo = @{
        PrId = $pr.pullRequestId
        Title = $pr.title
        CreatedDate = $pr.creationDate
        ClosedDate = $pr.closedDate
        Status = $pr.status
        SourceBranch = $pr.sourceRefName -replace 'refs/heads/', ''
        TargetBranch = $pr.targetRefName -replace 'refs/heads/', ''
        Url = Get-PrWebUrl -PrId $pr.pullRequestId
    }

    $prList += $prInfo

    Write-Host "PR #$($pr.pullRequestId)" -ForegroundColor Yellow
    Write-Host "  Titel: $($pr.title)" -ForegroundColor Gray
    Write-Host "  Erstellt: $($pr.creationDate)" -ForegroundColor DarkGray
    Write-Host "  Status: $($pr.status)" -ForegroundColor $(if ($pr.status -eq 'completed') { 'Green' } else { 'Yellow' })
    Write-Host ""
}

# ============ OPTIONAL: KOMMENTARE HOLEN ============
if ($FetchComments) {
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host " HOLE KOMMENTARE (fetch.ps1)" -ForegroundColor Magenta
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host ""

    $fetchScript = Join-Path $PSScriptRoot "fetch.ps1"

    foreach ($pr in $prs.value) {
        Write-Host "Fetching PR #$($pr.pullRequestId)..." -ForegroundColor Cyan
        & $fetchScript -PrId $pr.pullRequestId -MyTfsId $MyTfsId
        Write-Host ""
    }
}

# ============ PR-LISTE ALS JSON SPEICHERN ============
$outputFile = Join-Path $script:StateDir "my-prs.json"
$prList | ConvertTo-Json -Depth 5 | Out-File $outputFile -Encoding UTF8

Write-Host "PR-Liste gespeichert: $outputFile" -ForegroundColor Green
