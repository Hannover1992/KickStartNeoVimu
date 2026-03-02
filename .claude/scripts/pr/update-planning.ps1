param(
    [int]$PrId = 18979
)

$stateFile = "C:\Users\Administrator\Documents\Work\Code2\DCSRE\Sources\Backend\.claude\analysis\pr-$PrId-state.json"
$state = Get-Content $stateFile -Raw | ConvertFrom-Json

# Planning-Daten fuer jede Gruppe
$planningData = @{
    2 = @{
        Summary = 'SetupController Log-Message entspricht bereits DCSRE-Standard. BEREITS KORREKT.'
        EstimatedTime = '0min'
        Complexity = 'S'
        AffectedFiles = @('SetupController.cs')
        SolutionApproach = 'Keine Aktion erforderlich - Thread kann geschlossen werden.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    4 = @{
        Summary = 'Englische Texte in 3 Dateien auf Deutsch umstellen. DownloadToPathCommand hat englische Log-Meldung.'
        EstimatedTime = '30min'
        Complexity = 'M'
        AffectedFiles = @('UploadFromPathCommand.cs', 'DicPortAllocator.cs', 'DownloadToPathCommand.cs')
        SolutionApproach = 'Log-Messages uebersetzen: Download failed -> Download fehlgeschlagen'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    6 = @{
        Summary = 'Magic Strings BEREIT, UPLOAD_BNIK, DCS_0_00000 sind bereits in Konstanten. BEREITS ERLEDIGT.'
        EstimatedTime = '0min'
        Complexity = 'S'
        AffectedFiles = @('StoredFile.cs', 'DicPathComponents.cs', 'UploadMetadata.cs')
        SolutionApproach = 'Commit f8de0f5a0 hat dies bereits umgesetzt. Threads koennen geschlossen werden.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    11 = @{
        Summary = 'SerilogConfigurationTests.cs Zeile 67: Magic String im Test-Logger.'
        EstimatedTime = '30min'
        Complexity = 'M'
        AffectedFiles = @('SerilogConfigurationTests.cs')
        SolutionApproach = 'Magic Strings in Konstanten auslagern, Logger-Disposal verbessern.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    12 = @{
        Summary = 'ContainerIntegrationTestBase: Docker Image Name, Ports, Timeouts in appsettings.json auslagern.'
        EstimatedTime = '30min'
        Complexity = 'M'
        AffectedFiles = @('ContainerIntegrationTestBase.cs', 'appsettings.json')
        SolutionApproach = 'Neue TestConfiguration Section in appsettings.json, IConfiguration laden.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    13 = @{
        Summary = 'ServerConfig.cs: Basis-URLs (SOAP localhost:5809, REST localhost:5808) in Konstanten.'
        EstimatedTime = '15min'
        Complexity = 'S'
        AffectedFiles = @('ServerConfig.cs')
        SolutionApproach = 'Zwei private const string Felder fuer SOAP und REST Base-URLs.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    15 = @{
        Summary = 'ManualTestRunner Program.cs: Serilog hardcoded, sollte via appsettings.json.'
        EstimatedTime = '30min'
        Complexity = 'M'
        AffectedFiles = @('Program.cs', 'ServerConfig.cs')
        SolutionApproach = 'appsettings.json erstellen, Serilog-Section hinzufuegen, IConfigurationBuilder nutzen.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
    16 = @{
        Summary = 'Log.Warning ist BEREITS KORREKT implementiert (Zeile 77, 90). KEINE AKTION NOETIG.'
        EstimatedTime = '0min'
        Complexity = 'S'
        AffectedFiles = @('Program.cs')
        SolutionApproach = 'Code verwendet bereits Log.Warning(). Thread bezieht sich auf aeltere Version.'
        AnalyzedAt = '2026-01-20T12:00:00Z'
    }
}

foreach ($group in $state.Groups) {
    if ($planningData.ContainsKey($group.Nr)) {
        $group | Add-Member -MemberType NoteProperty -Name 'Planning' -Value $planningData[$group.Nr] -Force
    }
}

$state | ConvertTo-Json -Depth 10 | Set-Content $stateFile -Encoding UTF8
Write-Host "State-Datei aktualisiert mit Planning-Daten fuer 8 Gruppen" -ForegroundColor Green
