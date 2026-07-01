# ============================================================
# PR-Scripts: Gemeinsame Funktionen & Konfiguration
# Wird von allen PR-Scripts per dot-source geladen:
#   . "$PSScriptRoot\_common.ps1"
# ============================================================

# --- Repo-Root & Routing-Config ---
$script:RepoRoot = (Get-Item "$PSScriptRoot\..\..\..").FullName
$script:RoutingFile = Join-Path $RepoRoot ".claude\meta\pr\routing.json"
$script:ActivePrFile = Join-Path $RepoRoot ".claude\meta\pr\active-pr.json"

if (-not (Test-Path $RoutingFile)) {
    Write-Error "Routing-Config nicht gefunden: $RoutingFile"
    Write-Error "Bitte .claude/meta/pr/routing.json anlegen."
    exit 1
}

$script:Routing = Get-Content $RoutingFile -Raw | ConvertFrom-Json

# --- URLs aus Routing ---
$script:WebBaseUrl = $Routing.urls.web
$script:ApiBaseUrl = $Routing.urls.api
$script:ApiVersion = $Routing.apiVersion

# --- Pfade ---
$script:StateDir = Join-Path $RepoRoot $Routing.paths.stateDir

# --- Active PR laden ---
function Get-ActivePrId {
    param([int]$OverridePrId = 0)

    if ($OverridePrId -gt 0) { return $OverridePrId }

    if (Test-Path $script:ActivePrFile) {
        $activePr = Get-Content $script:ActivePrFile -Raw | ConvertFrom-Json
        return $activePr.prId
    }

    Write-Error "Keine aktive PR. Bitte /pr-init ausfuehren oder -PrId angeben."
    exit 1
}

# --- State-Datei Pfad ---
function Get-StateFile {
    param([int]$PrId)
    return Join-Path $script:StateDir "pr-$PrId-state.json"
}

function Get-RawFile {
    param([int]$PrId)
    return Join-Path $script:StateDir "pr-$PrId-raw.json"
}

# --- PR-URLs ---
function Get-PrWebUrl {
    param([int]$PrId)
    return "$script:WebBaseUrl/pullrequest/$PrId"
}

function Get-CommitWebUrl {
    param([string]$Hash, [string]$Branch = "")
    $url = "$script:WebBaseUrl/commit/$Hash"
    if ($Branch) {
        $branchEncoded = $Branch -replace '/', '%2F'
        $url += "?refName=refs%2Fheads%2F$branchEncoded"
    }
    return $url
}

function Get-ThreadsApiUrl {
    param([int]$PrId)
    return "$script:ApiBaseUrl/pullRequests/$PrId/threads?api-version=$script:ApiVersion"
}

function Get-ThreadApiUrl {
    param([int]$PrId, [int]$ThreadId)
    return "$script:ApiBaseUrl/pullRequests/$PrId/threads/$ThreadId`?api-version=$script:ApiVersion"
}

function Get-PullRequestsApiUrl {
    param([int]$Top = 150, [string]$Status = "completed")
    return "$script:ApiBaseUrl/pullrequests?searchCriteria.status=$Status&`$top=$Top&api-version=$script:ApiVersion"
}

# --- Credential Manager (einmal definiert) ---
if (-not ([System.Management.Automation.PSTypeName]'PrCredentialManager').Type) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public class PrCredentialManager {
    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CredRead(string target, int type, int flags, out IntPtr credential);

    [DllImport("advapi32.dll")]
    public static extern void CredFree(IntPtr credential);

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct CREDENTIAL {
        public int Flags;
        public int Type;
        public string TargetName;
        public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public int CredentialBlobSize;
        public IntPtr CredentialBlob;
        public int Persist;
        public int AttributeCount;
        public IntPtr Attributes;
        public string TargetAlias;
        public string UserName;
    }

    public static string GetPassword(string target) {
        IntPtr credPtr;
        if (CredRead(target, 1, 0, out credPtr)) {
            CREDENTIAL cred = (CREDENTIAL)Marshal.PtrToStructure(credPtr, typeof(CREDENTIAL));
            string password = Marshal.PtrToStringUni(cred.CredentialBlob, cred.CredentialBlobSize / 2);
            CredFree(credPtr);
            return password;
        }
        return null;
    }
}
'@
}

function Get-AuthHeaders {
    $credKey = $script:Routing.auth.credentialKey
    $pat = [PrCredentialManager]::GetPassword($credKey)

    if (-not $pat) {
        Write-Error "PAT nicht gefunden. Bitte speichern mit: cmdkey /generic:$credKey /user:PAT /pass:DEIN_TOKEN"
        exit 1
    }

    $base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
    return @{ Authorization = "Basic $base64Auth" }
}

# --- Auto-Detect PR (fuer Scripts die PrId optional haben) ---
function Resolve-PrId {
    param([int]$PrId = 0)

    if ($PrId -gt 0) { return $PrId }

    # 1. Versuche active-pr.json
    $resolved = Get-ActivePrId -OverridePrId $PrId
    if ($resolved -gt 0) { return $resolved }

    # 2. Fallback: einzige State-Datei
    $stateFiles = Get-ChildItem $script:StateDir -Filter "pr-*-state.json" -ErrorAction SilentlyContinue
    if ($stateFiles.Count -eq 1) {
        return [int]($stateFiles[0].Name -replace 'pr-(\d+)-state\.json', '$1')
    }

    Write-Error "PR-ID konnte nicht ermittelt werden. Bitte -PrId angeben oder /pr-init ausfuehren."
    exit 1
}
