#Requires -Version 5.1
# BL-134 Pre-Migration Safety Check (Slice-4 Atom-Point)
# Prueft Vorbedingungen fuer SDF Phase-2 Cut (~939 LOC raus, ~30 LOC rein).

$ErrorActionPreference = 'Stop'
$VerbosePreference = 'SilentlyContinue'

$repoRoot     = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$claudeRoot   = "$repoRoot\.claude"
$manifestPath = "$claudeRoot\analysis\_manifest.md"
$cmdDir       = "$claudeRoot\commands"

$allPass   = $true
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$tagStamp  = Get-Date -Format 'yyyyMMdd-HHmm'
$backupTag = "bl-134-pre-cut-$tagStamp"

Write-Host ""
Write-Host "=== BL-134 Pre-Migration Check (Slice-4 Atom-Cut) ===" -ForegroundColor Cyan
Write-Host "Datum: $timestamp"
Write-Host ""

function Show-Result {
    param($Id, $Name, $Status, $Reason)
    $color = if ($Status -eq 'PASS') { 'Green' }
             elseif ($Status -eq 'WARN' -or $Status -eq 'INFO') { 'Yellow' }
             else { 'Red' }
    Write-Host ("Check {0} ({1,-22}): {2,-6} -- {3}" -f $Id, $Name, $Status, $Reason) -ForegroundColor $color
}

# ---------------------------------------------------------------
# C1: BATCH_STATE Schema im Manifest (INFO)
# ---------------------------------------------------------------
$c1Status = 'PASS'
$c1Reason = 'DF_BATCH_STATE Block-Marker im Manifest gefunden'
if (-not (Test-Path $manifestPath)) {
    $c1Status = 'INFO'
    $c1Reason = "Manifest nicht gefunden: $manifestPath (kein FAIL)"
} else {
    $manifest = Get-Content $manifestPath -Raw -Encoding UTF8
    if ($manifest -notmatch 'DF_BATCH_STATE') {
        $c1Status = 'INFO'
        $c1Reason = 'DF_BATCH_STATE-Block fehlt im Manifest (Slice-3 Setup nachholen)'
    }
}
Show-Result 'C1' 'BATCH_STATE Schema' $c1Status $c1Reason

# ---------------------------------------------------------------
# C2: 4 neue Berater-Files existieren (FAIL)
# ---------------------------------------------------------------
$beraterFiles = @(
    '_SDF_berater_validator.md',
    '_SDF_berater_dependencyAnalyzer.md',
    '_SDF_berater_sequencePlanner.md',
    '_SDF_berater_batchPlanner.md'
)
$missing = @()
foreach ($f in $beraterFiles) {
    if (-not (Test-Path "$cmdDir\$f")) { $missing += $f }
}
$c2Status = if ($missing.Count -eq 0) { 'PASS' } else { 'FAIL' }
$c2Reason = if ($missing.Count -eq 0) { 'alle 4 Berater vorhanden' } else { 'fehlt: ' + ($missing -join ', ') }
if ($c2Status -eq 'FAIL') { $allPass = $false }
Show-Result 'C2' '4 Berater vorhanden' $c2Status $c2Reason

# ---------------------------------------------------------------
# C3: modusEntscheidung batch_aware (FAIL)
# ---------------------------------------------------------------
$c3Path = "$cmdDir\_SDF_berater_modusEntscheidung.md"
$c3Status = 'PASS'
$c3Reason = 'batch_aware: true gefunden'
if (-not (Test-Path $c3Path)) {
    $c3Status = 'FAIL'
    $c3Reason = "Datei fehlt: $c3Path"
    $allPass = $false
} else {
    $content = Get-Content $c3Path -Raw -Encoding UTF8
    if ($content -notmatch '(?m)batch_aware\s*:\s*true') {
        $c3Status = 'FAIL'
        $c3Reason = 'batch_aware: true NICHT gefunden in modusEntscheidung'
        $allPass = $false
    }
}
Show-Result 'C3' 'batch_aware modus' $c3Status $c3Reason

# ---------------------------------------------------------------
# C4: executionDispatch BATCH_STATE-Read (FAIL)
# ---------------------------------------------------------------
$c4Path = "$cmdDir\_SDF_berater_executionDispatch.md"
$c4Status = 'PASS'
$c4Reason = 'DF_BATCH_STATE.modus Lese-Pattern gefunden'
if (-not (Test-Path $c4Path)) {
    $c4Status = 'FAIL'
    $c4Reason = "Datei fehlt: $c4Path"
    $allPass = $false
} else {
    $content = Get-Content $c4Path -Raw -Encoding UTF8
    $matches = [regex]::Matches($content, 'DF_BATCH_STATE\.modus')
    if ($matches.Count -eq 0) {
        $c4Status = 'FAIL'
        $c4Reason = 'DF_BATCH_STATE.modus NICHT gefunden in executionDispatch'
        $allPass = $false
    } else {
        $c4Reason = "DF_BATCH_STATE.modus Treffer: $($matches.Count)"
    }
}
Show-Result 'C4' 'execDispatch reads' $c4Status $c4Reason

# ---------------------------------------------------------------
# C5: Sub-Pipeline-Pflaster bl_134_pflaster: true (FAIL)
# ---------------------------------------------------------------
$subPipelines = @(
    '_I_orchestrate.md',
    '_SC_orchestrate.md',
    '_WP_orchestrate.md',
    '_TDD_orchestrate.md'
)
$missingPflaster = @()
foreach ($p in $subPipelines) {
    $path = "$cmdDir\$p"
    if (-not (Test-Path $path)) {
        $missingPflaster += "$p (DATEI fehlt)"
        continue
    }
    $content = Get-Content $path -Raw -Encoding UTF8
    if ($content -notmatch '(?m)bl_134_pflaster\s*:\s*true') {
        $missingPflaster += $p
    }
}
$c5Status = if ($missingPflaster.Count -eq 0) { 'PASS' } else { 'FAIL' }
$c5Reason = if ($missingPflaster.Count -eq 0) { 'alle 4 Sub-Pipelines tragen bl_134_pflaster: true' } else { 'fehlt: ' + ($missingPflaster -join ', ') }
if ($c5Status -eq 'FAIL') { $allPass = $false }
Show-Result 'C5' 'Sub-Pipeline Pflaster' $c5Status $c5Reason

# ---------------------------------------------------------------
# C6: Branch != main (WARN)
# ---------------------------------------------------------------
$c6Status = 'PASS'
$c6Reason = ''
try {
    $branch = & git -C $repoRoot rev-parse --abbrev-ref HEAD 2>&1
    if ($LASTEXITCODE -ne 0) {
        $c6Status = 'WARN'
        $c6Reason = 'git rev-parse fehlgeschlagen'
    } elseif ($branch -eq 'main' -or $branch -eq 'master') {
        $c6Status = 'WARN'
        $c6Reason = "Branch=$branch -- Cut sollte auf Feature-Branch laufen"
    } else {
        $c6Reason = "Branch=$branch (OK)"
    }
} catch {
    $c6Status = 'WARN'
    $c6Reason = "git-Aufruf fehlgeschlagen: $_"
}
Show-Result 'C6' 'Branch != main' $c6Status $c6Reason

# ---------------------------------------------------------------
# Gesamt
# ---------------------------------------------------------------
Write-Host ""
if ($allPass) {
    Write-Host "GESAMT: PASS" -ForegroundColor Green
    Write-Host ""
    Write-Host "Empfohlener Backup-Tag (User fuehrt git selbst aus):" -ForegroundColor Cyan
    Write-Host "  git tag $backupTag"
    Write-Host "  git tag -l `"bl-134-*`""
    Write-Host ""
    exit 0
} else {
    Write-Host "GESAMT: FAIL" -ForegroundColor Red
    Write-Host ""
    Write-Host "Bei FAIL -- abbrechen, Vorbedingungen herstellen, dann erneut pruefen." -ForegroundColor Red
    Write-Host ""
    exit 1
}
