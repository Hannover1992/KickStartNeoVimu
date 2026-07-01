param(
    [int]$PrId = 0,
    [int]$ThreadId,
    [switch]$Raw
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$headers = Get-AuthHeaders

$url = Get-ThreadApiUrl -PrId $PrId -ThreadId $ThreadId

$response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

if ($Raw) {
    $response.comments | ConvertTo-Json -Depth 5
    exit
}

Write-Host "============================================"
Write-Host " Thread $ThreadId"
Write-Host "============================================"
Write-Host ""

foreach ($comment in $response.comments) {
    $author = $comment.author.displayName
    $date = $comment.publishedDate
    $text = $comment.content

    Write-Host "--- $author ($date) ---" -ForegroundColor Cyan
    if ($text) {
        Write-Host $text
    } else {
        Write-Host "(Kein Text)" -ForegroundColor Yellow
    }
    Write-Host ""
}

if ($response.threadContext) {
    Write-Host "Datei: $($response.threadContext.filePath)" -ForegroundColor Gray
    Write-Host "Zeile: $($response.threadContext.rightFileStart.line)" -ForegroundColor Gray
}
