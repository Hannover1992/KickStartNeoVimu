# sync-with-frontmatter.ps1
# Kopiert Datei in Vault und fuegt Frontmatter hinzu
# DYNAMISCH: Funktioniert in allen Projekten

param(
    [Parameter(Mandatory=$true)]
    [string]$SourcePath,        # Quell-Datei (.claude/analysis/...)

    [Parameter(Mandatory=$true)]
    [string]$VaultPath,         # Ziel im Vault (z.B. C:\Users\...\DCS\Dateiabholung-ANALYSE.md)

    [Parameter(Mandatory=$true)]
    [string]$FrontmatterJson    # YAML-Frontmatter als JSON-Objekt
)

# Parse Frontmatter
$fm = $FrontmatterJson | ConvertFrom-Json

# Kopiere Datei
Copy-Item $SourcePath $VaultPath -Force

# Lese existierende Datei
$existing = Get-Content $VaultPath -Encoding UTF8

# Baue Frontmatter-Header
$header = @("---")

# ID
$header += "id: $($fm.id)"

# Aliases (Array)
$header += "aliases:"
foreach ($alias in $fm.aliases) {
    $header += "  - $alias"
}

# Tags (Array)
$header += "tags:"
foreach ($tag in $fm.tags) {
    $header += "  - $tag"
}

# Feature
$header += "feature: '$($fm.feature)'"

# Chain-Felder (falls vorhanden)
if ($fm.cycle) {
    $header += "cycle: $($fm.cycle)"
}
if ($fm.'chain-position') {
    $header += "chain-position: $($fm.'chain-position')"
}
if ($fm.prev) {
    $header += "prev: '$($fm.prev)'"
}
if ($fm.next) {
    $header += "next: '$($fm.next)'"
}
if ($fm.'model-br') {
    $header += "model-br: '$($fm.'model-br')'"
}

$header += "---"
$header += ""

# Callout (falls vorhanden)
if ($fm.callout) {
    $header += "> [!info] Feature-Kontext"
    $header += "> $($fm.callout)"
    $header += ""
}

# Kombiniere Header + Inhalt
$header + $existing | Set-Content $VaultPath -Encoding UTF8

Write-Host "Synced: $VaultPath ($(($header + $existing).Count) lines)"
