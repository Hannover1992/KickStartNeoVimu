# compute-hashes.ps1
# Berechnet MD5-Hashes fuer alle Sync-Kandidaten
# DYNAMISCH: Funktioniert in allen Projekten (DCSLESE, DCSRE, CenCoCo, Private/Brain)

param(
    [Parameter(Mandatory=$true)]
    [string]$FilesJson  # JSON-Array mit Pfaden: ["path1", "path2", ...]
)

$files = $FilesJson | ConvertFrom-Json

$results = @()

foreach ($path in $files) {
    if (Test-Path $path) {
        $hash = (Get-FileHash -Path $path -Algorithm MD5).Hash.Substring(0,12)
        $results += [PSCustomObject]@{
            Path = $path
            Hash = $hash
            Exists = $true
        }
    } else {
        $results += [PSCustomObject]@{
            Path = $path
            Hash = $null
            Exists = $false
        }
    }
}

# Output als JSON (kann von Agent geparst werden)
$results | ConvertTo-Json -Depth 10
