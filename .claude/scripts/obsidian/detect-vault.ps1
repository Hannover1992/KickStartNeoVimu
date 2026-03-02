# detect-vault.ps1
# Erkennt automatisch den Ziel-Vault basierend auf Projekt-Pfad
# DYNAMISCH: Funktioniert in DCSRE, CenCoCo, Private/Brain

param(
    [Parameter(Mandatory=$false)]
    [string]$CurrentPath = (Get-Location).Path,  # Default: aktueller Pfad

    [Parameter(Mandatory=$false)]
    [string]$ConfigPath  # Wird auto-detected wenn nicht angegeben
)

# Auto-detect ConfigPath (suche von aktuellem Pfad nach .claude/config/)
if (-not $ConfigPath) {
    $searchPath = $CurrentPath
    while ($searchPath -and (Test-Path $searchPath)) {
        $candidate = Join-Path $searchPath ".claude\config\vault-routing.json"
        if (Test-Path $candidate) {
            $ConfigPath = $candidate
            break
        }
        # Gehe eine Ebene hoeher
        $parent = Split-Path $searchPath -Parent
        if ($parent -eq $searchPath) { break }  # Root erreicht
        $searchPath = $parent
    }
}

# Fallback: relativ zu Script-Location
if (-not $ConfigPath) {
    $ConfigPath = Join-Path (Split-Path (Split-Path $PSScriptRoot -Parent) -Parent) "config\vault-routing.json"
}

# Lade Config
if (-not (Test-Path $ConfigPath)) {
    Write-Error "vault-routing.json nicht gefunden: $ConfigPath"
    exit 1
}

$config = Get-Content $ConfigPath -Raw | ConvertFrom-Json

# Detection Logic
$detectedVault = $null
$matchedRule = $null

foreach ($rule in ($config.detection.rules | Sort-Object priority)) {
    $pattern = $rule.pattern

    # Wildcard-Match (Default-Rule)
    if ($pattern -eq "*") {
        $detectedVault = $rule.vault
        $matchedRule = $rule
        break
    }

    # Pattern-Match (case-insensitive)
    if ($CurrentPath -match $pattern) {
        $detectedVault = $rule.vault
        $matchedRule = $rule
        break
    }
}

# Vault-Pfad nachschlagen
$vaultPath = $config.vaults.$detectedVault.path

# Verifiziere ob Vault existiert
if (-not (Test-Path $vaultPath)) {
    Write-Warning "Vault erkannt aber Pfad existiert nicht: $vaultPath"
    Write-Warning "Vault wird trotzdem zurueckgegeben (moeglicherweise muss er erstellt werden)"
}

# Verifiziere ob .obsidian/ Ordner existiert
$obsidianPath = Join-Path $vaultPath ".obsidian"
$isValidVault = Test-Path $obsidianPath

# Ausgabe als JSON
$result = @{
    Vault = $detectedVault
    Path = $vaultPath
    Rule = @{
        Pattern = $matchedRule.pattern
        Priority = $matchedRule.priority
        Description = $matchedRule.description
    }
    CurrentPath = $CurrentPath
    IsValidVault = $isValidVault
    ObsidianPath = $obsidianPath
}

$result | ConvertTo-Json -Depth 10
