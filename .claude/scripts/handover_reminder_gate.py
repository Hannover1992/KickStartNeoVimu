#!/usr/bin/env python3
"""Handschuhwechsel-Reminder Modus-Gate (BL-227 Sub-Batch C-3, AK-9/AK-10).

modus_gate(modus, toggle) -> reminder_action  (rein, NUR-LESEND, INV-MODUS-1 Read-Only).

Die Funktion liest ausschliesslich den uebergebenen Modus + Toggle und gibt zurueck,
ob der Handschuhwechsel-Reminder (Phase-3-Handover, INV-HANDOVER-1 / INV-MODUS-7)
feuern soll. Sie schreibt NICHTS in DF_BATCH_STATE.modus (INV-MODUS-1 bleibt
gewahrt: nur _SDF_berater_modusEntscheidung setzt den Modus).

INVARIANTE "Reminder != Enforcement" (AK-12): Keine Block-Faehigkeit, kein State-
Change-Veto. Nur Entscheidung (rein/read-only). Enforcement bleibt ausschliesslich
bei den Hooks geist9/geist9b. Zuverlaessigkeits-Ranking: Motor > Hook > Reminder.

Gate-Logik (AK-9):

  1. toggle (step_adherence_reminder) ist Master-Voraussetzung:
       toggle="off" (oder None/falsy) -> "no-fire" fuer JEDEN Modus, kein Logging,
       kein weiteres Gating.

  2. toggle="on" -> Modus-Gate greift:

     Modus-Gate-Matrix:
       M1 -> "no-fire"    Skelett-Modus ohne Phase-3-Gating -> Reminder aus.
                          (Geschwindigkeit zaehlt, kein Phase-3-Overhead)
       M2 -> "optional"   Coverage-/Teil-Gating -> Reminder optional/konfigurierbar.
                          (M2-WARNING-Aufloesung: M2 faellt weder unter "MUSS feuern"
                          noch unter "DARF NICHT feuern" — die Entscheidung liegt
                          beim Aufrufer via Kontext. Default-Verhalten: feuert
                          vorsichtshalber (konservative Variante), aber mit niedrigerer
                          Prio als M3. Der Aufrufer (C-4-Hook) KANN bei M2 auf
                          "no-fire" downgraden, wenn motorisiert oder im schnellen
                          Durchlauf. AK-9 formuliert: "gemaess konfiguriertem M2-
                          Verhalten" — das Gate liefert "optional" als Signal.)
       M3 -> "fire"       KRITISCHER Hauptfall. DCSRE-486 19->4-Step-Skip-Beleg:
                          M3 = ~19 Steps (TDD/System-Aufbau), wo der Skip am
                          meisten schadet (AK-10 Kern-Ziel-Anker).
       Mx (unbekannt) -> "no-fire"   Fail-Safe: unbekannte Modi nicht feuern
                          (M4..M9 nicht spezifiziert in v1.0; Erweiterung via
                          _GATE_MATRIX ohne Interface-Bruch moeglich).

AK-10 Kern-Ziel-Anker: "Wenn M3 entschieden ist, MUSS es durchgezogen werden —
nicht uebersprungen." Der modus-entschiedene Step-Skeleton ist verbindlich, nicht
wegoptimierbar. Beleg: DCSRE-486 Round-17 19->4-Step-Skip. Der Reminder erinnert
den Team Lead daran VOR dem geist9b-Gate.
"""

# AK-9 Modus-Gate-Matrix (erweiterbar, M4+ via Eintrag moeglich).
# Unbekannte Eintraege: Fail-Safe "no-fire" (kein KeyError, keine Ausnahme).
_GATE_MATRIX = {
    "M1": "no-fire",
    "M2": "optional",
    "M3": "fire",
}


def modus_gate(modus, toggle="off"):
    """Entscheide ob der Reminder feuern soll (rein, read-only, kein Block-Pfad).

    Args:
        modus:  Aktueller Batch-Modus (str, z.B. "M1"/"M2"/"M3"). Wird NUR gelesen,
                nie geschrieben (INV-MODUS-1). Unbekannte Werte -> "no-fire" (Fail-Safe).
        toggle: Wert des session_params `step_adherence_reminder` (str "on"/"off"
                oder None/bool-aehnlich). toggle != "on" -> immer "no-fire", kein
                weiteres Gating (Master-Voraussetzung, AK-5/AK-9).

    Returns:
        str: "fire"     — Reminder soll feuern (M3 + toggle=on).
             "optional" — Reminder ist optional (M2 + toggle=on); Aufrufer entscheidet.
             "no-fire"  — Reminder feuert nicht (M1, unbekannter Modus, oder toggle off).

    INVARIANTE: kein Block-/Abort-/Veto-Pfad (AK-12). Read-only.
    """
    # Master-Gate: toggle muss explizit "on" sein.
    if toggle != "on":
        return "no-fire"

    # Modus-Gate: Fail-Safe fuer unbekannte Modi (M4..M9 etc.)
    return _GATE_MATRIX.get(modus, "no-fire")
