param([int]$GroupNr = 13)

$state = Get-Content 'C:\Users\Administrator\Documents\Work\Code2\DCSRE\Sources\Backend\.claude\analysis\pr-18979-state.json' -Raw | ConvertFrom-Json

$group = $state.Groups | Where-Object { $_.Nr -eq $GroupNr }

Write-Host "=== Gruppe $GroupNr Debug ===" -ForegroundColor Cyan
Write-Host "Theme: $($group.Theme)"
Write-Host "Status: $($group.Status)"
Write-Host ""

# Check Threads type
Write-Host "=== Threads Type Check ===" -ForegroundColor Yellow
Write-Host "  Threads Type: $($group.Threads.GetType().Name)"
Write-Host "  Threads BaseType: $($group.Threads.GetType().BaseType)"
Write-Host "  Threads Count Property: $($group.Threads.Count)"
Write-Host "  Threads as @(): $(@($group.Threads).Count)"
Write-Host ""

# Force array
$threads = @($group.Threads)
Write-Host "=== After @() Force ===" -ForegroundColor Yellow
Write-Host "  Threads Type: $($threads.GetType().Name)"
Write-Host "  Threads Count: $($threads.Count)"
Write-Host ""

foreach ($t in $threads) {
    Write-Host "Thread $($t.Id): IsMyResponse = $($t.IsMyResponse)" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Counts (with @() fix) ===" -ForegroundColor Cyan
$answered = @($threads | Where-Object { $_.IsMyResponse -eq $true }).Count
Write-Host "  Answered: $answered / $($threads.Count)"
