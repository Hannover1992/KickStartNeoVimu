# /_fork — Session als abgezapfter Branch markieren (kein Compact, kein Clear)

```yaml
status: active
version: 1.0.0
created: 2026-07-01
type: satellite
chain_position: standalone
team_based: false
```

## Zweck

Eine Session ist manchmal faktisch der Fortsatz/Abzweig einer anderen (noch laufenden oder gerade
unterbrochenen) Session — z.B. weil der zugrundeliegende Claude-Code-Prozess neu gestartet wurde und
diese Session mit dem alten Transkript weiterlaeuft, oder weil der User bewusst einen zweiten
Terminal/Kontext aus demselben Gespraech abzweigt. `/_fork` markiert diese Session EXPLIZIT als
**Fork/Beobachter, NICHT als aktiven Treiber** — ohne den Kontext zu verlieren und ohne die Kosten
eines vollen Re-Reads.

**Live-Anlass (2026-07-01):** waehrend einer laufenden BL-493-A-Pipeline (sequenzielle
Worker-Kette) kam eine Task-Notification "previous Claude Code process exited" — ein Hinweis, dass
die Session-Kontinuitaet unterbrochen war. Der User wollte NICHT, dass automatisch weitere Worker
nachgeschossen werden (moegliche Doppel-Treiber-Kollision mit einer parallel laufenden Haupt-Session
auf demselben Manifest), aber auch KEIN `/compact` (zu langsam) oder `/clear` (zu viel Infoverlust,
User muesste den Stand erneut erklaeren).

**Alternative zu:**
- `/compact` — komprimiert Kontext, aber dauert (Re-Zusammenfassung) — zu langsam wenn schnell
  weitergemacht werden soll.
- `/clear` — verliert den Kontext komplett, erzwingt erneute Erklaerung durch den User, was gerade
  lief.

`/_fork` behaelt den GESAMTEN bisherigen Kontext als informativ/Hintergrund — aendert aber das
**Verhalten**: kein automatisches Fortsetzen/Wiederaufnehmen einer zuvor laufenden Mehrschritt-
Operation (z.B. eine Pipeline-Worker-Kette) NUR weil eine Task-Notification eintrifft oder der
Kontext es hergibt.

## Aufruf

```
/_fork
```

Keine Argumente.

## Verhalten NACH /_fork

1. **Kein Auto-Continue:** laufende/angekuendigte Hintergrund-Worker dieser Session werden NICHT
   automatisch fortgesetzt oder erneut gespawnt, nur weil eine `<task-notification>` eintrifft. Der
   Lead wartet auf eine EXPLIZITE naechste Anweisung des Users, bevor er die naechste Phase/den
   naechsten Worker startet.
2. **Kein Kontext-Verlust:** der bisherige Gespraechs-Kontext bleibt vollstaendig nutzbar (anders als
   `/clear`) — der Lead darf ihn weiterhin als Wissensbasis fuer Fragen/Entscheidungen heranziehen,
   nur eben nicht als Trigger fuer automatisches Fortfahren.
3. **Kein Vault-/Manifest-Write durch `/_fork` selbst** — rein Session-lokale Verhaltensaenderung.
   Explizit KEIN State-Marker im Vault/Manifest, weil das mit einer parallel laufenden "Haupt"-
   Session auf demselben BL/Manifest kollidieren koennte (Split-Brain-Risiko, INV-FORK-1).
4. Der Lead bestaetigt kurz in 1 Satz: *"Fork markiert — ich fahre nichts automatisch weiter, sag
   mir wie's weitergeht."*

## Invarianten

- **INV-FORK-1:** `/_fork` schreibt NIEMALS in Vault/Manifest (reines Session-Verhalten, kein
  persistenter State — verhindert Kollision mit parallelen Sessions auf demselben Artefakt).
- **INV-FORK-2:** `/_fork` ist NICHT teuer wie `/compact` — kein Re-Read, kein Re-Summarize, quasi
  kostenlos.
- **INV-FORK-3:** Nach `/_fork` gilt *"Explizite Anweisung vor Auto-Continue"*, bis entweder ein
  neues `/clear`/`/compact` erfolgt ODER der User eine neue explizite Mehrschritt-Beauftragung gibt
  (z.B. "mach jetzt weiter mit Phase X").
- **INV-FORK-4:** `/_fork` unterbricht KEINE bereits laufenden (Background-)Agenten — es unterdrueckt
  nur das automatische *Anschliessen weiterer* Schritte durch den Lead. Bereits gestartete Worker
  laufen zu Ende und melden sich regulaer per Notification; der Lead nimmt das Ergebnis nur zur
  Kenntnis, ohne selbststaendig den naechsten Schritt zu starten.

## Verwandt

- `/compact`, `/clear` — Alternativen mit anderem Kosten/Kontext-Trade-off.
