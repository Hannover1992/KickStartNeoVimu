# /stage Command

Gruppiere alle ge?nderten Dateien nach Fix-Typ und stage sie schrittweise.

## Phase 1: ?bersicht

1. F?hre `git status --short` aus um alle ge?nderten Dateien zu sehen
2. Gruppiere die Dateien nach Fix-Typ (z.B. "Constructor visibility", "Unused methods", etc.)
3. F?r jede Gruppe erkl?re:
   - **a) Was wurde gemacht:** Beschreibe die ?nderung
   - **b) Welche Dateien:** Liste alle Dateien dieser Gruppe
4. Frage: "Soll ich Gruppe X stagen? (ja/nein)"

## Phase 2: Staging (nur wenn JA)

1. F?hre NUR `git add` aus f?r die Dateien dieser Gruppe
2. **NICHT committen!**
3. Schlage Commit-Message vor im Format:
   ```
   $branch: $Title
   ```
   Beispiel: `DCSRE-1189: S3442 - Constructor visibility auf protected ge?ndert`

   **Keine Description, nur Titel!**

4. **Clipboard:** Kopiere die Commit-Message automatisch in die Zwischenablage:
   ```bash
   echo -n "$COMMIT_MESSAGE" | xclip -selection clipboard 2>/dev/null || echo -n "$COMMIT_MESSAGE" | clip.exe 2>/dev/null
   ```
   Danach kurz bestaetigen: `(in Clipboard kopiert)`


   Falsch Ausgabe Fur Phase 2:
    ● Phase 2: Commit-Message
    
      DCSRE-1189: S4136 - LINQ-Aufrufe vereinfacht (.Where().First/Single() → .First/Single(predicate))
    
      ---
      Welche Gruppe als nächstes? (3-8)
    
    ──────────────────────────────────────────

    Richtige Ausgabe Fur Phase 2:
    DCSRE-1189: S4136 - LINQ-Aufrufe vereinfacht (.Where().First/Single() → .First/Single(predicate))

    Falsche Ausgabe:
    ```
    DCSRE-1189: S4136 - LINQ-Aufrufe vereinfacht (.Where().First/Single()  .First/Single(predicate))
    ```

    Positive Ausgabe:
    DCSRE-1189: S4136 - LINQ-Aufrufe vereinfacht (.Where().First/Single()  .First/Single(predicate))

    Noch ein Beispiel:

    > Negativ:
    DCSRE-946: SA1609/SA1623 - Property-Dokumentation mit value-Tags und korrekten Präfixen (ManualTestRunner Models)
    
      ---
      Welche Gruppe als nächstes? (2-4)
    
    Positiv:
    
    DCSRE-946: SA1609/SA1623 - Property-Dokumentation mit value-Tags und korrekten Präfixen (ManualTestRunner Models)



## Regeln

- Eine Gruppe nach der anderen abarbeiten
- Warte auf Best?tigung bevor du stagst
- Nach dem Stagen einer Gruppe, frage nach der n?chsten
- Der User macht den Commit selbst
- In Phase 2: Gibst du Nur die Vorgeschlagene Commit message. So das der user Deine Ausgabe 1 zu 1 copieren kann. 
- Der User sagt dir dann danach z.b Gruppe 2, und dann fange wieder von phase 1 , bzw den teil wo du dann sagt dise date gehor zu sammen wil , a b c und dann fra soll ich sit stage user sagt ja und wir sind wieder in phase 2 

