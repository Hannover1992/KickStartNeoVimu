param([int]$ThreadId = 121039, [int]$PrId = 18979)

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class CredMgr {
    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    public static extern bool CredRead(string target, int type, int flags, out IntPtr credential);
    [DllImport("advapi32.dll")]
    public static extern void CredFree(IntPtr credential);
    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    public struct CREDENTIAL {
        public int Flags; public int Type; public string TargetName; public string Comment;
        public System.Runtime.InteropServices.ComTypes.FILETIME LastWritten;
        public int CredentialBlobSize; public IntPtr CredentialBlob; public int Persist;
        public int AttributeCount; public IntPtr Attributes; public string TargetAlias; public string UserName;
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

$pat = [CredMgr]::GetPassword('TFS_ITSG_PAT')
$base64Auth = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":$pat"))
$headers = @{ Authorization = "Basic $base64Auth" }

$url = "https://tfs.itsg.de/tfs/ITSGCollection/DCS_Pflege/_apis/git/repositories/DCSRE/pullRequests/$PrId/threads/$ThreadId`?api-version=6.0"
$thread = Invoke-RestMethod -Uri $url -Headers $headers

Write-Host "Thread $ThreadId - Details:" -ForegroundColor Cyan
Write-Host "  Kommentare gesamt: $($thread.comments.Count)"
Write-Host ""

foreach ($comment in $thread.comments) {
    Write-Host "  [$($comment.id)] $($comment.author.displayName)" -ForegroundColor Yellow
    Write-Host "       UniqueID: $($comment.author.uniqueName)"
    Write-Host "       Datum: $($comment.publishedDate)"
    Write-Host "       Inhalt: $($comment.content.Substring(0, [Math]::Min(50, $comment.content.Length)))..."
    Write-Host ""
}

$lastComment = $thread.comments | Select-Object -Last 1
Write-Host "LETZTER AUTOR: $($lastComment.author.displayName)" -ForegroundColor Green
