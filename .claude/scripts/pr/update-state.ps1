param(
    [int]$PrId = 0,
    [int]$GroupNr,
    [string]$Status,
    [string]$Notes
)

. "$PSScriptRoot\_common.ps1"

$PrId = Resolve-PrId -PrId $PrId
$statePath = Get-StateFile -PrId $PrId
$state = Get-Content $statePath -Raw | ConvertFrom-Json

$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }
if ($group) {
    if ($Status) { $group.Status = $Status }
    if ($Notes) { $group.Notes = $Notes }
    $state | ConvertTo-Json -Depth 20 | Set-Content $statePath -Encoding UTF8
    Write-Host "Gruppe ${GroupNr} - Status=$($group.Status), Notes=$($group.Notes)"
} else {
    Write-Error "Gruppe $GroupNr nicht gefunden"
}
