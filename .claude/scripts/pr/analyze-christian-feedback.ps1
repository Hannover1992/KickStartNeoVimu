<#
.SYNOPSIS
    Analysiert Christian Hoffmanns Feedback ueber mehrere PRs hinweg.
.EXAMPLE
    .\analyze-christian-feedback.ps1 -PrIds 18979,19060,18212
#>
param(
    [Parameter(Mandatory=$false)]
    [string]$PrIdsFile = "",
    [Parameter(Mandatory=$false)]
    [int[]]$PrIds,
    [string]$ReviewerName = "Christian Hoffmann"
)

. "$PSScriptRoot\_common.ps1"

if ([string]::IsNullOrEmpty($PrIdsFile)) {
    $PrIdsFile = Join-Path $script:StateDir "my-prs.json"
}

# Wenn keine PrIds angegeben, aus File lesen
if ($PrIds.Count -eq 0 -and (Test-Path $PrIdsFile)) {
    Write-Host "Lese PR-IDs aus $PrIdsFile..." -ForegroundColor Cyan
    $prData = Get-Content $PrIdsFile | ConvertFrom-Json
    $PrIds = $prData | Select-Object -ExpandProperty PrId
    Write-Host "  Gefunden: $($PrIds.Count) PRs" -ForegroundColor Green
}

$headers = Get-AuthHeaders

# ============ ALLE KOMMENTARE SAMMELN ============
$allComments = @()

foreach ($prId in $PrIds) {
    Write-Host "Hole Threads von PR #$prId..." -ForegroundColor Cyan

    $threadsUrl = Get-ThreadsApiUrl -PrId $prId

    try {
        $threads = Invoke-RestMethod -Uri $threadsUrl -Headers $headers

        foreach ($thread in $threads.value) {
            if ($thread.threadContext -eq $null) { continue }

            foreach ($comment in $thread.comments) {
                if ($comment.author.displayName -ne $ReviewerName) { continue }

                $content = $comment.content -replace '@<[^>]+>', ''
                $content = $content.Trim()

                if ([string]::IsNullOrWhiteSpace($content)) { continue }

                $line = if ($thread.threadContext.leftFileStart) {
                    $thread.threadContext.leftFileStart.line
                } elseif ($thread.threadContext.rightFileStart) {
                    $thread.threadContext.rightFileStart.line
                } else { 0 }

                $allComments += [PSCustomObject]@{
                    PrId = $prId
                    ThreadId = $thread.id
                    ThreadStatus = $thread.status
                    File = $thread.threadContext.filePath -replace '^/Sources/Backend/', ''
                    Line = $line
                    Content = $content
                    PublishedDate = $comment.publishedDate
                    CommentId = $comment.id
                }
            }
        }

        Write-Host "  Threads: $($threads.value.Count), Christian-Kommentare: $(($allComments | Where-Object { $_.PrId -eq $prId }).Count)" -ForegroundColor Green
    }
    catch {
        Write-Error "Fehler bei PR #${prId}: $_"
    }
}

# ============ PATTERN-ANALYSE ============
Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host " CHRISTIAN HOFFMANN FEEDBACK-ANALYSE" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host ""

Write-Host "Gesamt Kommentare: $($allComments.Count)" -ForegroundColor Cyan
Write-Host "PRs analysiert: $($PrIds.Count)" -ForegroundColor Cyan
Write-Host ""

$keywords = @{}
foreach ($comment in $allComments) {
    $words = $comment.Content -split '\s+' | Where-Object { $_.Length -gt 4 }
    foreach ($word in $words) {
        $word = $word.ToLower() -replace '[^a-zaeoeueess]', ''
        if ($word.Length -gt 4) {
            if (-not $keywords.ContainsKey($word)) {
                $keywords[$word] = 0
            }
            $keywords[$word]++
        }
    }
}

Write-Host "TOP 20 KEYWORDS:" -ForegroundColor Yellow
$keywords.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 20 | ForEach-Object {
    Write-Host "  $($_.Key): $($_.Value)" -ForegroundColor Gray
}

Write-Host ""

Write-Host "TOP 10 DATEIEN MIT MEISTEN KOMMENTAREN:" -ForegroundColor Yellow
$allComments | Group-Object File | Sort-Object Count -Descending | Select-Object -First 10 | ForEach-Object {
    Write-Host "  [$($_.Count)x] $($_.Name)" -ForegroundColor Gray
}

Write-Host ""

Write-Host "STATUS-VERTEILUNG:" -ForegroundColor Yellow
$allComments | Group-Object ThreadStatus | ForEach-Object {
    Write-Host "  $($_.Name): $($_.Count)" -ForegroundColor Gray
}

Write-Host ""

# ============ EXPORT ============
$outputFile = Join-Path $script:StateDir "christian-feedback-analysis.json"
$reportFile = Join-Path $script:StateDir "christian-feedback-report.md"

$allComments | ConvertTo-Json -Depth 5 | Out-File $outputFile -Encoding UTF8

$report = @"
# Christian Hoffmann - Feedback-Analyse

**PRs analysiert:** $($PrIds.Count)
**Gesamt Kommentare:** $($allComments.Count)

---

## Top 20 Keywords

$($keywords.GetEnumerator() | Sort-Object -Property Value -Descending | Select-Object -First 20 | ForEach-Object { "- **$($_.Key)**: $($_.Value)x" } | Out-String)

---

## Top 10 Dateien mit meisten Kommentaren

$($allComments | Group-Object File | Sort-Object Count -Descending | Select-Object -First 10 | ForEach-Object { "- **$($_.Name)**: $($_.Count)x" } | Out-String)

---

## Status-Verteilung

$($allComments | Group-Object ThreadStatus | ForEach-Object { "- **$($_.Name)**: $($_.Count)x" } | Out-String)
"@

$report | Out-File $reportFile -Encoding UTF8

Write-Host "Gespeichert:" -ForegroundColor Green
Write-Host "  JSON: $outputFile" -ForegroundColor Gray
Write-Host "  Report: $reportFile" -ForegroundColor Gray
