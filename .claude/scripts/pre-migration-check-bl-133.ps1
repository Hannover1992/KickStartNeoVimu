#Requires -Version 5.1
# BL-133 Pre-Migration Safety Check
# Prueft ob der Cut von SDF Phasen 4-7 sicher ist (Blueprint §8, D03 Pre-Cut-Schritte)

$ErrorActionPreference = 'Stop'
$VerbosePreference = 'SilentlyContinue'

$manifestPath = "$PSScriptRoot\..\analysis\_manifest.md"
$outputDir    = "$PSScriptRoot\..\output"

$allPass  = $true
$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
$tagStamp  = Get-Date -Format 'yyyyMMdd-HHmm'
$backupTag = "bl-133-pre-migration-$tagStamp"

Write-Host ""
Write-Host "=== BL-133 Pre-Migration Check ===" -ForegroundColor Cyan
Write-Host "Datum: $timestamp"
Write-Host ""

# ---------------------------------------------------------------
# Check 1: df_status darf NICHT in geblockte POST_PHASE-Zustaende
# ---------------------------------------------------------------
$blockedStates = @(
    'POST_PHASE_GUARD',
    'POST_PHASE_QUALITY',
    'POST_PHASE_DELIVERY',
    'POST_PHASE_FINISH'
)

$c1Status  = 'PASS'
$c1Reason  = 'df_status nicht in geblockte POST_PHASE-Zustands-Menge'
$dfStatus  = $null

if (-not (Test-Path $manifestPath)) {
    $c1Status = 'WARN'
    $c1Reason = "Manifest nicht gefunden: $manifestPath"
} else {
    $manifest = Get-Content $manifestPath -Raw -Encoding UTF8
    $match    = [regex]::Match($manifest, '(?m)^\s*df_status:\s*(\S+)')
    if ($match.Success) {
        $dfStatus = $match.Groups[1].Value.TrimEnd(',').Trim()
        if ($blockedStates -contains $dfStatus) {
            $c1Status  = 'FAIL'
            $c1Reason  = "df_status=$dfStatus -- aktive POST_PHASE-Session muss abgeschlossen werden"
            $allPass   = $false
        } else {
            $c1Reason = "df_status=$dfStatus (OK)"
        }
    } else {
        $c1Status = 'WARN'
        $c1Reason = 'df_status-Feld nicht gefunden im Manifest (Edge-Case -- kein FAIL)'
    }
}

$c1Color = if ($c1Status -eq 'PASS') { 'Green' } elseif ($c1Status -eq 'WARN') { 'Yellow' } else { 'Red' }
Write-Host ("Check 1 (df_status):     {0,-6} -- {1}" -f $c1Status, $c1Reason) -ForegroundColor $c1Color

# ---------------------------------------------------------------
# Check 2: post_phase_status -- keine aktiven Sub-Felder
# ---------------------------------------------------------------
$c2Status = 'PASS'
$c2Reason = 'post_phase_status leer oder alle Sub-Felder complete/PASS/SKIP/null'

if (Test-Path $manifestPath) {
    $manifest = Get-Content $manifestPath -Raw -Encoding UTF8

    # Suche post_phase_status Block (YAML-aehnlich, nicht echt YAML)
    $ppMatch = [regex]::Match($manifest, '(?ms)post_phase_status\s*:(.*?)(?=\n\s*\n|\n\*\*|\Z)')
    if ($ppMatch.Success) {
        $block = $ppMatch.Groups[1].Value

        # Aktive Sub-Felder: Wert != complete, PASS, SKIP, null, leer, --
        $activeMatches = [regex]::Matches(
            $block,
            '(?m)^\s*\w+:\s*(?!complete|PASS|SKIP|null|--|$)(\S+)'
        )

        if ($activeMatches.Count -gt 0) {
            $activeValues = ($activeMatches | ForEach-Object { $_.Value.Trim() }) -join '; '
            $c2Status = 'FAIL'
            $c2Reason = "Aktive sub-Felder gefunden: $activeValues"
            $allPass  = $false
        }
    }
    # Kein post_phase_status Block = kein Problem (Feld bereits entfernt oder nie gesetzt)
}

$c2Color = if ($c2Status -eq 'PASS') { 'Green' } elseif ($c2Status -eq 'WARN') { 'Yellow' } else { 'Red' }
Write-Host ("Check 2 (post_phase):    {0,-6} -- {1}" -f $c2Status, $c2Reason) -ForegroundColor $c2Color

# ---------------------------------------------------------------
# Check 3: Aktiver Branch (main = WARN)
# ---------------------------------------------------------------
$c3Status = 'PASS'
$c3Reason = ''
$branch   = $null

try {
    $branch = & git -C $PSScriptRoot rev-parse --abbrev-ref HEAD 2>&1
    if ($LASTEXITCODE -ne 0) {
        $c3Status = 'WARN'
        $c3Reason = "git rev-parse fehlgeschlagen (kein Git-Repo oder git nicht im PATH)"
    } elseif ($branch -eq 'main' -or $branch -eq 'master') {
        $c3Status = 'WARN'
        $c3Reason = "Branch=$branch -- BL-133 sollte auf Feature-Branch laufen, nicht auf main"
    } else {
        $c3Reason = "Branch=$branch (OK)"
    }
} catch {
    $c3Status = 'WARN'
    $c3Reason = "git-Aufruf fehlgeschlagen: $_"
}

$c3Color = if ($c3Status -eq 'PASS') { 'Green' } else { 'Yellow' }
Write-Host ("Check 3 (branch):        {0,-6} -- {1}" -f $c3Status, $c3Reason) -ForegroundColor $c3Color

# ---------------------------------------------------------------
# Gesamt-Ergebnis
# ---------------------------------------------------------------
Write-Host ""
if ($allPass) {
    Write-Host "GESAMT: PASS" -ForegroundColor Green
    Write-Host ""
    Write-Host "Bei PASS -- empfohlener Backup-Tag (User fuehrt git selbst aus):" -ForegroundColor Cyan
    Write-Host "  git tag $backupTag"
    Write-Host "  git tag -l `"bl-133-*`""
    Write-Host ""
    exit 0
} else {
    Write-Host "GESAMT: FAIL" -ForegroundColor Red
    Write-Host ""
    Write-Host "Bei FAIL -- abbrechen, Issue beheben, dann erneut pruefen." -ForegroundColor Red
    Write-Host ""
    exit 1
}
