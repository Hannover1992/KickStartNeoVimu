---
type: satellite
---

Wir haben uns gerade ueber ein Dokument unterhalten. Gib mir den vollen Pfad dieses Dokuments.

## Vorgehen (BEIDE Schritte ausfuehren!)

### Schritt 1: In Clipboard kopieren
Verwende das Bash-Tool um den Pfad in die Zwischenablage zu kopieren:
```bash
echo -n "DER_VOLLE_PFAD" | xclip -selection clipboard 2>/dev/null || echo -n "DER_VOLLE_PFAD" | clip.exe 2>/dev/null
```

### Schritt 2: Pfad anzeigen
Gib den Pfad als reinen Text aus (fuer den User sichtbar):
- Keine Erklaerung, keine Formatierung, kein Code-Block, kein Markdown
- Verwende IMMER Anfuehrungszeichen um den Pfad
- Pfade mit .claude muessen EXAKT so ausgegeben werden - nichts weglassen
- NUR der Pfad, sonst NICHTS
- Danach kurz: `(in Clipboard kopiert)`

## Beispiel

Unterhaltung war ueber: ARCHITEKTEN-PRAESENTATION.md

Schritt 1 (Bash):
```bash
echo -n "/home/uczen/Projekt/.claude/analysis/ARCHITEKTEN-PRAESENTATION.md" | xclip -selection clipboard 2>/dev/null || echo -n "/home/uczen/Projekt/.claude/analysis/ARCHITEKTEN-PRAESENTATION.md" | clip.exe 2>/dev/null
```

Schritt 2 (Textausgabe):
"/home/uczen/Projekt/.claude/analysis/ARCHITEKTEN-PRAESENTATION.md" (in Clipboard kopiert)

## Jetzt ausfuehren

Ermittle das zuletzt besprochene Dokument und fuehre BEIDE Schritte aus.
