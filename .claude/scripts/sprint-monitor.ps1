$worktrees = @(
    @{Label='V1-Param';  Path='C:\Users\Administrator\Documents\Work\Code2\DCSRE_Azure\OmniCommand-V1-Param'},
    @{Label='V2-Audit';  Path='C:\Users\Administrator\Documents\Work\Code2\DCSRE_Azure\OmniCommand-V2-Audit'},
    @{Label='V3-SCI';    Path='C:\Users\Administrator\Documents\Work\Code2\DCSRE_Azure\OmniCommand-V3-SCI-Uebergang'},
    @{Label='V4-Mermaid';Path='C:\Users\Administrator\Documents\Work\Code2\DCSRE_Azure\OmniCommand-V4-Mermaid'},
    @{Label='V5-Monitor';Path='C:\Users\Administrator\Documents\Work\Code2\DCSRE_Azure\OmniCommand-V5-Monitor'}
)
$outFile = 'C:\Users\Administrator\Documents\Work\Code2\DCSRE_Azure\OmniCommand\.claude\sprint-status.md'

while ($true) {
    $ts = Get-Date -Format 'HH:mm'
    $lines = @("# SPRINT STATUS $ts", "")

    foreach ($wt in $worktrees) {
        $mf = "C:\Users\Administrator\Documents\DCS\OmniCommand\_manifest.md"
        if (Test-Path $mf) {
            $phase  = (Select-String -Path $mf -Pattern '^PHASE:'      | Select-Object -First 1).Line
            $next   = (Select-String -Path $mf -Pattern '^NAECHSTER'   | Select-Object -First 1).Line
            $scstat = (Select-String -Path $mf -Pattern '^sc_status:'  | Select-Object -First 1).Line
            $lines += "$($wt.Label) | $phase | $scstat | $next"
        } else {
            $lines += "$($wt.Label) | manifest nicht gefunden"
        }
    }

    $lines += ""
    $lines += "Updated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
    $lines -join "`n" | Out-File $outFile -Encoding UTF8
    Start-Sleep -Seconds 300
}
