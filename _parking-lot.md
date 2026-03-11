# Parking Lot — KickStartNeoVim

## 2026-03-04 — Von /_SC_modelMaintain (out-of-cycle)

- [ ] **Debloat: KickStartNeoVim_Model.md**
  - **Beschreibung:** Model hat 588 Zeilen (≥500). SOFT-Trigger. User entschied: später.
  - **Priorität:** MITTEL
  - **Aktion:** `/_D_orchestrate KickStartNeoVim` ausführen wenn Zeit vorhanden.

## 2026-03-08 — Manuell (Feature-Idee)

- [ ] **rT* Test-Stufen-System (5 Stufen)**
  - **Beschreibung:** Universelles Test-Stufen-Konzept: Unit→Integration→IsolatedDocker→BlazorSystem→E2E. Keybindings: `<leader>rTS` (Stage setzen), `rTr` (Run), `rTs` (Search/Telescope), `rTf` (Failed re-run). Zustand wird gespeichert, TRX-Infrastruktur auf alle 5 Stufen ausweiten. Preconditions pro Stage (Docker-Rebuild etc.) automatisch prüfen.
  - **Priorität:** MITTEL
  - **TC-Nähe:** Keybindings / Test-Infrastruktur
  - **Kontext:** CenCoCo README.md (`tests/README.md`) hat die 5 Stufen + PowerShell-Befehle fertig definiert. DCSRE-Mapping noch offen. Konzept steht, noch nicht getestet/implementiert.
  - **Quelle:** User-Idee, Voice-Transkript 2026-03-08
