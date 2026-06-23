# Parking Lot — KickStartNeoVim

## 2026-03-04 — Von /_SC_modelMaintain (out-of-cycle)

- [ ] **Debloat: KickStartNeoVim_Model.md**
  - **Beschreibung:** Model hat 588 Zeilen (≥500). SOFT-Trigger. User entschied: später.
  - **Priorität:** MITTEL
  - **Aktion:** `/_D_orchestrate KickStartNeoVim` ausführen wenn Zeit vorhanden.

## 2026-03-08 — Manuell (Feature-Idee)

- [x] **rT* Test-Stufen-System (5 Stufen)** — IMPLEMENTIERT 2026-03-14
  - **Beschreibung:** Project-aware rT1-rT5 + rTR/rTF/rTS mit TRX-Infrastruktur. Beide Projekte gemappt.
  - **Status:** Aufgenommen und umgesetzt. Alte ri*/re* als [DEPRECATED] Fallback.
  - **DCSRE:** rT1=BE Unit, rT2=FE Unit(Jest), rT3=IntMock(38T), rT4=IntDB(8T), rT5=E2E(Cypress)
  - **CenCoCo:** rT1=Unit, rT2=Integration, rT3=IsolatedDocker, rT4=BlazorSystem, rT5=E2E(Playwright)
  - **TRX:** rt-latest.trx (getrennt von altem it-latest.trx), rTR=Retry, rTF=Failed, rTS=Search
  - **Offen:** rT6 (alle Stufen sequentiell mit Cold Start) — siehe neuer Eintrag unten

## 2026-03-14 — Manuell (Feature-Ideen aus rT*-Implementierung)

- [ ] **rT6: Alle Stufen sequentiell (Cold Start)**
  - **Beschreibung:** Ein Befehl der rT1→rT2→rT3→rT4→rT5 nacheinander ausfuehrt. Stoppt bei Fehler. Optionaler Cold Start (Docker Reset + Image Rebuild vor Stufe 3+). Project-aware.
  - **Priorität:** MITTEL
  - **TC-Nähe:** Keybindings / Test-Infrastruktur
  - **Quelle:** User-Idee, 2026-03-14 (waehrend rT*-Implementierung)
