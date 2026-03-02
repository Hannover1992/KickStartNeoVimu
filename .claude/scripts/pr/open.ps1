<#
.SYNOPSIS
    Oeffnet einen oder mehrere PR-Kommentare im Browser

.EXAMPLE
    .\open.ps1 -Ids 121074
    .\open.ps1 -Ids 121074,121075,121076
    .\open.ps1 -Ids "121074, 121075, 121076"
#>
param(
    [Parameter(Mandatory=$true)]
    [string]$Ids,
    [int]$PrId = 18979,
    [int]$DelayMs = 500
)

$BaseUrl = "https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_git/DCSRE/pullrequest/$PrId"
$JsonFile = "C:\Users\Administrator\Documents\Work\Code2\DCSRE\Sources\Backend\pr-$PrId-comments.json"

# IDs parsen (kommasepariert, mit oder ohne Leerzeichen)
$idList = $Ids -split '[,\s]+' | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ }

if ($idList.Count -eq 0) {
    Write-Error "Keine gueltigen IDs angegeben"
    exit 1
}

Write-Host "Oeffne $($idList.Count) Kommentar(e) im Browser..." -ForegroundColor Cyan
Write-Host ""

# JSON laden fuer Datei-Pfade
$threads = @{}
if (Test-Path $JsonFile) {
    $json = Get-Content $JsonFile -Raw -Encoding UTF8 | ConvertFrom-Json
    foreach ($thread in $json.value) {
        if ($thread.threadContext) {
            $threads[$thread.id] = $thread.threadContext.filePath
        }
    }
}

# Jeden Kommentar oeffnen
foreach ($id in $idList) {
    $filePath = $threads[$id]

    if ($filePath) {
        $url = "$BaseUrl`?_a=files&path=$filePath&discussionId=$id"
        Write-Host "  [$id] $filePath" -ForegroundColor Green
    } else {
        # Fallback ohne Pfad
        $url = "$BaseUrl`?_a=files&discussionId=$id"
        Write-Host "  [$id] (Pfad unbekannt)" -ForegroundColor Yellow
    }

    # Neues Fenster mit Chrome (--new-window)
    Start-Process "chrome" -ArgumentList "--new-window", $url

    # Kurze Pause zwischen Tabs damit Browser nicht ueberlastet
    if ($idList.Count -gt 1) {
        Start-Sleep -Milliseconds $DelayMs
    }
}

Write-Host ""
Write-Host "Fertig! $($idList.Count) Fenster geoeffnet." -ForegroundColor Green
