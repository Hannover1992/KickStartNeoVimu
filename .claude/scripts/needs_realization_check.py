"""
needs_realization_check.py — BL-383 batch_PL5 (AK-3): Pattern-Realization-Check.

HEUTE inkrementiert Pattern-Konsum nur `usage++` (Treffer-Zaehlung, F4). NACH BL-383
traegt jeder PatternLibrary-Treffer ein `needs_realization_check=true`-Flag, bis ein
AKTIVER Realization-Verify ihn auf `realized=true|false` aufloest. Ein Treffer mit
offenem Flag zaehlt NICHT als architektonischer Pluspunkt (Kern-Anti-These, F6/F7) —
das ist die INV-VEHIKEL-false-GREEN-Lehre (W-PRC-3) von der TDD-/Code-Ebene auf die
ARCHITEKTUR-Bewertung gehoben: "Pattern present != good" (Kazman).

Der aktive Verify prueft ZWEI Achsen (W-PRC-2):
  (a) Suitability         — passt das getroffene Pattern fuer den Kontext? (Kazman: dieselbe
                            Taktik wirkt je Realisierung +/-). URTEIL -> ROTE Zone (AK-8,
                            `_eval_berater_realizationverify`, workflow_zones rot). Hier kommt
                            es als pass|fail|None INPUT an (kein Urteil in diesem Script).
  (b) Instanziierungs-Ort — ist das Pattern an der korrekten `_project/{LAYER}`-Schicht-Grenze
                            instanziiert (die `_PostBatch_ArchConformance` ohnehin prueft)?
                            DETERMINISTISCH (code-naeher) — check_instantiation_site().
Beide gruen -> `realized=true`; sonst -> Realization-Risiko-Befund (risk_class=Realization,
eval_kind=pattern_realization, AK-4).

Scope batch_PL5 (AK-3): die FLAG-Mechanik (needs_realization_check-Setzen, "offener Treffer
!= Pluspunkt", `realized`-Aufloesung aus 2 Achsen) + der DETERMINISTISCHE Instanziierungs-
Ort-Schicht-Grenz-Check. Der Suitability-Verify SELBST (passt das Pattern?) ist
markdown_uncoverable (ROTE Zone, agentisch). KEIN Modus-Write (INV-MODUS-1), KEIN neuer
Truth-Node-Typ (W-DOM-1) — der Realization-Befund ist ein Gate-/Report-Record (eval_finding).

CLI: `py needs_realization_check.py <PatternLibrary/_index.md> [...]`  (read-only).
exit 0 = Lauf ok, 2 = Usage-Fehler.
"""

import re
import sys

import quality_model_wform as qmw

# Die kanonischen PatternLibrary-Layer (Libraries/PatternLibrary/_index.md). Ein Pattern
# ist erwartet unter `{VAULT_ROOT}/Libraries/PatternLibrary/_project/{LAYER}/*.md` (die
# Grenze, die _PostBatch_ArchConformance prueft, BL-154).
KNOWN_LAYERS = {"BERATER", "COMMANDS", "ORCHESTRATOR", "SCRIPTS", "META", "HOOKS"}

# `_project/{LAYER}/`-Pfad-Segment (die Schicht-Grenze). Greift den LAYER zwischen
# `_project/` und dem naechsten `/`.
_PROJECT_LAYER_RE = re.compile(r"_project[\\/]([A-Za-z0-9_]+)[\\/]")


# ── Flag-Mechanik (W-PRC-1): Treffer -> needs_realization_check=true (KEINE Auto-Gutschrift) ──

def new_pattern_hit(pattern_id, usage=0):
    """AK-3 (T-9): baut den Treffer-Record fuer einen frischen PatternLibrary-Treffer.
    Traegt `needs_realization_check=true` (offen) + `realized=None` NEBEN der bestehenden
    `usage`-Telemetrie (W-PRC-1: das Flag lebt neben dem Counter, aendert ihn nicht).
    Beide Achsen starten None (noch kein Verify). KEIN Modus-/Verbots-Feld (AK-9)."""
    return {
        "pattern_id": pattern_id,
        "usage": usage,                       # bestehende Telemetrie (unveraendert)
        "needs_realization_check": True,      # offen bis aktiver Verify
        "realized": None,                     # null=offen
        "realization_axes": {
            "suitability": None,              # Urteil (ROTE Zone, AK-8)
            "instantiation_site": None,       # Schicht-Grenze (code-naeher)
        },
    }


def _both_axes_pass(suitability, instantiation_site):
    """W-PRC-2: realized=true GENAU dann, wenn BEIDE Achsen explizit 'pass' sind.
    Eine fail -> realized=false; eine None/offen -> noch nicht entscheidbar (None)."""
    if suitability == "fail" or instantiation_site == "fail":
        return False
    if suitability == "pass" and instantiation_site == "pass":
        return True
    return None  # mind. eine Achse offen


def resolve_realization(hit, suitability=None, instantiation_site=None):
    """AK-3 (W-PRC-2): loest den needs_realization_check-Treffer mit dem 2-Achsen-Ergebnis auf.

    `suitability`/`instantiation_site` IN {"pass", "fail", None}:
      - beide "pass"            -> realized=True,  Flag geschlossen  (zaehlt als Pluspunkt)
      - mind. eine "fail"       -> realized=False, Flag geschlossen  (Realization-Risiko)
      - mind. eine None (offen) -> realized=None,  Flag BLEIBT OFFEN (keine Auto-Gutschrift)
    Liefert eine NEUE dict-Kopie (kein Mutieren des Inputs). KEIN Modus-Feld (AK-9)."""
    out = dict(hit)
    axes = dict(hit.get("realization_axes") or {})
    axes["suitability"] = suitability
    axes["instantiation_site"] = instantiation_site
    out["realization_axes"] = axes
    realized = _both_axes_pass(suitability, instantiation_site)
    out["realized"] = realized
    # Flag geschlossen NUR wenn der Verify ein Verdikt hat (True ODER False); offen sonst.
    out["needs_realization_check"] = (realized is None)
    return out


def counts_as_credit(hit):
    """AK-3 (Kern-Anti-These F6/F7): ein Treffer zaehlt NUR als architektonischer Pluspunkt,
    wenn er VOLL realisiert ist (realized is True). Offener Check ODER realized=False ->
    KEIN Pluspunkt. Das ist die Anti-false-GREEN-Klammer (kein stiller usage++ -> credit)."""
    return hit.get("realized") is True


# ── Instanziierungs-Ort-Schicht-Check (Achse b, deterministisch, `_project/{LAYER}`) ──

def _layer_of_path(instantiation_path):
    """Zieht den `_project/{LAYER}`-Layer aus einem Instanziierungs-Pfad. None, wenn der
    Pfad kein `_project/{LAYER}/`-Segment traegt (Ort nicht bestimmbar)."""
    if not instantiation_path:
        return None
    m = _PROJECT_LAYER_RE.search(str(instantiation_path))
    if not m:
        return None
    return m.group(1).upper()


def check_instantiation_site(pattern_layer, instantiation_path):
    """AK-3 (T-10, W-PRC-2 Achse b): deterministischer Schicht-Grenz-Abgleich.

    -> "pass"  wenn der Instanziierungs-Pfad in der ERWARTETEN `_project/{LAYER}`-Schicht
               des Patterns liegt.
    -> "fail"  wenn er in einer ANDEREN (bekannten) `_project/{LAYER}`-Schicht liegt
               (Grenz-Verletzung — der code-nahe Realization-Risiko-Teil).
    -> None    wenn der Ort nicht bestimmbar ist (kein _project/{LAYER}-Pfad) -> faellt auf
               den Urteils-Pfad zurueck (KEIN false-fail, Graceful)."""
    if not pattern_layer:
        return None
    found = _layer_of_path(instantiation_path)
    if found is None:
        return None
    return "pass" if found == str(pattern_layer).strip().upper() else "fail"


# ── Realization-Risiko-Befund = pattern_realization eval_finding (AK-4-Interop) ──

def _finding(bl_slug, idx, pattern_id, severity, befund, cost, benefit, suggested_action):
    """Baut EINEN eval_finding-Record (PL1-Schema, eval_kind=pattern_realization,
    risk_class=Realization). Traegt KEIN Modus-/Verbots-Feld (INV-MODUS-5) und KEINEN
    metric/threshold-Bezug (pattern_realization ist von der AK-7-Klammer exempt)."""
    return {
        "finding_id": "%s.EF-%d" % (bl_slug, idx),
        "eval_kind": "pattern_realization",
        "ref_node": pattern_id,
        "risk_class": "Realization",
        "severity": severity,
        "befund": befund,
        "cost": cost,
        "benefit": benefit,
        "suggested_action": suggested_action,
        "status": "offen",
    }


def realization_findings(hits, bl_slug="BL-383"):
    """AK-3: erzeugt Realization-Risiko-Befunde fuer alle Treffer, die NICHT voll realisiert
    sind. Drei Faelle erzeugen einen Befund (Anti-false-GREEN — kein stiller Durchlass):
      - realized is False (eine Achse fail)      -> Realization-Befund (falsch realisiert)
      - needs_realization_check offen (kein Verify) -> Realization-Befund (ungeklaertes Risiko)
    Voll realisierte Treffer (realized is True) erzeugen KEINEN Befund.
    -> Liste PL1-schema-valider eval_finding-Records (leer = alle realisiert/keine Treffer)."""
    findings = []
    idx = 0
    for hit in hits:
        if counts_as_credit(hit):
            continue  # realized=True -> kein Risiko-Befund
        idx += 1
        pid = hit.get("pattern_id", "?")
        axes = hit.get("realization_axes") or {}
        if hit.get("realized") is False:
            # falsch realisiert: nenne die fehlgeschlagene(n) Achse(n).
            failed = [a for a in ("suitability", "instantiation_site") if axes.get(a) == "fail"]
            befund = ("Pattern-Treffer %s NICHT korrekt realisiert (Achse(n) fail: %s) — "
                      "Treffer zaehlt NICHT als Pluspunkt" % (pid, ", ".join(failed) or "?"))
            cost = "Pattern an %s korrigieren bzw. ersetzen (mittel)" % (", ".join(failed) or "?")
            benefit = "verhindert false-GREEN durch falsch realisiertes Pattern (Kazman)"
            action = "Realization von %s nachbessern (Suitability/Instanziierungs-Ort)" % pid
        else:
            # needs_realization_check noch offen -> ungeklaertes Realisierungs-Risiko.
            befund = ("Pattern-Treffer %s hat offenen needs_realization_check (kein aktiver "
                      "Realization-Verify) — zaehlt NICHT als architektonischer Pluspunkt" % pid)
            cost = "Realization-Verify (Suitability + Instanziierungs-Ort) durchfuehren (niedrig)"
            benefit = "schliesst Anti-false-GREEN-Luecke (Auto-Gutschrift verhindert)"
            action = "Realization-Verify fuer %s ausfuehren" % pid
        findings.append(_finding(bl_slug, idx, pid, "mittel", befund, cost, benefit, action))
    return findings


def render_findings_as_w_blocks(findings):
    """Rendert pattern_realization-Befunde als `### W{n}`-Gold-Form-Bloecke (eval_finding-
    Subtyp), sodass der `quality_model_wform.py`-Validator sie als gold prueft (Interop-
    Beweis AK-3 x AK-4). Nur die Schema-Felder werden in den eval_finding:-Block geschrieben."""
    schema_keys = qmw.EVAL_FINDING_FIELDS
    parts = []
    for f in findings:
        fid = f["finding_id"]
        lines = [
            "### W-%s · Pattern-Realization-Befund %s" % (fid.replace(".", "-"), f["ref_node"]),
            "- **text:** Pattern-Realization-Befund fuer %s (%s)." % (f["ref_node"], f["risk_class"]),
            "- **Status:** TENTATIV",
            "- **source:** `Repo: needs_realization_check.py gate-script run`",
            "- **Quelle:** `[[3_Spec/BL-383_Spec.md#AK-3]]`",
            "- **Edge zu:** W-PRC-1",
            "- **type:** eval_finding",
            "- **id:** `%s`" % fid,
            "- **eval_finding:**",
        ]
        for k in schema_keys:
            if k in f:
                lines.append("    - %s: %s" % (k, f[k]))
        parts.append("\n".join(lines) + "\n")
    return "".join(parts)


# ── CLI (read-only: liest den PatternLibrary-Index, listet Treffer + Flag-Status) ──

def _index_pattern_ids(content):
    """Zieht die PT-IDs (z.B. PT-META-001) aus einer PatternLibrary-Index-/Layer-Datei.
    Read-only Heuristik (Markdown-Tabelle/Liste) — keine Vault-Schreibung."""
    return sorted(set(re.findall(r"\bPT-[A-Z]+-\d+\b", content)))


def _print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def main(argv):
    if not argv:
        print("usage: needs_realization_check.py <PatternLibrary/_index.md> [...]")
        return 2
    for path in argv:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            _print("[FEHLER] {}: {}".format(path, exc))
            return 2
        pids = _index_pattern_ids(content)
        if not pids:
            _print("[GRACEFUL] {}: 0 Pattern-IDs gefunden -> kein Realization-Check".format(path))
            continue
        hits = [new_pattern_hit(pid) for pid in pids]
        findings = realization_findings(hits, bl_slug="BL-383")
        _print("[REALIZATION-CHECK] {}: {} Treffer, alle needs_realization_check=true "
               "(offen, kein Auto-Pluspunkt), {} Befund(e)".format(path, len(hits), len(findings)))
        for f in findings:
            _print("    {}: {} — {}".format(f["risk_class"], f["ref_node"], f["befund"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
