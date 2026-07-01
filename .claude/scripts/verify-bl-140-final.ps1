#Requires -Version 5.1
# BL-140 Final Verify Script
# Prueft alle Verdrahtungs-Invarianten nach Slice 1-5.

$ErrorActionPreference = 'Stop'

$repoRoot   = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$claudeRoot = "$repoRoot\.claude"
$cmdDir     = "$claudeRoot\commands"

$timestamp = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'

Write-Host ""
Write-Host "=== BL-140 Final Verify ===" -ForegroundColor Cyan
Write-Host "Datum: $timestamp"
Write-Host "CmdDir: $cmdDir"
Write-Host ""

$results = @()
$allPass = $true

function Add-Check {
    param($Id, $Name, $Status, $Reason)
    $script:results += [PSCustomObject]@{ Id=$Id; Name=$Name; Status=$Status; Reason=$Reason }
    if ($Status -eq 'FAIL') { $script:allPass = $false }
}

function Count-Matches {
    param($Pattern, $Path, $Recurse=$true)
    try {
        if ($Recurse) {
            $files = Get-ChildItem -Path $Path -Filter '*.md' -Recurse -ErrorAction Stop
        } else {
            $files = Get-ChildItem -Path $Path -Filter '*.md' -ErrorAction Stop
        }
        $count = 0
        foreach ($f in $files) {
            $content = Get-Content $f.FullName -Raw -ErrorAction SilentlyContinue
            if ($content -and ($content | Select-String -Pattern $Pattern -Quiet)) {
                $matches = [regex]::Matches($content, $Pattern)
                $count += $matches.Count
            }
        }
        return $count
    } catch {
        return -1
    }
}

# --- CHECK 1: C4 status:DELETED (1 Treffer) ---
$c4File = "$cmdDir\_SDF_berater_sdfHub.md"
if (Test-Path $c4File) {
    $c4Content = Get-Content $c4File -Raw -ErrorAction SilentlyContinue
    if ($c4Content -and ($c4Content | Select-String -Pattern 'status:\s*DELETED' -Quiet)) {
        Add-Check '01' 'C4 status:DELETED' 'PASS' 'sdfHub.md enthaelt status:DELETED'
    } else {
        Add-Check '01' 'C4 status:DELETED' 'FAIL' 'sdfHub.md gefunden aber kein status:DELETED'
    }
} else {
    Add-Check '01' 'C4 status:DELETED' 'FAIL' "File nicht gefunden: $c4File"
}

# --- CHECK 2: 4 Phase-0-Berater haben SCHRITT 0a Slug-Lookup ---
$phase0Files = @(
    "$cmdDir\_SDF_berater_validator.md",
    "$cmdDir\_SDF_berater_dependencyAnalyzer.md",
    "$cmdDir\_SDF_berater_sequencePlanner.md",
    "$cmdDir\_SDF_berater_batchPlanner.md"
)
$slugCount = 0
foreach ($f in $phase0Files) {
    if (Test-Path $f) {
        $c = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($c -and ($c | Select-String -Pattern 'SCHRITT 0a' -Quiet)) { $slugCount++ }
    }
}
if ($slugCount -ge 4) {
    Add-Check '02' 'Phase-0 SCHRITT-0a Slug-Lookup' 'PASS' "$slugCount/4 Berater haben SCHRITT 0a"
} else {
    Add-Check '02' 'Phase-0 SCHRITT-0a Slug-Lookup' 'FAIL' "Nur $slugCount/4 Berater haben SCHRITT 0a"
}

# --- CHECK 3: 4 Phase-0-Berater verwenden {bl_slug}/6_PL/ (kein BL-{NNN}) ---
$slugPathCount = 0
$badPathCount  = 0
foreach ($f in $phase0Files) {
    if (Test-Path $f) {
        $c = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($c) {
            if ($c | Select-String -Pattern '\{bl_slug\}/6_PL/' -Quiet) { $slugPathCount++ }
            if ($c | Select-String -Pattern 'BL-\d{3}/6_PL/' -Quiet)    { $badPathCount++ }
        }
    }
}
if ($slugPathCount -ge 4 -and $badPathCount -eq 0) {
    Add-Check '03' 'Phase-0 {bl_slug} Pfad' 'PASS' "$slugPathCount Treffer {bl_slug}/6_PL/, 0 BL-NNN-Reste"
} elseif ($badPathCount -gt 0) {
    Add-Check '03' 'Phase-0 {bl_slug} Pfad' 'FAIL' "$badPathCount BL-NNN-Pfade noch vorhanden"
} else {
    Add-Check '03' 'Phase-0 {bl_slug} Pfad' 'FAIL' "Nur $slugPathCount/4 Berater haben {bl_slug}/6_PL/"
}

# --- CHECK 4: C2/C5/C6/C7 Frontmatter batch_aware: true (>=4 Treffer) ---
$dispatcherFiles = @(
    "$cmdDir\_SDF_berater_itemContext.md",
    "$cmdDir\_SDF_berater_recalibrate.md",
    "$cmdDir\_SDF_berater_postItem.md",
    "$cmdDir\_SDF_berater_statusTransition.md"
)
$batchAwareCount = 0
foreach ($f in $dispatcherFiles) {
    if (Test-Path $f) {
        $c = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($c -and ($c | Select-String -Pattern 'batch_aware:\s*true' -Quiet)) { $batchAwareCount++ }
    }
}
if ($batchAwareCount -ge 4) {
    Add-Check '04' 'C2/C5/C6/C7 batch_aware:true' 'PASS' "$batchAwareCount/4 Dispatcher haben batch_aware:true"
} else {
    Add-Check '04' 'C2/C5/C6/C7 batch_aware:true' 'FAIL' "Nur $batchAwareCount/4 Dispatcher haben batch_aware:true"
}

# --- CHECK 5: C12/C13 Frontmatter wired_in: _PostBatch_orchestrate (>=2 Treffer) ---
$postBatchFiles = @(
    "$cmdDir\_SDF_berater_garbageCollection.md",
    "$cmdDir\_SDF_berater_stateMaintain.md"
)
$wiredCount = 0
foreach ($f in $postBatchFiles) {
    if (Test-Path $f) {
        $c = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($c -and ($c | Select-String -Pattern 'wired_in:.*_PostBatch_orchestrate' -Quiet)) { $wiredCount++ }
    }
}
if ($wiredCount -ge 2) {
    Add-Check '05' 'C12/C13 wired_in PostBatch' 'PASS' "$wiredCount/2 PostBatch-Berater haben wired_in"
} else {
    Add-Check '05' 'C12/C13 wired_in PostBatch' 'FAIL' "Nur $wiredCount/2 haben wired_in:_PostBatch_orchestrate"
}

# --- CHECK 6: SDF SCHRITT 0.6 + 3.1 + 3.2 + 3.3 vorhanden ---
$sdfFile = "$cmdDir\_SDF_orchestrate.md"
$sdfSchritte = @('SCHRITT 0\.6', 'SCHRITT 3\.1', 'SCHRITT 3\.2', 'SCHRITT 3\.3')
$sdfSchritteFound = 0
if (Test-Path $sdfFile) {
    $sdfContent = Get-Content $sdfFile -Raw -ErrorAction SilentlyContinue
    foreach ($pat in $sdfSchritte) {
        if ($sdfContent -and ($sdfContent | Select-String -Pattern $pat -Quiet)) { $sdfSchritteFound++ }
    }
}
if ($sdfSchritteFound -ge 4) {
    Add-Check '06' 'SDF SCHRITT 0.6/3.1/3.2/3.3' 'PASS' "Alle 4 Schritte in _SDF_orchestrate.md gefunden"
} else {
    Add-Check '06' 'SDF SCHRITT 0.6/3.1/3.2/3.3' 'FAIL' "Nur $sdfSchritteFound/4 Schritte gefunden"
}

# --- CHECK 7: PostBatch Skill(_SDF_berater_garbageCollection) + Skill(_SDF_berater_stateMaintain) ---
$postBatchCmd = "$cmdDir\_PostBatch_orchestrate.md"
$postBatchSkills = 0
if (Test-Path $postBatchCmd) {
    $pbContent = Get-Content $postBatchCmd -Raw -ErrorAction SilentlyContinue
    if ($pbContent) {
        if ($pbContent | Select-String -Pattern 'Skill\(_SDF_berater_garbageCollection\)' -Quiet) { $postBatchSkills++ }
        if ($pbContent | Select-String -Pattern 'Skill\(_SDF_berater_stateMaintain\)'     -Quiet) { $postBatchSkills++ }
    }
}
if ($postBatchSkills -ge 2) {
    Add-Check '07' 'PostBatch Skill C12+C13' 'PASS' "Beide Skill-Calls in _PostBatch_orchestrate.md"
} else {
    Add-Check '07' 'PostBatch Skill C12+C13' 'FAIL' "Nur $postBatchSkills/2 Skill-Calls gefunden"
}

# --- CHECK 8: 4 Sub-Pipelines bl_140_pflaster_code: true (4 Treffer) ---
$subPipelineFiles = @(
    "$cmdDir\_I_orchestrate.md",
    "$cmdDir\_SC_orchestrate.md",
    "$cmdDir\_WP_orchestrate.md",
    "$cmdDir\_TDD_orchestrate.md"
)
$pflasterFmCount = 0
foreach ($f in $subPipelineFiles) {
    if (Test-Path $f) {
        $c = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($c -and ($c | Select-String -Pattern 'bl_140_pflaster_code:\s*true' -Quiet)) { $pflasterFmCount++ }
    }
}
if ($pflasterFmCount -ge 4) {
    Add-Check '08' 'Sub-Pipelines bl_140_pflaster_code' 'PASS' "$pflasterFmCount/4 Sub-Pipelines haben bl_140_pflaster_code:true"
} else {
    Add-Check '08' 'Sub-Pipelines bl_140_pflaster_code' 'FAIL' "Nur $pflasterFmCount/4 Sub-Pipelines haben bl_140_pflaster_code:true"
}

# --- CHECK 9: INV-{I,SC,WP,TDD}-PFLASTER-2 (4 Treffer) ---
$invPatterns = @('INV-I-PFLASTER-2', 'INV-SC-PFLASTER-2', 'INV-WP-PFLASTER-2', 'INV-TDD-PFLASTER-2')
$invCount = 0
for ($i = 0; $i -lt $subPipelineFiles.Count; $i++) {
    $f   = $subPipelineFiles[$i]
    $pat = $invPatterns[$i]
    if (Test-Path $f) {
        $c = Get-Content $f -Raw -ErrorAction SilentlyContinue
        if ($c -and ($c | Select-String -Pattern $pat -Quiet)) { $invCount++ }
    }
}
if ($invCount -ge 4) {
    Add-Check '09' 'INV-{I,SC,WP,TDD}-PFLASTER-2' 'PASS' "Alle 4 INV-Marker gefunden"
} else {
    Add-Check '09' 'INV-{I,SC,WP,TDD}-PFLASTER-2' 'FAIL' "Nur $invCount/4 INV-PFLASTER-2 gefunden"
}

# --- AUSGABE: PASS/FAIL Tabelle ---
Write-Host ""
Write-Host ("  {0,-4}  {1,-35}  {2,-6}  {3}" -f "ID", "Check", "Status", "Reason")
Write-Host ("  {0,-4}  {1,-35}  {2,-6}  {3}" -f "----", "-----------------------------------", "------", "------")

foreach ($r in $results) {
    $color = if ($r.Status -eq 'PASS') { 'Green' } else { 'Red' }
    Write-Host ("  {0,-4}  {1,-35}  {2,-6}  {3}" -f $r.Id, $r.Name, $r.Status, $r.Reason) -ForegroundColor $color
}

Write-Host ""
if ($allPass) {
    Write-Host "GESAMT: PASS -- alle 9 Checks bestanden" -ForegroundColor Green
} else {
    $failCount = ($results | Where-Object { $_.Status -eq 'FAIL' }).Count
    Write-Host "GESAMT: FAIL -- $failCount von 9 Checks fehlgeschlagen" -ForegroundColor Red
    exit 1
}
