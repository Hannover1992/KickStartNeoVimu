param(
    [string]$FileFilter = "editorconfig",
    [int]$PrId = 0
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$headers = Get-AuthHeaders
$url = Get-ThreadsApiUrl -PrId $PrId

$response = Invoke-RestMethod -Uri $url -Headers $headers -Method Get

$response.value | Where-Object {
    $_.threadContext.filePath -like "*$FileFilter*"
} | ForEach-Object {
    Write-Host "Thread ID: $($_.id)"
    Write-Host "File: $($_.threadContext.filePath)"
    Write-Host "Status: $($_.status)"
    Write-Host "Comments: $($_.comments.Count)"
    if ($_.comments.Count -gt 0) {
        Write-Host "First comment: $($_.comments[0].content.Substring(0, [Math]::Min(100, $_.comments[0].content.Length)))..."
    }
    Write-Host "---"
}
