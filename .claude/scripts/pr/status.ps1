param(
    [int]$PrId = 0
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$stateFile = Get-StateFile -PrId $PrId

if (-not (Test-Path $stateFile)) {
    Write-Host "FEHLER: State-Datei nicht gefunden: $stateFile" -ForegroundColor Red
    Write-Host "Fuehre zuerst /pr-init aus."
    exit 1
}

$state = Get-Content $stateFile -Raw | ConvertFrom-Json
$myName = "Patryk Krzyzanski"

# Kategorisierung
$actionRequired = @()
$waitingForReview = @()
$completed = @()

foreach ($group in $state.Groups) {
    $myThreads = @($group.Threads | Where-Object { $_.LastAuthor -like "*$myName*" })
    $reviewerThreads = @($group.Threads | Where-Object { $_.LastAuthor -notlike "*$myName*" })

    $totalThreads = $group.Threads.Count
    $openCount = $reviewerThreads.Count

    $estimatedTime = if ($group.Planning.EstimatedTime) { $group.Planning.EstimatedTime } else { "?" }
    $complexity = if ($group.Planning.Complexity) { $group.Planning.Complexity } else { "-" }
    $summary = if ($group.Planning.Summary) { $group.Planning.Summary } else { "" }

    $groupInfo = [PSCustomObject]@{
        Nr = $group.Nr
        Theme = $group.Theme
        Pattern = $group.Pattern
        Status = $group.Status
        TotalThreads = $totalThreads
        OpenThreads = $openCount
        AnsweredThreads = $myThreads.Count
        ReviewerThreads = $reviewerThreads
        HasCommits = ($group.Commits.Count -gt 0)
        EstimatedTime = $estimatedTime
        Complexity = $complexity
        Summary = $summary
    }

    if ($group.Status -eq 'done' -and $openCount -eq 0) {
        $completed += $groupInfo
    }
    elseif ($openCount -gt 0) {
        $actionRequired += $groupInfo
    }
    elseif ($openCount -eq 0 -and $totalThreads -gt 0) {
        $waitingForReview += $groupInfo
    }
    else {
        $actionRequired += $groupInfo
    }
}

# Ausgabe
Write-Host ""
Write-Host "============================================" -ForegroundColor White
Write-Host " PR #$PrId - Uebersicht" -ForegroundColor White
Write-Host "============================================" -ForegroundColor White
Write-Host ""

$totalAction = ($actionRequired | Measure-Object -Property OpenThreads -Sum).Sum
$totalWaiting = ($waitingForReview | Measure-Object -Property TotalThreads -Sum).Sum
$totalDone = ($completed | Measure-Object -Property TotalThreads -Sum).Sum

Write-Host "  Aktion erforderlich:  $totalAction Threads in $($actionRequired.Count) Gruppen" -ForegroundColor Red
Write-Host "  Wartet auf Reviewer:  $totalWaiting Threads in $($waitingForReview.Count) Gruppen" -ForegroundColor Yellow
Write-Host "  Abgeschlossen:        $totalDone Threads in $($completed.Count) Gruppen" -ForegroundColor Green
Write-Host ""

if ($actionRequired.Count -gt 0) {
    Write-Host "----------------------------------------" -ForegroundColor Red
    Write-Host " AKTION ERFORDERLICH" -ForegroundColor Red
    Write-Host "----------------------------------------" -ForegroundColor Red

    $totalMinutes = 0
    foreach ($g in $actionRequired) {
        if ($g.EstimatedTime -match '(\d+)') {
            $totalMinutes += [int]$Matches[1]
        }
    }
    if ($totalMinutes -gt 0) {
        $hours = [math]::Floor($totalMinutes / 60)
        $mins = $totalMinutes % 60
        $timeStr = if ($hours -gt 0) { "${hours}h ${mins}min" } else { "${mins}min" }
        Write-Host "  Geschaetzter Aufwand: ~$timeStr" -ForegroundColor Magenta
    }
    Write-Host ""

    foreach ($g in $actionRequired | Sort-Object OpenThreads -Descending) {
        $theme = if ([string]::IsNullOrEmpty($g.Theme)) { "(KEIN THEME)" } else { $g.Theme }
        if ($theme.Length -gt 40) { $theme = $theme.Substring(0, 37) + "..." }

        $commitMark = if ($g.HasCommits) { "[C]" } else { "" }
        $timeMark = if ($g.EstimatedTime -ne "?") { "| $($g.EstimatedTime)" } else { "" }

        Write-Host "  Gruppe $($g.Nr): $theme" -ForegroundColor White -NoNewline
        Write-Host " $timeMark $commitMark" -ForegroundColor Cyan

        if ($g.Summary) {
            $summaryShort = if ($g.Summary.Length -gt 60) { $g.Summary.Substring(0, 57) + "..." } else { $g.Summary }
            Write-Host "    -> $summaryShort" -ForegroundColor DarkGray
        }

        foreach ($t in $g.ReviewerThreads) {
            $shortFile = Split-Path $t.File -Leaf
            Write-Host "    -> $shortFile`:$($t.Line)" -ForegroundColor Red
        }
    }
    Write-Host ""
}

if ($waitingForReview.Count -gt 0) {
    Write-Host "----------------------------------------" -ForegroundColor Yellow
    Write-Host " WARTET AUF REVIEWER" -ForegroundColor Yellow
    Write-Host "----------------------------------------" -ForegroundColor Yellow

    foreach ($g in $waitingForReview | Sort-Object TotalThreads -Descending) {
        $theme = if ([string]::IsNullOrEmpty($g.Theme)) { "(KEIN THEME)" } else { $g.Theme }
        if ($theme.Length -gt 50) { $theme = $theme.Substring(0, 47) + "..." }

        Write-Host "  Gruppe $($g.Nr): $($g.TotalThreads) Threads - $theme" -ForegroundColor Yellow
    }
    Write-Host ""
}

if ($completed.Count -gt 0) {
    Write-Host "----------------------------------------" -ForegroundColor Green
    Write-Host " ABGESCHLOSSEN" -ForegroundColor Green
    Write-Host "----------------------------------------" -ForegroundColor Green

    $completedNrs = ($completed | Sort-Object Nr | ForEach-Object { $_.Nr }) -join ", "
    $completedTotal = ($completed | Measure-Object -Property TotalThreads -Sum).Sum
    Write-Host "  Gruppen: $completedNrs ($completedTotal Threads)" -ForegroundColor Green
    Write-Host ""
}

Write-Host "============================================" -ForegroundColor White
if ($actionRequired.Count -gt 0) {
    $next = $actionRequired | Sort-Object OpenThreads -Descending | Select-Object -First 1
    Write-Host " Naechster Schritt: /pr-work $($next.Nr)" -ForegroundColor Cyan
} else {
    Write-Host " Alle Gruppen bearbeitet! Warte auf Reviewer." -ForegroundColor Green
}
Write-Host "============================================" -ForegroundColor White
Write-Host ""
