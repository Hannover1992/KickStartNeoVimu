<#
.SYNOPSIS
    Synchronisiert PR-State mit Azure DevOps - holt aktuellen Thread-Status
.EXAMPLE
    .\sync.ps1
    .\sync.ps1 -PrId 20 -Init
#>
param(
    [Parameter(Position=0)]
    [int]$PrId = 0,
    [switch]$Init,
    [string]$MyTfsId = "ITSG\\Patryk.Krzyzanski"
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$StateFile = Get-StateFile -PrId $PrId
$headers = Get-AuthHeaders

# ============ THREADS ABRUFEN ============
Write-Host "Hole Threads von PR #$PrId..." -ForegroundColor Cyan
$threadsUrl = Get-ThreadsApiUrl -PrId $PrId

try {
    $threads = Invoke-RestMethod -Uri $threadsUrl -Headers $headers
    Write-Host "Threads geladen: $($threads.value.Count)" -ForegroundColor Green
}
catch {
    Write-Error "Fehler beim Abrufen der Threads: $_"
    exit 1
}

# ============ INIT: NEUE STATE-DATEI ============
if ($Init -or -not (Test-Path $StateFile)) {
    Write-Host "Erstelle neue State-Datei..." -ForegroundColor Yellow

    $activeThreads = $threads.value | Where-Object {
        $_.status -eq 'active' -and $_.threadContext -ne $null
    }

    Write-Host "Aktive Code-Kommentare: $($activeThreads.Count)" -ForegroundColor Cyan

    $groups = @{}

    foreach ($thread in $activeThreads) {
        $firstComment = $thread.comments[0]
        $content = $firstComment.content -replace '@<[^>]+>', ''
        $content = $content.Trim()

        $key = if ($content.Length -gt 80) {
            $content.Substring(0, 80) -replace '\s+\S*$', '...'
        } else {
            $content
        }

        if (-not $groups.ContainsKey($key)) {
            $groups[$key] = @{
                Pattern = $key
                FullComment = $content
                Author = $firstComment.author.displayName
                Threads = @()
            }
        }

        $line = if ($thread.threadContext.leftFileStart) {
            $thread.threadContext.leftFileStart.line
        } elseif ($thread.threadContext.rightFileStart) {
            $thread.threadContext.rightFileStart.line
        } else { 0 }

        $lastComment = $thread.comments | Select-Object -Last 1
        $myNamePart = ($MyTfsId -split '\\')[-1]
        $isMyResponse = $lastComment.author.uniqueName -match [regex]::Escape($myNamePart)

        $groups[$key].Threads += @{
            Id = $thread.id
            TfsStatus = $thread.status
            File = $thread.threadContext.filePath -replace '^/Sources/Backend/', ''
            Line = $line
            LastAuthor = $lastComment.author.displayName
            LastAuthorId = $lastComment.author.uniqueName
            LastUpdate = $lastComment.publishedDate
            IsMyResponse = $isMyResponse
        }
    }

    $groupNr = 1
    $stateGroups = @()

    foreach ($group in ($groups.Values | Sort-Object { -$_.Threads.Count })) {
        $stateGroups += @{
            Nr = $groupNr
            Status = "pending"
            Theme = ($group.FullComment -replace '[\r\n]', ' ').Substring(0, [Math]::Min(60, $group.FullComment.Length))
            Pattern = $group.FullComment
            Author = $group.Author
            Commits = @()
            Threads = $group.Threads
            Notes = ""
        }
        $groupNr++
    }

    # Branch aus active-pr.json oder Fallback
    $branch = ""
    if (Test-Path $script:ActivePrFile) {
        $activePr = Get-Content $script:ActivePrFile -Raw | ConvertFrom-Json
        $branch = $activePr.branch
    }

    $state = @{
        PrId = $PrId
        Branch = $branch
        CreatedAt = (Get-Date).ToString("o")
        LastSync = (Get-Date).ToString("o")
        TotalComments = $activeThreads.Count
        PrUrl = Get-PrWebUrl -PrId $PrId
        Groups = $stateGroups
        Config = @{
            MyTfsId = $MyTfsId
            BranchName = $branch
        }
    }

    $state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8
    Write-Host "State-Datei erstellt: $StateFile" -ForegroundColor Green
    Write-Host "Gruppen: $($stateGroups.Count)" -ForegroundColor Cyan
}
# ============ UPDATE: BESTEHENDE STATE-DATEI ============
else {
    Write-Host "Aktualisiere bestehende State-Datei..." -ForegroundColor Yellow
    $state = Get-Content $StateFile -Raw | ConvertFrom-Json

    $updatedCount = 0
    $statusChanges = @()

    foreach ($group in $state.Groups) {
        foreach ($thread in $group.Threads) {
            $tfsThread = $threads.value | Where-Object { $_.id -eq $thread.Id }
            if ($tfsThread) {
                $oldStatus = $thread.TfsStatus
                $thread.TfsStatus = $tfsThread.status

                if ($oldStatus -ne $tfsThread.status) {
                    $statusChanges += "Thread $($thread.Id): $oldStatus -> $($tfsThread.status)"
                }

                $lastComment = $tfsThread.comments | Select-Object -Last 1
                $thread.LastAuthor = $lastComment.author.displayName
                $thread.LastAuthorId = $lastComment.author.uniqueName
                $thread.LastUpdate = $lastComment.publishedDate

                $myNamePart = ($state.Config.MyTfsId -split '\\')[-1]
                $thread.IsMyResponse = $lastComment.author.uniqueName -match [regex]::Escape($myNamePart)

                $updatedCount++
            }
        }

        $allFixed = ($group.Threads | Where-Object { $_.TfsStatus -eq 'fixed' }).Count -eq $group.Threads.Count
        $allClosed = ($group.Threads | Where-Object { $_.TfsStatus -in @('fixed', 'closed') }).Count -eq $group.Threads.Count
        $hasCommits = $group.Commits.Count -gt 0

        if ($allFixed -or $allClosed) {
            if ($group.Status -ne "done") {
                $statusChanges += "[HINWEIS] Gruppe $($group.Nr): Alle Threads fixed/closed - evtl. auf 'done' setzen?"
            }
        }
        elseif ($hasCommits -and $group.Status -eq "pending") {
            $statusChanges += "[HINWEIS] Gruppe $($group.Nr): Hat Commits aber Status 'pending' - evtl. auf 'waiting' setzen?"
        }
    }

    $state.LastSync = (Get-Date).ToString("o")
    $state | ConvertTo-Json -Depth 10 | Out-File $StateFile -Encoding UTF8

    Write-Host "Aktualisiert: $updatedCount Threads" -ForegroundColor Green

    if ($statusChanges.Count -gt 0) {
        Write-Host ""
        Write-Host "Hinweise:" -ForegroundColor Yellow
        foreach ($change in $statusChanges) {
            Write-Host "  $change" -ForegroundColor Cyan
        }
    }

    # Antwort-Status pro Gruppe
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host " Antwort-Status pro Gruppe" -ForegroundColor Magenta
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host ""

    foreach ($group in $state.Groups | Sort-Object Nr) {
        $total = @($group.Threads).Count
        $answered = @($group.Threads | Where-Object { $_.IsMyResponse -eq $true }).Count

        if ($answered -gt 0) {
            $pct = [math]::Round(($answered / $total) * 100)
            if ($answered -eq $total) {
                Write-Host "  [OK] Gruppe $($group.Nr): $answered/$total beantwortet (100%) - WAITING" -ForegroundColor Green
            } else {
                Write-Host "  [>>] Gruppe $($group.Nr): $answered/$total beantwortet ($pct%)" -ForegroundColor Yellow
            }
        } elseif ($group.Status -eq "done") {
            Write-Host "  [+] Gruppe $($group.Nr): done" -ForegroundColor Green
        } else {
            Write-Host "  [ ] Gruppe $($group.Nr): 0/$total beantwortet" -ForegroundColor DarkGray
        }
    }

    # GESAMT-FORTSCHRITT
    Write-Host ""
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host " GESAMT-FORTSCHRITT" -ForegroundColor Magenta
    Write-Host "============================================" -ForegroundColor Magenta
    Write-Host ""

    $totalThreads = ($state.Groups | ForEach-Object { @($_.Threads).Count } | Measure-Object -Sum).Sum
    $answeredThreads = ($state.Groups | ForEach-Object { @($_.Threads | Where-Object { $_.IsMyResponse -eq $true }).Count } | Measure-Object -Sum).Sum
    $doneGroups = ($state.Groups | Where-Object { $_.Status -eq "done" }).Count
    $totalGroups = $state.Groups.Count

    $threadPct = if ($totalThreads -gt 0) { [math]::Round(($answeredThreads / $totalThreads) * 100) } else { 0 }

    $filledBlocks = [math]::Floor($threadPct / 5)
    $emptyBlocks = 20 - $filledBlocks
    $progressBar = ("=" * $filledBlocks) + ("-" * $emptyBlocks)

    Write-Host "  Threads beantwortet: $answeredThreads/$totalThreads ($threadPct%)" -ForegroundColor Cyan
    Write-Host "  Gruppen erledigt:    $doneGroups/$totalGroups" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  $progressBar $threadPct%" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Sync abgeschlossen!" -ForegroundColor Green
Write-Host "State-Datei: $StateFile" -ForegroundColor DarkGray
