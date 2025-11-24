# Open PR with specific file in Azure DevOps TFS
# Usage: .\open-pr-file.ps1 -PrNumber 123 -FilePath "/Sources/Frontend/apps/app-standalone/src/app/feature/user/pflegeeinrichtung-user-details/pflegeeinrichtung-user-details.component.html"

param(
    [Parameter(Mandatory=$true)]
    [int]$PrNumber,

    [Parameter(Mandatory=$true)]
    [string]$FilePath
)

# TFS Base URL
$baseUrl = "https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_git/DCSRE"

# URL-encode the file path (replace / with %2F, etc.)
$encodedPath = [System.Uri]::EscapeDataString($FilePath)

# Build the full PR URL with file path
# Azure DevOps PR file view format: pullrequest/{id}?_a=files&path={path}
$prUrl = "$baseUrl/pullrequest/$PrNumber`?_a=files&path=$encodedPath"

Write-Host "Opening PR #$PrNumber at file: $FilePath"
Write-Host "URL: $prUrl"

# Open in default browser
Start-Process $prUrl
