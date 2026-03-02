<#
.SYNOPSIS
    Holt PR-Kommentare von TFS und erstellt Arbeits-Markdown

.EXAMPLE
    .\fetch.ps1 -PrId 18979
    .\fetch.ps1 -Url "https://tfs.itsg.de/.../pullrequest/18979"
#>
param(
    [int]$PrId = 0,
    [string]$Url = ""
)

$ScriptDir = $PSScriptRoot
$OutputDir = "C:\Users\Administrator\Documents\Work\Code2\DCSRE\Sources\Backend\.claude\analysis"

# Sicherstellen dass der Ordner existiert
if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

# ============ URL PARSING ============
if ($Url -and -not $PrId) {
    if ($Url -match "pullrequest[/s](\d+)") {
        $PrId = [int]$Matches[1]
        Write-Host "PR-ID aus URL extrahiert: $PrId" -ForegroundColor Cyan
    } else {
        Write-Error "Konnte PR-ID nicht aus URL extrahieren: $Url"
        exit 1
    }
}

if ($PrId -eq 0) {
    Write-Error "Bitte PR-ID oder URL angeben: .\fetch.ps1 -PrId 18979"
    exit 1
}

# ============ CREDENTIAL MANAGER ============
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;

public class CredentialManager {
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

$pat = [CredentialManager]::GetPassword('TFS_ITSG_PAT')

if (-not $pat) {
    Write-Error "PAT nicht gefunden. Bitte speichern mit: cmdkey /generic:TFS_ITSG_PAT /user:PAT /pass:DEIN_TOKEN"
    exit 1
}

# ============ API ABRUF ============
Write-Host "Lade Kommentare fuer PR #$PrId..." -ForegroundColor Cyan

$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{ Authorization = "Basic $base64Auth" }

$threadsUrl = "https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_apis/git/repositories/DCSRE/pullRequests/$PrId/threads?api-version=6.0"
$threads = Invoke-RestMethod -Uri $threadsUrl -Headers $headers

# JSON speichern
$jsonFile = Join-Path $OutputDir "pr-$PrId-comments.json"
$threads | ConvertTo-Json -Depth 20 | Out-File -FilePath $jsonFile -Encoding UTF8
Write-Host "JSON gespeichert: $jsonFile" -ForegroundColor Green

# ============ AKTIVE KOMMENTARE FILTERN ============
$activeComments = $threads.value | Where-Object {
    $_.status -eq 'active' -and $_.threadContext -ne $null
} | Sort-Object { $_.threadContext.filePath }

Write-Host "Aktive Code-Kommentare: $($activeComments.Count)" -ForegroundColor Yellow

# ============ GRUPPIERUNG NACH KOMMENTAR-MUSTER ============
$groups = @{}

foreach ($thread in $activeComments) {
    $firstComment = $thread.comments[0]
    $content = $firstComment.content -replace '@<[^>]+>', ''  # Mentions entfernen
    $content = $content.Trim()

    # Ersten Satz als Gruppierungsschluessel
    $key = if ($content.Length -gt 80) {
        $content.Substring(0, 80) -replace '\s+\S*$', '...'
    } else {
        $content
    }

    if (-not $groups.ContainsKey($key)) {
        $groups[$key] = @{
            Pattern = $key
            FullComment = $content
            Author = $firstComment.author.displayName
            Threads = @()
        }
    }

    $line = if ($thread.threadContext.leftFileStart) {
        $thread.threadContext.leftFileStart.line
    } elseif ($thread.threadContext.rightFileStart) {
        $thread.threadContext.rightFileStart.line
    } else { 0 }

    $groups[$key].Threads += @{
        Id = $thread.id
        File = $thread.threadContext.filePath
        Line = $line
    }
}

# ============ MARKDOWN GENERIEREN ============
$mdFile = Join-Path $OutputDir "pr-$PrId-arbeitsplan.md"
$md = @()

$md += "# PR #$PrId - Arbeitsplan"
$md += ""
$md += "**Erstellt:** $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
$md += "**Aktive Kommentare:** $($activeComments.Count)"
$md += "**Gruppen:** $($groups.Count)"
$md += ""
$md += "---"
$md += ""

$groupNum = 1
foreach ($group in ($groups.Values | Sort-Object { -$_.Threads.Count })) {
    $ids = ($group.Threads | ForEach-Object { $_.Id }) -join ', '

    $md += "## Gruppe $groupNum : $($group.Threads.Count) Kommentar(e)"
    $md += ""
    $md += "**IDs:** ``$ids``"
    $md += ""
    $md += "**Kommando:** ``.\open.ps1 -Ids $ids``"
    $md += ""
    $md += "### Dateien"
    $md += ""
    $md += "| ID | Datei | Zeile |"
    $md += "|---:|-------|------:|"

    foreach ($t in $group.Threads) {
        $shortFile = $t.File -replace '^/Sources/Backend/', ''
        $md += "| $($t.Id) | ``$shortFile`` | $($t.Line) |"
    }

    $md += ""
    $md += "### Kommentar ($($group.Author))"
    $md += ""
    $md += "> $($group.FullComment -replace "`n", "`n> ")"
    $md += ""
    $md += "---"
    $md += ""

    $groupNum++
}

# Quick-Reference am Ende
$md += "## Quick Reference - Alle IDs"
$md += ""
$md += "| Gruppe | IDs |"
$md += "|-------:|-----|"

$groupNum = 1
foreach ($group in ($groups.Values | Sort-Object { -$_.Threads.Count })) {
    $ids = ($group.Threads | ForEach-Object { $_.Id }) -join ', '
    $md += "| $groupNum | ``$ids`` |"
    $groupNum++
}

$md | Out-File -FilePath $mdFile -Encoding UTF8

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Arbeitsplan erstellt: $mdFile" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Naechste Schritte:" -ForegroundColor Cyan
Write-Host "  1. Oeffne $mdFile"
Write-Host "  2. Waehle eine Gruppe"
Write-Host "  3. Kopiere die IDs"
Write-Host "  4. .\open.ps1 -Ids 121074,121075,121076"
