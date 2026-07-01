param(
    [string]$Ids,
    [int]$PrId = 0,
    [string]$StateFile = ""
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$baseUrl = Get-PrWebUrl -PrId $PrId

if ([string]::IsNullOrEmpty($StateFile)) {
    $StateFile = Get-StateFile -PrId $PrId
}

# IDs parsen (komma-separiert)
$threadIds = $Ids -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' }

if ($threadIds.Count -eq 0) {
    Write-Host "Keine Thread-IDs angegeben." -ForegroundColor Red
    Write-Host "Verwendung: open.ps1 -Ids '121074,121075,121076'"
    exit 1
}

# State laden um Pfade zu finden
$threadPaths = @{}
if (Test-Path $StateFile) {
    $state = Get-Content $StateFile -Raw | ConvertFrom-Json
    foreach ($group in $state.Groups) {
        foreach ($thread in $group.Threads) {
            $threadPaths[$thread.Id.ToString()] = $thread.File
        }
    }
}

Write-Host "Oeffne $($threadIds.Count) Thread(s) im Browser..." -ForegroundColor Cyan
Write-Host "  PR: $baseUrl" -ForegroundColor DarkGray

# Sammle alle URLs zuerst
$urls = @()
foreach ($id in $threadIds) {
    $filePath = $threadPaths[$id]

    if ($filePath) {
        $encodedPath = "/Sources/Backend/$filePath" -replace '/', '%2F'
        $url = "$baseUrl`?_a=files&discussionId=$id&path=$encodedPath"
    } else {
        $url = "$baseUrl`?_a=files&discussionId=$id"
    }

    $urls += $url
    Write-Host "  -> Thread $id" -ForegroundColor Gray
    if ($filePath) {
        Write-Host "     $filePath" -ForegroundColor DarkGray
    }
}

# Oeffne NEUES Chrome-Fenster mit erstem Tab, dann weitere Tabs hinzufuegen
$isFirst = $true
foreach ($url in $urls) {
    if ($isFirst) {
        Start-Process "chrome" -ArgumentList "--new-window", $url
        $isFirst = $false
        Start-Sleep -Milliseconds 1000
    } else {
        Start-Process "chrome" -ArgumentList $url
        Start-Sleep -Milliseconds 300
    }
}

Write-Host "Fertig!" -ForegroundColor Green
