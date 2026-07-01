#Requires -Version 5.1
# BL-134 Post-Cut Verification (Slice-4 Atom-Point)
# Prueft ob SDF Phase-2 Cut korrekt durchgefuehrt wurde.

$ErrorActionPreference = 'Stop'
$VerbosePreference = 'SilentlyContinue'

$repoRoot   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$sdfPath    = "$repoRoot\.claude\commands\_SDF_orchestrate.md"

$allPass = $true
Write-Host ""
Write-Host "=== BL-134 Post-Cut Verify ===" -ForegroundColor Cyan
Write-Host "Datum: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Write-Host ""

if (-not (Test-Path $sdfPath)) {
    Write-Host "FAIL: SDF nicht gefunden: $sdfPath" -ForegroundColor Red
    exit 1
}

$lines       = Get-Content $sdfPath -Encoding UTF8
$content     = $lines -join "`n"
$lineCount   = $lines.Count
# Aktiver Code = ohne Frontmatter (zwischen erstem ```yaml und seinem ```-Ende).
$frontEnd    = 0
for ($i = 1; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^```\s*$') { $frontEnd = $i; break }
}
$activeBody  = ($lines[($frontEnd+1)..($lines.Count-1)]) -join "`n"

function Show-Result {
    param($Id, $Name, $Status, $Reason)
    $color = if ($Status -eq 'PASS') { 'Green' } else { 'Red' }
    Write-Host ("Check {0} ({1,-32}): {2,-6} -- {3}" -f $Id, $Name, $Status, $Reason) -ForegroundColor $color
}

# V1: GENAU 1 Skill(_SDF_berater_executionDispatch in SDF
$v1m = [regex]::Matches($content, 'Skill\(_SDF_berater_executionDispatch')
$v1 = if ($v1m.Count -eq 1) { 'PASS' } else { 'FAIL' }
$v1r = "Treffer=$($v1m.Count) (erwartet=1)"
if ($v1 -eq 'FAIL') { $allPass = $false }
Show-Result 'V1' 'executionDispatch genau 1x'    $v1 $v1r

# V2: KEIN BATCH-ITEM-LOOP Header in aktivem Body (Changelog-Erwaehnung erlaubt)
$v2m = [regex]::Matches($activeBody, '(?m)^##\s+PHASE\s+2:\s+BATCH-ITEM-LOOP')
$v2 = if ($v2m.Count -eq 0) { 'PASS' } else { 'FAIL' }
$v2r = "Header-Treffer=$($v2m.Count) (erwartet=0)"
if ($v2 -eq 'FAIL') { $allPass = $false }
Show-Result 'V2' 'kein BATCH-ITEM-LOOP Header'   $v2 $v2r

# V3: KEIN 'for item in batch' Inline-Loop
$v3m = [regex]::Matches($activeBody, 'for\s+item\s+in\s+batch')
$v3 = if ($v3m.Count -eq 0) { 'PASS' } else { 'FAIL' }
$v3r = "Treffer=$($v3m.Count) (erwartet=0)"
if ($v3 -eq 'FAIL') { $allPass = $false }
Show-Result 'V3' 'kein Inline-Loop Pattern'      $v3 $v3r

# V4: LOC < 1300
$v4 = if ($lineCount -lt 1300) { 'PASS' } else { 'FAIL' }
$v4r = "LOC=$lineCount (Schwelle <1300)"
if ($v4 -eq 'FAIL') { $allPass = $false }
Show-Result 'V4' 'LOC unter Schwelle'            $v4 $v4r

# V5: Phase 0/1/2/3/FINAL Headers vorhanden
$expected = @('PHASE 0:', 'PHASE 1:', 'PHASE 2:', 'PHASE 3:', 'PHASE FINAL:')
$missing = @()
foreach ($h in $expected) {
    if ($activeBody -notmatch [regex]::Escape($h)) { $missing += $h }
}
$v5 = if ($missing.Count -eq 0) { 'PASS' } else { 'FAIL' }
$v5r = if ($missing.Count -eq 0) { 'alle 5 Phasen-Header da' } else { 'fehlt: ' + ($missing -join ', ') }
if ($v5 -eq 'FAIL') { $allPass = $false }
Show-Result 'V5' 'Phase-Header vollstaendig'     $v5 $v5r

# V6: Hub-Invariante #8: kein Skill(_I_/_SC_/_TDD_/_WP_orchestrate) mehr in SDF (alle ueber executionDispatch)
$v6m = [regex]::Matches($activeBody, 'Skill\(_(I|SC|TDD|WP)_orchestrate')
$v6 = if ($v6m.Count -eq 0) { 'PASS' } else { 'FAIL' }
$v6r = "Direkt-Routing-Treffer=$($v6m.Count) (erwartet=0)"
if ($v6 -eq 'FAIL') { $allPass = $false }
Show-Result 'V6' 'Hub-Invariante #8 (no direct)' $v6 $v6r

Write-Host ""
if ($allPass) {
    Write-Host "GESAMT: PASS" -ForegroundColor Green
    exit 0
} else {
    Write-Host "GESAMT: FAIL" -ForegroundColor Red
    exit 1
}
