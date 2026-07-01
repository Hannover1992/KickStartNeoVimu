<#
.SYNOPSIS
    Holt ROHE PR-Kommentare von Azure DevOps - KEINE Gruppierung!
    Die Gruppierung macht Claude mit Ultrathink in /pr-planning.
.EXAMPLE
    .\fetch.ps1 20
#>
param(
    [Parameter(Position=0, Mandatory=$true)]
    [int]$PrId,
    [string]$MyTfsId = "ITSG\\Patryk.Krzyzanski"
)

. "$PSScriptRoot\_common.ps1"

$RawFile = Get-RawFile -PrId $PrId
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

# ============ ROHE DATEN EXTRAHIEREN (KEINE GRUPPIERUNG!) ============
$activeThreads = $threads.value | Where-Object {
    $_.status -eq 'active' -and $_.threadContext -ne $null
}

Write-Host "Aktive Code-Kommentare: $($activeThreads.Count)" -ForegroundColor Cyan

$myNamePart = ($MyTfsId -split '\\')[-1]

$rawComments = @()

foreach ($thread in $activeThreads) {
    $firstComment = $thread.comments[0]
    $lastComment = $thread.comments | Select-Object -Last 1

    $content = $firstComment.content -replace '@<[^>]+>', ''
    $content = $content.Trim()

    $line = if ($thread.threadContext.leftFileStart) {
        $thread.threadContext.leftFileStart.line
    } elseif ($thread.threadContext.rightFileStart) {
        $thread.threadContext.rightFileStart.line
    } else { 0 }

    $rawComments += @{
        ThreadId = $thread.id
        TfsStatus = $thread.status
        File = $thread.threadContext.filePath -replace '^/Sources/Backend/', ''
        Line = $line
        Author = $firstComment.author.displayName
        AuthorId = $firstComment.author.uniqueName
        Content = $content
        PublishedDate = $firstComment.publishedDate
        LastAuthor = $lastComment.author.displayName
        LastAuthorId = $lastComment.author.uniqueName
        LastUpdate = $lastComment.publishedDate
        IsMyResponse = $lastComment.author.uniqueName -match [regex]::Escape($myNamePart)
        CommentCount = $thread.comments.Count
    }
}

# Sortiere nach Datei und Zeile (fuer Claude's Analyse)
$rawComments = $rawComments | Sort-Object File, Line

$rawData = @{
    PrId = $PrId
    FetchedAt = (Get-Date).ToString("o")
    PrUrl = Get-PrWebUrl -PrId $PrId
    TotalComments = $rawComments.Count
    Config = @{
        MyTfsId = $MyTfsId
        MyNamePart = $myNamePart
    }
    Comments = $rawComments
}

$rawData | ConvertTo-Json -Depth 10 | Out-File $RawFile -Encoding UTF8

Write-Host ""
Write-Host "============================================" -ForegroundColor Magenta
Write-Host " ROHE DATEN GESPEICHERT" -ForegroundColor Magenta
Write-Host "============================================" -ForegroundColor Magenta
Write-Host "Datei: $RawFile" -ForegroundColor Green
Write-Host "Kommentare: $($rawComments.Count)" -ForegroundColor Cyan
Write-Host ""
Write-Host "Naechster Schritt: /pr-planning" -ForegroundColor Yellow
Write-Host "Claude analysiert die Daten und erstellt intelligente Gruppierung." -ForegroundColor DarkGray
