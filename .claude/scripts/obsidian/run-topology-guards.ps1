# run-topology-guards.ps1
# Fuehrt 5 Topology-Guards aus (G-CHAIN, G-BIDIR, G-NAME, G-XREF, G-CAUSAL)
# DYNAMISCH: Funktioniert in allen Projekten

param(
    [Parameter(Mandatory=$true)]
    [string]$ChainMapJson,      # Chain-Map als JSON (Knoten + Kanten)

    [Parameter(Mandatory=$true)]
    [string]$SyncTableJson,     # Sync-Tabelle als JSON (Quelle → Vault Mapping)

    [Parameter(Mandatory=$true)]
    [string]$ManifestHistoryJson # Zyklus-Historie als JSON (fuer Labels)
)

$chainMap = $ChainMapJson | ConvertFrom-Json
$syncTable = $SyncTableJson | ConvertFrom-Json
$history = $ManifestHistoryJson | ConvertFrom-Json

$results = @{
    'G-CHAIN' = @{ Status = 'PASS'; Details = @() }
    'G-BIDIR' = @{ Status = 'PASS'; Details = @() }
    'G-NAME' = @{ Status = 'PASS'; Details = @() }
    'G-XREF' = @{ Status = 'PASS'; Details = @() }
    'G-CAUSAL' = @{ Status = 'PASS'; Details = @() }
}

# ===== G-CHAIN: Chain-Vollstaendigkeit =====
$maxCycle = ($chainMap.nodes | Where-Object { $_.type -eq 'analyse' } | Measure-Object -Property cycle -Maximum).Maximum

for ($i = 1; $i -le $maxCycle; $i++) {
    $analyse = $chainMap.nodes | Where-Object { $_.type -eq 'analyse' -and $_.cycle -eq $i }
    $ergebnis = $chainMap.nodes | Where-Object { $_.type -eq 'ergebnis' -and $_.cycle -eq $i }

    if (-not $analyse) {
        $results['G-CHAIN'].Status = 'WARN'
        $results['G-CHAIN'].Details += "Zyklus $i: ANALYSE fehlt"
    }

    # ERGEBNIS darf beim letzten Zyklus fehlen (in Arbeit)
    if ($i -lt $maxCycle -and -not $ergebnis) {
        $results['G-CHAIN'].Status = 'WARN'
        $results['G-CHAIN'].Details += "Zyklus $i: ERGEBNIS fehlt aber ANALYSE$($i+1) existiert"
    }
}

$hypothese = $chainMap.nodes | Where-Object { $_.type -eq 'hypothese' }
if (-not $hypothese) {
    $results['G-CHAIN'].Status = 'WARN'
    $results['G-CHAIN'].Details += "HYPOTHESEN-Dokument fehlt"
}

if ($results['G-CHAIN'].Details.Count -eq 0) {
    $results['G-CHAIN'].Details += "Alle $maxCycle Zyklen vollstaendig"
}

# ===== G-BIDIR: Bidirektionale Konsistenz =====
$bidirErrors = 0
foreach ($node in $chainMap.nodes) {
    if ($node.prev) {
        $prevNode = $chainMap.nodes | Where-Object { $_.id -eq $node.prev }
        if ($prevNode) {
            if ($prevNode.next -and $prevNode.next -ne $node.id) {
                $results['G-BIDIR'].Status = 'WARN'
                $results['G-BIDIR'].Details += "$($node.id).prev zeigt auf $($node.prev), aber $($node.prev).next zeigt auf $($prevNode.next)"
                $bidirErrors++
            }
        }
    }
}

if ($bidirErrors -eq 0) {
    $pairCount = ($chainMap.nodes | Where-Object { $_.prev }).Count
    $results['G-BIDIR'].Details += "$pairCount prev/next-Paare symmetrisch"
}

# ===== G-NAME: Vault-Namen-Konsistenz =====
$renameCount = 0
foreach ($entry in $syncTable) {
    $sourceName = Split-Path -Leaf $entry.source
    $vaultName = Split-Path -Leaf $entry.vault

    if ($sourceName -ne $vaultName) {
        $results['G-NAME'].Status = 'WARN'
        $results['G-NAME'].Details += "$sourceName → $vaultName (Umbenennung)"
        $renameCount++
    }
}

if ($renameCount -eq 0) {
    $results['G-NAME'].Details += "Alle Namen identisch (kein Rename)"
} else {
    $results['G-NAME'].Details = @("$renameCount Umbenennungen gefunden:") + $results['G-NAME'].Details
}

# ===== G-XREF: Externe Referenz-Kanten =====
$analyseWithoutModel = 0
foreach ($node in $chainMap.nodes | Where-Object { $_.type -eq 'analyse' }) {
    $hasModelEdge = $chainMap.edges | Where-Object {
        ($_.from -eq $node.id -and $_.to -eq 'MODEL') -or
        ($_.from -eq 'MODEL' -and $_.to -eq $node.id)
    }

    if (-not $hasModelEdge) {
        $results['G-XREF'].Status = 'WARN'
        $results['G-XREF'].Details += "$($node.id) hat keine MODEL-Kante"
        $analyseWithoutModel++
    }
}

if ($analyseWithoutModel -eq 0) {
    $analyseCount = ($chainMap.nodes | Where-Object { $_.type -eq 'analyse' }).Count
    $results['G-XREF'].Details += "Alle $analyseCount ANALYSE-Knoten haben MODEL-Kante"
}

# ===== G-CAUSAL: Kausale Kanten-Labels =====
$edgesWithoutLabel = 0
foreach ($edge in $chainMap.edges | Where-Object { $_.type -eq 'causal' }) {
    if (-not $edge.label -or $edge.label -eq '') {
        $results['G-CAUSAL'].Status = 'WARN'
        $results['G-CAUSAL'].Details += "Kante $($edge.from)→$($edge.to) ohne Label"
        $edgesWithoutLabel++
    }
}

if ($edgesWithoutLabel -eq 0) {
    $causalCount = ($chainMap.edges | Where-Object { $_.type -eq 'causal' }).Count
    $results['G-CAUSAL'].Details += "Alle $causalCount kausalen Kanten haben Label"
}

# ===== OUTPUT =====
$summary = @{
    Guards = $results
    PassCount = ($results.Values | Where-Object { $_.Status -eq 'PASS' }).Count
    WarnCount = ($results.Values | Where-Object { $_.Status -eq 'WARN' }).Count
}

$summary | ConvertTo-Json -Depth 10
