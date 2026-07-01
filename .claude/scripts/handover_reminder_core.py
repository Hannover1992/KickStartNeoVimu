#!/usr/bin/env python3
"""Handschuhwechsel-Reminder Kern (BL-227 Sub-Batch C-1, AK-1/AK-2/AK-3).

Kern-Ziel-Anker (AK-10): "Wenn M3 entschieden ist, MUSS es durchgezogen werden —
nicht uebersprungen." Der modus-entschiedene Step-Skeleton ist verbindlich, nicht
wegoptimierbar. Beleg: DCSRE-486 Round-17 19->4-Step-Skip (der Mega-Worker liess
15 Pflicht-Schritte aus). Diese Praeventions-Schicht (L3) erinnert den Team Lead
an den naechsten Pflicht-Schritt VOR dem Gate — sie ersetzt aber NICHT geist9/9b.

INVARIANTE "Reminder != Enforcement" (AK-12): Dieser Kern hat KEINEN Block-,
Abort- oder Veto-Pfad. Er baut nur Text (read+build-only). Enforcement bleibt
AUSSCHLIESSLICH bei den Hooks geist9/geist9b (Default-BLOCK am State-Gate).
Zuverlaessigkeits-Ranking (einstimmig): Motor (BL-222) > Hook (geist9) > Reminder.

build_reminder(target_orchestrator, next_step, handoff_block) -> str

AK-1  Der Kern existiert + ist als Berater-Kern aufrufbar; er erzeugt die Injektion,
      die als ERSTER Schritt nach einem nicht-motorisierten Handoff gefeuert wird
      (Verdrahtung/Trigger = C-4-Hook, Scope = C-4, Param-Gate = C-2, Modus-Gate = C-3).
AK-2  Progressive Disclosure: NUR der naechste Pflicht-Schritt (k+1) + dessen
      Delegations-Vertrag, NICHT die volle ~19er-Liste (die erzeugt selbst Context-Rot).
AK-3  Format: XML-schema-getaggt, durchnummerierte Step-ID, ACK-pflichtig, KEINE
      Prosa (Opus 4.8 folgt literaler/strukturierter Instruktion). Platzierung:
      Recency + Sandwiching — der Step erscheint vor UND nach dem Handoff-Datenblock.
"""
from xml.sax.saxutils import escape


def _render_step_block(target_orchestrator, next_step):
    """Baue EINEN <step-reminder>-Block (AK-3: XML-getaggt, nummeriert, ACK, kein Prosa).

    Genau 1 Step (k+1) — AK-2 Progressive Disclosure. Vertrag (objective/output-format/
    boundaries) in getaggten Feldern, nicht als Freitext-Prosa.
    """
    step_id = escape(str(next_step["id"]))
    return (
        f'<step-reminder target="{escape(target_orchestrator)}" step-id="{step_id}">'
        f"<name>{escape(str(next_step.get('name', '')))}</name>"
        f"<objective>{escape(str(next_step.get('objective', '')))}</objective>"
        f"<output-format>{escape(str(next_step.get('output_format', '')))}</output-format>"
        f"<boundaries>{escape(str(next_step.get('boundaries', '')))}</boundaries>"
        f'<ack required="true">Quittiere Schritt {step_id} durch Ausfuehrung.</ack>'
        f"</step-reminder>"
    )


def build_reminder(target_orchestrator, next_step, handoff_block):
    """Baue die sandwiched Progressive-Disclosure-Injektion fuer den naechsten Step.

    Read+build-only (AK-12: kein Block-Pfad). Der gleiche 1-Step-Block (AK-2) wird
    VOR und NACH dem Handoff-Datenblock wiederholt (AK-3 Sandwiching: Recency +
    Lost-in-the-Middle-Gegenmittel).
    """
    block = _render_step_block(target_orchestrator, next_step)
    return f"{block}\n{handoff_block}\n{block}"
