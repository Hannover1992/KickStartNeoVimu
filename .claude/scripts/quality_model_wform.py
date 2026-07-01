"""
quality_model_wform.py — BL-243 AK-S3: Gold-Form-Validator fuer W{n}-Knoten.

Macht die Truth-Atomic-First-Konvention (BL-243 AK-S1, _model.md Model-
Qualitaetskriterien) ERZWINGBAR. Ein W{n}-Knoten ist „gold", wenn er die
kanonische atomare Form traegt — NICHT Prosa/Flowchart-statt-Text:

    ### W-{LAYER}-{N} · {atomarer Titel}
    - **text:**   {einzeiliger Wahrheits-Satz}
    - **Status:** {kanonischer Wert BL-205}        (auch inline mit Typ/Herkunft)
    - **source:** {Quelle mit INTERN/EXTERN-Prefix}
    - **Quelle:** {>=1 `[[Wikilink]]`}
    - **Edge zu:** {>=1 W{n}/Source-Ref}

Vorbild: BL-161 quality_*-Familie. CLI: `py quality_model_wform.py <Model.md> [...]`
exit 0 = alle gold, 1 = Violations/Prosa-Model, 2 = Usage-Fehler.
"""

import re
import sys

# Kanonische W{n}-Pflicht-Felder (Truth-Atomic-First, _model.md Z495-500 / BL-243).
GOLD_FIELDS = ["text", "Status", "source", "Quelle", "Edge zu"]

# --- BL-380 B1/AK-1: quality_scenario-Knoten (ADDITIVER Subtyp auf BL-243-Substrat) ---
# Greift NUR wenn der W-Block `type: quality_scenario` traegt; sonst unberuehrt (kein Breaking).
# Die 6 iSAQB-Felder unter dem `scenario:`-Block (W-DOM-2).
SCENARIO_ISAQB_FIELDS = [
    "source", "stimulus", "artifact", "environment", "response", "response_measure",
]
# Das response_measure-Pflicht-Triple (W-DOM-3); `method` = Goodhart-Guard (W-GH-1 / AK-6).
RESPONSE_MEASURE_FIELDS = ["metric", "threshold", "method"]
# Pflicht-Kanten (W-DOM-1): UP zum Qualitaetsziel-Node (§1.2), DOWN zum Endpunkt.
SCENARIO_EDGE_FIELDS = ["endpoint_type", "endpoint_ref", "qualitaetsziel_ref"]
# Erlaubte endpoint_type-Werte (W-RM-1).
SCENARIO_ENDPOINT_TYPES = {"metric_component", "ak_test"}

# --- BL-382 AK-1/AK-5/AK-6: type:adr-Knoten (ADDITIVER Subtyp auf BL-243-Substrat) ---
# Strukturelle Schwester des quality_scenario-Zweigs. Greift NUR wenn der W-Block
# `type: adr` traegt; sonst unberuehrt (kein Breaking).
# Die 6 Nygard-Felder unter dem `adr:`-Block (W-DOM-2, AK-1).
ADR_NYGARD_FIELDS = [
    "entscheidung", "problem_kontext", "alternativen",
    "begruendung", "konsequenzen", "status",
]
# Geschlossenes Status-Enum (W-STAT-1, AK-5) — FACHLICHER Entscheidungs-Lebenszyklus.
# ORTHOGONAL zu CANONICAL_STATUS (Gold-Form epistemisch); adr.status wird NIE gegen
# CANONICAL_STATUS geprueft (W-VAL-3, Namens-Kollisions-Schutz).
ADR_STATUS_ENUM = {"vorgeschlagen", "akzeptiert", "superseded", "konflikt-offen"}

# --- BL-382 AK-3: drei explizite Graph-Kanten im adr:-Block (Felder, KEINE Prosa) ---
# betrifft_baustein[] (nach UNTEN §5), superseded_by (ADR->ADR-Abloesung), abhaengig_von[]
# (ADR->ADR-Abhaengigkeit). ID-Format der gerichteten ADR->ADR-Kanten: {BL-SLUG}.ADR-{n}
# (BL-309-lokales Praefix, W-DOM-4). additiv — betrifft_baustein bleibt Default-Pflicht-MIT-
# Luecken-Marker (B-3), wird hier NICHT als Hard-Pflicht erzwungen (vor-Bausteinsicht-ADRs).
# Nur PRAESENTE superseded_by/abhaengig_von-Werte werden gegen das ID-Format geprueft.
ADR_EDGE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*\.ADR-\d+$")

# --- BL-383 batch_PL1 (AK-4): type:eval_finding-Knoten (ADDITIVER Subtyp auf BL-243-Substrat) ---
# Strukturelle Schwester des quality_scenario- + adr-Zweigs. Greift NUR wenn der W-Block
# `type: eval_finding` traegt; sonst unberuehrt (kein Breaking). Das Eval-Gate (BL-383) ist ein
# Bewertungs-KONSUMENT der BL-380/382-Nodes — KEIN neuer Vault-Truth-Node, sondern ein Gate-/
# Report-Record (W-DOM-1). Der Record traegt Kazman-Playbook-Issue-Form (W-DOM-3).
# Die Pflicht-Felder unter dem `eval_finding:`-Block (W-DOM-3 / AK-4).
EVAL_FINDING_FIELDS = [
    "finding_id", "eval_kind", "ref_node", "risk_class", "severity",
    "befund", "cost", "benefit", "suggested_action", "status",
]
# Geschlossenes risk_class-Enum: die GENAU 4 Kazman-Klassen (W-OUT-1, AK-4). Freie Strings
# verboten (analog ADR_STATUS_ENUM). Case-sensitiv (Title-Case, wie Kazman SEI-TR 2020).
RISK_CLASS_ENUM = {"Omission", "Commission", "Realization", "Managerial"}
# Geschlossenes eval_kind-Enum (3 Werte, AK-4): welcher der drei Eval-Mechanismen den Befund erzeugte.
EVAL_KIND_ENUM = {"design_eval", "drift_eval", "pattern_realization"}
# Verbotene binaere PASS/FAIL-Primaer-Felder (W-OUT-3, AK-4 Kern-Anti-These): das Gate liefert
# eine Risiko-Befund-Liste, NIE ein binaeres Verdikt als Primaer-Output. Ein abgeleitetes GO/NO-GO
# (Sekundaer, SOA-3) ist davon unberuehrt — diese Felder am eval_finding-RECORD sind die Verletzung.
EVAL_FINDING_FORBIDDEN_PASSFAIL = ["pass_fail", "passfail", "verdict", "pass/fail"]
# Die nicht-leer-pflichtigen String-Felder (Aktionierbarkeit, W-OUT-2): cost UND benefit
# muessen einen echten Wert tragen (nicht blank/`""`), sonst ist der Befund nicht priorisierbar.
EVAL_FINDING_NONEMPTY_FIELDS = ["cost", "benefit"]
# --- BL-383 batch_PL2 (AK-7): Messbarkeits-Klammer (goldDefine-Prinzip). ---
# Ein design_eval-Befund bewertet eine Szenario-Abdeckung gegen das BL-380
# response_measure{metric, threshold}. Er MUSS einen messbaren Bezug tragen — `metric`
# UND `threshold` — sonst ist die Abdeckungs-Bewertung Bauchgefuehl ("gut genug" statt
# "messbar"). Strukturell-Spiegel von BL-380 W-GH-1 (response_measure.method-Pflichtfeld):
# dort schuetzt `method` gegen Goodhart-Gaming des threshold, hier zwingt `metric`+`threshold`
# die Design-Seite gegen false-GREEN ("abgedeckt" ohne mess-Bezug). Greift typ-konditional
# NUR fuer eval_kind: design_eval — drift_eval/pattern_realization tragen KEINEN
# response_measure-Bezug (sie bewerten ADR-Widerspruch bzw. Pattern-Realisierung).
EVAL_FINDING_MEASURE_FIELDS = ["metric", "threshold"]
EVAL_FINDING_MEASURE_KIND = "design_eval"

# Kanonische Status-Werte (BL-205 AK-5, _model.md Z506-508).
CANONICAL_STATUS = {
    "BESTAETIGT", "BESTAETIGT-DB", "STABLE", "AKTIV", "RESOLVED", "RESOLVED-DB",
    "CLOSED", "TENTATIV", "HYPOTHESE", "OFFEN", "RETRACTED",
}

# '### W-DOM-1 ...' oder '### W1 ...' — Layer-Form (W-[A-Z]+-N) oder Legacy (W\d+).
_W_HEAD = re.compile(r"^###\s+(W-[A-Z]+-\d+|W\d+)\b(.*)$", re.M)
# Lockere W{n}-Erwaehnung (fuer Prosa-Model-Detektion).
_W_MENTION = re.compile(r"\bW-?[A-Za-z]*-?\d+\b")


def parse_w_blocks(content):
    """Findet '### W-...'-Headings -> Liste {w_id, title, body} (body bis zum
    naechsten '### W'-Heading bzw. EOF)."""
    blocks = []
    matches = list(_W_HEAD.finditer(content))
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        blocks.append({
            "w_id": m.group(1),
            "title": m.group(2).lstrip(" ·").strip(),
            "body": content[start:end],
        })
    return blocks


def _field_present(body, field):
    """'**{field}:**' vorhanden (case-insensitive, inline erlaubt)."""
    return bool(re.search(r"\*\*\s*" + re.escape(field) + r"\s*:\*\*", body, re.I))


def _status_value(body):
    m = re.search(r"\*\*\s*Status\s*:\*\*\s*([A-Za-z\-]+)", body, re.I)
    return m.group(1).upper() if m else None


def _quelle_has_wikilink(body):
    m = re.search(r"\*\*\s*Quelle\s*:\*\*([^\n]*)", body, re.I)
    return bool(m and "[[" in m.group(1))


def _key_present(body, key):
    """BL-380: Feld im Body vorhanden, egal ob Gold-Form-Bullet ('- **key:**') ODER
    YAML-indentierter Schluessel ('key:' / '  - key:'). Case-insensitive."""
    if _field_present(body, key):
        return True
    # YAML-Stil: optional Listen-Dash, dann 'key:' am (eingerueckten) Zeilen-Anfang.
    return bool(re.search(r"^\s*(?:-\s*)?" + re.escape(key) + r"\s*:", body, re.I | re.M))


def _is_quality_scenario(body):
    """True, wenn der W-Block 'type: quality_scenario' traegt (Bullet- ODER YAML-Form)."""
    return bool(re.search(
        r"(?:\*\*\s*type\s*:\*\*|^\s*(?:-\s*)?type\s*:)\s*[`\"']?quality_scenario\b",
        body, re.I | re.M,
    ))


def check_scenario_block(body):
    """BL-380 B1/AK-1: typ-konditionale Pruefung eines quality_scenario-Knotens.

    Erwartet (zusaetzlich zur Gold-Form-Basis):
      - 6 iSAQB-Felder unter `scenario:` (source/stimulus/artifact/environment/response/
        response_measure)
      - response_measure-Triple {metric, threshold, method}  (`method` = Goodhart-Guard)
      - 2 Pflicht-Kanten: qualitaetsziel_ref (UP), endpoint_type + endpoint_ref (DOWN)
      - endpoint_type IN {metric_component, ak_test}
    -> Liste fehlender/invalider Aspekte (leer = ok)."""
    missing = []
    for f in SCENARIO_ISAQB_FIELDS:
        if not _key_present(body, f):
            missing.append("scenario." + f)
    for f in RESPONSE_MEASURE_FIELDS:
        if not _key_present(body, f):
            missing.append("response_measure." + f)
    for f in SCENARIO_EDGE_FIELDS:
        if not _key_present(body, f):
            missing.append(f)
    # endpoint_type-Wert validieren (nur wenn das Feld ueberhaupt da ist).
    m = re.search(
        r"(?:\*\*\s*endpoint_type\s*:\*\*|^\s*(?:-\s*)?endpoint_type\s*:)\s*[`\"']?([A-Za-z_]+)",
        body, re.I | re.M,
    )
    if m and m.group(1).lower() not in SCENARIO_ENDPOINT_TYPES:
        missing.append("endpoint_type(invalid:%s)" % m.group(1))
    return missing


def _is_adr(body):
    """True, wenn der W-Block 'type: adr' traegt (Bullet- ODER YAML-Form).

    Strukturelle Schwester von _is_quality_scenario. Word-boundary nach 'adr',
    damit 'adresse'/'adr_x' o.ae. nicht faelschlich matchen."""
    return bool(re.search(
        r"(?:\*\*\s*type\s*:\*\*|^\s*(?:-\s*)?type\s*:)\s*[`\"']?adr\b",
        body, re.I | re.M,
    ))


def _adr_status_value(body):
    """Extrahiert den NESTED adr.status-Wert (unter dem `adr:`-Block) — die lowercase-
    `status:`-Zeile, NICHT der Gold-Form-Bullet `- **Status:**`. Gibt den Wert (lower)
    oder None zurueck. Trennung ist W-VAL-3 (orthogonale Status-Dimensionen)."""
    # YAML-indentiert: optionaler Listen-Dash, dann 'status:' (KEIN '**'-Markup).
    # Wert kann Bindestrich enthalten (z.B. konflikt-offen).
    m = re.search(r"^\s*(?:-\s*)?status\s*:\s*[`\"']?([A-Za-z\-]+)", body, re.M)
    return m.group(1).lower() if m else None


def _adr_edge_ids(body, edge_key):
    """Extrahiert die {BL-SLUG}.ADR-{n}-Tokens eines gerichteten ADR-Kanten-Felds
    (superseded_by / abhaengig_von) aus dem nested adr:-Block. Greift sowohl die
    Scalar-Form (`superseded_by: BL-382.ADR-2`) als auch die Inline-Listen-Form
    (`abhaengig_von: ["BL-382.ADR-3", "BL-382.ADR-4"]`). Leerwert/absent -> []."""
    m = re.search(
        r"^\s*(?:-\s*)?" + re.escape(edge_key) + r"\s*:\s*([^\n]*)",
        body, re.I | re.M,
    )
    if not m:
        return []
    raw = m.group(1).strip()
    if not raw or raw in ("[]", "~", "null", "None"):
        return []
    # Alle ADR-artigen Tokens aus dem Roh-Wert ziehen (Listen-Klammern/Quotes egal).
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9._-]*\.ADR-\d+|[^\s,\[\]\"'`]+", raw)


def _adr_scalar_nonempty(body, key):
    """BL-382 batch_PL6 (AK-6/B-3): True, wenn das nested adr.{key}-Skalar-Feld einen
    NICHT-LEEREN Wert traegt. Greift die Bullet- ODER YAML-indentierte Form; ein blanker
    Wert (''/Whitespace) ODER ein Leer-Marker (`[]`/`~`/`null`/`None`) zaehlt als LEER.
    Geht ueber `_key_present` (nur Anwesenheit) hinaus — die echte B-3-Inhalts-Pruefung."""
    # WICHTIG: [^\S\n]* (nur horizontaler Whitespace) nach dem Doppelpunkt — sonst frisst
    # \s* den Zeilenumbruch und greift faelschlich den Wert der NAECHSTEN Zeile (ein leeres
    # Feld wuerde so als nicht-leer durchgehen).
    m = re.search(
        r"(?:\*\*\s*" + re.escape(key) + r"\s*:\*\*|^\s*(?:-\s*)?" + re.escape(key) + r"\s*:)[^\S\n]*([^\n]*)",
        body, re.I | re.M,
    )
    if not m:
        return False
    val = m.group(1).strip()
    if val.startswith("`") and val.endswith("`") and len(val) >= 2:
        val = val[1:-1].strip()
    return bool(val) and val not in ("[]", "~", "null", "None", '""', "''")


def _adr_alternativen_nonempty(body):
    """BL-382 batch_PL6 (AK-6/B-3): True, wenn `adr.alternativen` mind. EINEN echten Eintrag
    hat (Nygards 'Warum nicht anders?'). Akzeptiert zwei valide Formen:
      (a) inline nicht-leerer Skalar/Liste (`alternativen: ["X"]`)  ODER
      (b) Block-Form mit mind. einem genesteten Listen-Eintrag (`- option: ...`).
    `alternativen: []` oder blanker Header OHNE genesteten Eintrag -> LEER (Violation)."""
    m = re.search(
        r"^([ \t]*)(?:-\s*)?alternativen\s*:[^\S\n]*([^\n]*)\n?",
        body, re.I | re.M,
    )
    if not m:
        return False
    indent, inline = m.group(1), m.group(2).strip()
    # (a) Inline-Wert vorhanden und nicht-leer (z.B. Inline-Liste oder Skalar).
    if inline and inline not in ("[]", "~", "null", "None"):
        return True
    # (b) Block-Form: mind. eine staerker eingerueckte Eintrags-Zeile unter dem Header.
    tail = body[m.end():]
    for line in tail.splitlines():
        if not line.strip():
            continue
        cur_indent = len(line) - len(line.lstrip(" \t"))
        if cur_indent <= len(indent):
            break  # zurueck auf/ueber Header-Ebene -> Block zu Ende, kein Eintrag.
        if line.strip().lstrip("- ").strip():
            return True
    return False


def check_adr_block(body):
    """BL-382 AK-1/AK-5/AK-6 + AK-3: typ-konditionale Pruefung eines type:adr-Knotens.

    Erwartet (zusaetzlich zur Gold-Form-Basis):
      - 6 Nygard-Felder unter `adr:` (entscheidung/problem_kontext/alternativen/
        begruendung/konsequenzen/status)  — AK-1
      - **Nicht-Leer-Inhaltspruefung (B-3, batch_PL6):** die String-Felder
        `entscheidung`/`problem_kontext`/`begruendung`/`konsequenzen` muessen NICHT-LEER
        sein (nicht blank/`""`); `alternativen` muss mind. EINEN Eintrag tragen (nicht `[]`).
        `begruendung` nicht-leer = strukturelle Haelfte des Goodhart-Guards (AK-4). Diese
        Pruefung geht ueber `_key_present` (nur Anwesenheit) hinaus.
      - `status` IN ADR_STATUS_ENUM (vorgeschlagen/akzeptiert/superseded/konflikt-offen),
        geprueft gegen das ADR-Enum, NIE gegen CANONICAL_STATUS  — AK-5 / W-VAL-3
      - Die gerichteten ADR->ADR-Kanten `superseded_by`/`abhaengig_von` (FALLS PRAESENT)
        tragen das ID-Format {BL-SLUG}.ADR-{n}  — AK-3
    -> Liste fehlender/invalider Aspekte (leer = ok).

    HINWEIS Scope: AK-3 deckt hier das ID-FORMAT praesenter Kanten ab (additiv);
    `betrifft_baustein` bleibt Default-Pflicht-MIT-Luecken-Marker (B-3) und wird NICHT hart
    erzwungen (vor-Bausteinsicht-ADRs tragen den `[ungegroundet: baustein?]`-Marker)."""
    missing = []
    for f in ADR_NYGARD_FIELDS:
        if not _key_present(body, f):
            missing.append("adr." + f)
    # B-3 (batch_PL6): Nicht-Leer-Inhaltspruefung der praesenten Pflichtfelder. NUR fuer Felder,
    # die ueberhaupt da sind (sonst doppelte Meldung) — `status` ist Enum-geprueft (unten), nicht
    # leer-geprueft. `alternativen` braucht mind. einen Eintrag; die uebrigen einen nicht-leeren Wert.
    for f in ("entscheidung", "problem_kontext", "begruendung", "konsequenzen"):
        if _key_present(body, f) and not _adr_scalar_nonempty(body, f):
            missing.append("adr.%s(empty)" % f)
    if _key_present(body, "alternativen") and not _adr_alternativen_nonempty(body):
        missing.append("adr.alternativen(empty)")
    # adr.status-Enum-Membership (nur wenn das nested status-Feld ueberhaupt da ist).
    # Gegen ADR_STATUS_ENUM, NICHT CANONICAL_STATUS (W-VAL-3 Orthogonalitaet).
    status_val = _adr_status_value(body)
    if status_val is not None and status_val not in ADR_STATUS_ENUM:
        missing.append("adr.status(invalid:%s)" % status_val)
    # AK-3: ID-Format praesenter gerichteter ADR->ADR-Kanten ({BL-SLUG}.ADR-{n}).
    # betrifft_baustein ist KEINE ADR->ADR-Kante (zeigt nach UNTEN auf §5) -> nicht ID-geprueft.
    for edge_key in ("superseded_by", "abhaengig_von"):
        for token in _adr_edge_ids(body, edge_key):
            if not ADR_EDGE_ID.match(token):
                missing.append("adr.%s(bad-id:%s)" % (edge_key, token))
    return missing


# --- BL-383 batch_PL1 / AK-4: type:eval_finding-Knoten-Pruefung (typ-konditional) ---


def _is_eval_finding(body):
    """True, wenn der W-Block 'type: eval_finding' traegt (Bullet- ODER YAML-Form).

    Strukturelle Schwester von _is_quality_scenario / _is_adr. Word-boundary nach
    'eval_finding', damit 'eval_finding_x' o.ae. nicht faelschlich matchen."""
    return bool(re.search(
        r"(?:\*\*\s*type\s*:\*\*|^\s*(?:-\s*)?type\s*:)\s*[`\"']?eval_finding\b",
        body, re.I | re.M,
    ))


def _eval_field_value(body, key):
    """Einzeiliger nested eval_finding.{key}-Skalar-Wert. Greift die Bullet- ODER YAML-
    indentierte Form; gibt den getrimmten Roh-Wert (Quotes/Backticks gestrippt) oder None.
    Nutzt [^\\S\\n]* (nur horizontaler Whitespace) damit ein leeres Feld nicht faelschlich
    den Wert der NAECHSTEN Zeile frisst (vgl. _adr_scalar_nonempty-Doku)."""
    m = re.search(
        r"(?:\*\*\s*" + re.escape(key) + r"\s*:\*\*|^\s*(?:-\s*)?" + re.escape(key) + r"\s*:)[^\S\n]*([^\n]*)",
        body, re.I | re.M,
    )
    if not m:
        return None
    val = m.group(1).strip()
    if val.startswith("`") and val.endswith("`") and len(val) >= 2:
        val = val[1:-1].strip()
    return val


def check_eval_finding_block(body):
    """BL-383 batch_PL1 / AK-4: typ-konditionale Pruefung eines type:eval_finding-Knotens.

    Erwartet (zusaetzlich zur Gold-Form-Basis):
      - 10 Pflicht-Schema-Felder unter `eval_finding:` (finding_id/eval_kind/ref_node/
        risk_class/severity/befund/cost/benefit/suggested_action/status)  — W-DOM-3
      - `risk_class` IN RISK_CLASS_ENUM (genau die 4 Kazman-Klassen Omission/Commission/
        Realization/Managerial; freier String -> Violation)  — W-OUT-1
      - `eval_kind` IN EVAL_KIND_ENUM (design_eval/drift_eval/pattern_realization)
      - **`cost` UND `benefit` NICHT-LEER** (Aktionierbarkeit, W-OUT-2) — nicht nur praesent
      - **KEIN binaeres PASS/FAIL als Primaer-Output** (pass_fail/verdict-Feld am Record
        -> Violation; das Gate liefert eine Risiko-Befund-Liste, NIE ein Verdikt)  — W-OUT-3
      - **Messbarkeits-Klammer (batch_PL2, AK-7):** ein `design_eval`-Befund MUSS `metric`
        UND `threshold` als messbaren Bezug tragen (goldDefine "messbar, nicht gut-genug";
        Spiegel BL-380 W-GH-1). Greift NUR fuer eval_kind: design_eval — drift_eval/
        pattern_realization sind exempt (kein response_measure-Bezug).
    -> Liste fehlender/invalider Aspekte (leer = ok).

    HINWEIS Scope: batch_PL1 deckt AK-4 (Schema/Enum/cost-benefit/no-PASS-FAIL); batch_PL2
    ergaenzt AK-7 (Messbarkeits-Klammer, design_eval-konditional). Das ref_node-ID-Format
    (AK-6), die Realization-Flag-Mechanik (AK-3) und der betrifft_baustein-Drift-Anker (AK-2)
    gehoeren NICHT hierher. Die Design-Eval-LOGIK selbst (Szenario-Lesen, endpoint_type-
    Routing, SOLL/IST-Vergleich, AK-1) lebt in `design_eval.py` (eigenes Script) — dieser
    Validator prueft nur die OUTPUT-FORM des design_eval-Befunds. risk_class wird
    case-sensitiv geprueft (Kazman-Title-Case); die forbidden-modus-Felder (INV-MODUS-5)
    deckt der Pre-Write-Hook (AK-9) ab, NICHT dieser Validator."""
    missing = []
    # 1) Schema-Vollstaendigkeit: alle Pflichtfelder vorhanden.
    for f in EVAL_FINDING_FIELDS:
        if not _key_present(body, f):
            missing.append("eval_finding." + f)
    # 2) risk_class IN Kazman-4-Enum (nur wenn das Feld ueberhaupt da ist; case-sensitiv).
    rc = _eval_field_value(body, "risk_class")
    if rc is not None and rc not in RISK_CLASS_ENUM:
        missing.append("eval_finding.risk_class(invalid:%s)" % rc)
    # 3) eval_kind IN 3-Enum (nur wenn praesent).
    ek = _eval_field_value(body, "eval_kind")
    if ek is not None and ek not in EVAL_KIND_ENUM:
        missing.append("eval_finding.eval_kind(invalid:%s)" % ek)
    # 4) cost/benefit NICHT-LEER (Aktionierbarkeit) — nur fuer praesente Felder (sonst
    #    doppelte Meldung mit Check 1). _adr_scalar_nonempty ist der generische Nicht-Leer-Helfer.
    for f in EVAL_FINDING_NONEMPTY_FIELDS:
        if _key_present(body, f) and not _adr_scalar_nonempty(body, f):
            missing.append("eval_finding.%s(empty)" % f)
    # 5) KEIN binaeres PASS/FAIL-Primaer-Feld am Record (W-OUT-3 Kern-Anti-These).
    for f in EVAL_FINDING_FORBIDDEN_PASSFAIL:
        if _key_present(body, f):
            missing.append("eval_finding.pass_fail-forbidden(%s)" % f)
    # 6) Messbarkeits-Klammer (batch_PL2, AK-7): ein design_eval-Befund MUSS metric+threshold
    #    als messbaren Bezug tragen (goldDefine "messbar, nicht gut-genug"). Typ-konditional —
    #    NUR fuer eval_kind: design_eval; drift_eval/pattern_realization sind exempt (kein
    #    response_measure-Bezug). Default-fail-open: fehlt das eval_kind-Feld, greift die
    #    Klammer NICHT (das ist schon ueber Check 1 als Schema-Luecke gemeldet).
    if ek == EVAL_FINDING_MEASURE_KIND:
        for f in EVAL_FINDING_MEASURE_FIELDS:
            if not _key_present(body, f):
                missing.append("eval_finding.%s(design_eval-measurability-AK7)" % f)
    return missing


# --- BL-382 batch_PL3 / AK-7 + AK-8: Cross-ADR-Konsistenz (mehrere adr-Knoten) ---
# AK-7 (superseded-Ketten-Konsistenz) und AK-8 Stufe-1 (deterministischer Konflikt-
# Vorfilter) sind CROSS-ADR-Checks: sie operieren NICHT auf einem einzelnen W-Block,
# sondern auf der NODE-LISTE eines ganzen Models. Daher eigene Funktionen
# (check_adr_superseded_chains / detect_adr_conflicts) statt einer check_adr_block-
# Erweiterung. Beide sind deterministisch + rein lesend (kein Producer-Write hier).
# Aktiver Status (W-STAT-4): ein ADR-Knoten ist "aktiv" wenn adr.status akzeptiert
# ODER vorgeschlagen ist; superseded/konflikt-offen sind nicht-aktiv.
ADR_ACTIVE_STATUS = {"akzeptiert", "vorgeschlagen"}


def _adr_node_id(body):
    """Eigene ADR-ID des Knotens aus `- **id:** {ID}` ODER YAML `id: {ID}`.
    Quotes/Backticks werden gestrippt. None wenn nicht vorhanden."""
    m = re.search(
        r"(?:\*\*\s*id\s*:\*\*|^\s*(?:-\s*)?id\s*:)\s*[`\"']?([A-Za-z0-9][A-Za-z0-9._-]*)",
        body, re.I | re.M,
    )
    return m.group(1) if m else None


def _adr_field_value(body, key):
    """Einzeiliger nested adr.{key}-Skalar-Wert (z.B. entscheidung/betrifft_baustein-roh).
    Greift die Bullet- ODER YAML-indentierte Form; gibt den getrimmten Roh-Wert oder None.
    Fuer Listen-/ID-Kanten -> _adr_edge_ids verwenden."""
    m = re.search(
        r"(?:\*\*\s*" + re.escape(key) + r"\s*:\*\*|^\s*(?:-\s*)?" + re.escape(key) + r"\s*:)\s*([^\n]*)",
        body, re.I | re.M,
    )
    if not m:
        return None
    val = m.group(1).strip()
    return val or None


def _adr_nodes(nodes):
    """Filtert die ADR-Knoten aus einer parse_w_blocks-Liste und reichert sie mit den
    fuer die Cross-Checks noetigen Feldern an. Knoten ohne eigene ID erhalten als
    Fallback ihre w_id (damit dangling-Refs trotzdem erkennbar bleiben)."""
    out = []
    for n in nodes:
        body = n["body"]
        if not _is_adr(body):
            continue
        node_id = _adr_node_id(body) or n["w_id"]
        sup = _adr_edge_ids(body, "superseded_by")
        out.append({
            "w_id": n["w_id"],
            "id": node_id,
            "status": _adr_status_value(body),
            "superseded_by": sup[0] if sup else None,
            "bausteine": _adr_edge_ids(body, "betrifft_baustein"),
            "entscheidung": _adr_field_value(body, "entscheidung"),
        })
    return out


def check_adr_superseded_chains(nodes):
    """BL-382 AK-7 / W-STAT-4: Konsistenz der superseded_by-Ketten ueber alle ADR-Knoten.

    Prueft (deterministisch, rein lesend):
      - **Zyklus-Guard:** keine zyklische superseded_by-Kette (ADR-1 -> ADR-2 -> ADR-1).
      - **Dangling-Guard:** superseded_by zeigt auf eine im Scope NICHT existente ADR-ID
        (Kette nicht aufloesbar -> kein stiller Durchlass; Cross-BL = AK-7-Constraint).
      - **Ein-aktiver-Kopf:** in jeder zusammenhaengenden Ketten-Komponente traegt GENAU
        EIN Knoten einen aktiven Status (akzeptiert/vorgeschlagen); alle Vorgaenger sind
        superseded. Null aktive Koepfe ODER >=2 aktive Koepfe -> Violation.

    `nodes` = parse_w_blocks(content)-Liste. -> Liste von Violation-Strings (leer = ok)."""
    adrs = _adr_nodes(nodes)
    by_id = {a["id"]: a for a in adrs}
    violations = []

    # 1) Dangling-Edges: superseded_by-Ziel nicht im Scope.
    for a in adrs:
        tgt = a["superseded_by"]
        if tgt is not None and tgt not in by_id:
            violations.append(
                "adr.superseded_by dangling: %s -> %s (Ziel-ADR nicht im Scope)" % (a["id"], tgt)
            )

    # 2) Zyklus-Erkennung entlang der superseded_by-Kanten (gerichteter Graph, out-degree<=1).
    state = {}  # 0=unbesucht, 1=im-Stack, 2=fertig
    cyclic_ids = set()

    def walk(start):
        node, path = start, []
        while node is not None and node in by_id:
            st = state.get(node, 0)
            if st == 1:
                # Zurueck auf einen Knoten im aktuellen Pfad -> Zyklus.
                idx = path.index(node)
                for c in path[idx:]:
                    cyclic_ids.add(c)
                return
            if st == 2:
                return
            state[node] = 1
            path.append(node)
            node = by_id[node]["superseded_by"]
        for c in path:
            state[c] = 2

    for a in adrs:
        if state.get(a["id"], 0) == 0:
            walk(a["id"])
    for cid in sorted(cyclic_ids):
        violations.append("adr.superseded_by cycle: %s ist Teil einer zyklischen Kette" % cid)

    # 3) Ein-aktiver-Kopf pro zusammenhaengender Komponente (Union ueber superseded_by-Kanten).
    #    Zyklische Knoten sind oben schon geflaggt -> aus der Kopf-Zaehlung ausgeklammert.
    parent = {a["id"]: a["id"] for a in adrs}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        parent[find(x)] = find(y)

    for a in adrs:
        tgt = a["superseded_by"]
        if tgt in by_id:
            union(a["id"], tgt)

    comps = {}
    for a in adrs:
        if a["id"] in cyclic_ids:
            continue
        comps.setdefault(find(a["id"]), []).append(a)
    for root, members in comps.items():
        heads = [m for m in members if (m["status"] or "") in ADR_ACTIVE_STATUS]
        member_ids = ", ".join(sorted(m["id"] for m in members))
        if len(heads) == 0:
            violations.append(
                "adr-chain no active head: Kette [%s] hat keinen aktiven Kopf "
                "(alle superseded/konflikt-offen)" % member_ids
            )
        elif len(heads) > 1:
            head_ids = ", ".join(sorted(h["id"] for h in heads))
            violations.append(
                "adr-chain >1 active head: Kette [%s] hat mehrere aktive Koepfe (%s) — "
                "Vorgaenger muessen superseded sein" % (member_ids, head_ids)
            )
    return violations


def detect_adr_conflicts(nodes):
    """BL-382 AK-8 Stufe-1 / W-STAT-3: deterministischer Konflikt-KANDIDATEN-Vorfilter.

    Findet Paare von ZWEI nicht-superseded ADRs mit Status `akzeptiert`, die denselben
    `betrifft_baustein` referenzieren UND eine UNTERSCHIEDLICHE `entscheidung` tragen ->
    Konflikt-KANDIDAT. Das ist die deterministisch maschinelle Stufe-1 (Set-Overlap +
    Entscheidungs-Ungleichheit). Ob der Widerspruch INHALTLICH echt ist, entscheidet
    Stufe-2 (opus-§9-Render, `_arc42_berater_entscheidungen`, ceiling-tier) — NICHT hier.
    Stufe-1-Kandidaten ohne Stufe-2-Bestaetigung bleiben `akzeptiert` (kein false-positive-Flag).

    `nodes` = parse_w_blocks(content)-Liste.
    -> Liste von Kandidaten-Dicts: {baustein, adr_ids:[id_a, id_b], entscheidungen:[e_a, e_b]}."""
    adrs = _adr_nodes(nodes)
    # Nur AKTIV-akzeptierte ADRs (W-STAT-3: zwei AKZEPTIERTE widersprechen sich; vorgeschlagen
    # = noch nicht entschieden -> kein aktiver Konflikt; superseded -> abgeloest, raus).
    active = [a for a in adrs if a["status"] == "akzeptiert"]
    candidates = []
    seen_pairs = set()
    for i in range(len(active)):
        for j in range(i + 1, len(active)):
            a, b = active[i], active[j]
            shared = set(a["bausteine"]) & set(b["bausteine"])
            if not shared:
                continue
            # Unterschiedliche Entscheidung = potenzieller Widerspruch (gleiche = kein Konflikt).
            if (a["entscheidung"] or "") == (b["entscheidung"] or ""):
                continue
            for baustein in sorted(shared):
                key = (baustein, tuple(sorted((a["id"], b["id"]))))
                if key in seen_pairs:
                    continue
                seen_pairs.add(key)
                candidates.append({
                    "baustein": baustein,
                    "adr_ids": [a["id"], b["id"]],
                    "entscheidungen": [a["entscheidung"], b["entscheidung"]],
                })
    return candidates


def check_w_block(block):
    """Prueft EINEN W-Block gegen die Gold-Form. -> {w_id, gold, missing[], ...}.

    BL-380 (additiv): traegt der Block `type: quality_scenario`, kommt eine typ-konditionale
    Szenario-Pruefung HINZU (6 iSAQB-Felder + response_measure-Triple + 2 Pflicht-Kanten).
    BL-382 (additiv): traegt der Block `type: adr`, kommt eine typ-konditionale ADR-Pruefung
    HINZU (6 Nygard-Felder + adr.status-Enum).
    BL-383 (additiv): traegt der Block `type: eval_finding`, kommt eine typ-konditionale
    Eval-Gate-Pruefung HINZU (10 Pflichtfelder + risk_class-Kazman-4-Enum + cost/benefit
    nicht-leer + kein binaeres PASS/FAIL-Primaer). Alle Subtyp-Pruefungen sind exklusiv (ein
    Knoten traegt genau einen type). Fuer alle anderen Knoten-Typen bleibt die Pruefung exakt
    wie zuvor (kein Breaking-Change)."""
    body = block["body"]
    missing = [f for f in GOLD_FIELDS if not _field_present(body, f)]
    if "Quelle" not in missing and not _quelle_has_wikilink(body):
        missing.append("Quelle(Wikilink)")
    status_value = _status_value(body)
    status_canonical = bool(status_value) and status_value in CANONICAL_STATUS

    is_scenario = _is_quality_scenario(body)
    scenario_missing = check_scenario_block(body) if is_scenario else []

    is_adr = _is_adr(body)
    adr_missing = check_adr_block(body) if is_adr else []

    is_eval_finding = _is_eval_finding(body)
    eval_finding_missing = check_eval_finding_block(body) if is_eval_finding else []

    return {
        "w_id": block["w_id"],
        "gold": (not missing) and status_canonical and (not scenario_missing)
        and (not adr_missing) and (not eval_finding_missing),
        "missing": missing + scenario_missing + adr_missing + eval_finding_missing,
        "status_value": status_value,
        "status_canonical": status_canonical,
        "is_scenario": is_scenario,
        "scenario_missing": scenario_missing,
        "is_adr": is_adr,
        "adr_missing": adr_missing,
        "is_eval_finding": is_eval_finding,
        "eval_finding_missing": eval_finding_missing,
    }


def validate_model(content):
    """Validiert ein ganzes Model. -> {w_blocks, total, gold_count, violations, prose_only}."""
    blocks = parse_w_blocks(content)
    checks = [check_w_block(b) for b in blocks]
    return {
        "w_blocks": checks,
        "total": len(blocks),
        "gold_count": sum(1 for c in checks if c["gold"]),
        "violations": [c for c in checks if not c["gold"]],
        # Prosa-Model: keine ### W-Bloecke, ABER W{n}-Erwaehnungen im Text (BL-243 AK-S4 Backfill-Kandidat).
        "prose_only": len(blocks) == 0 and bool(_W_MENTION.search(content)),
    }


def main(argv):
    if not argv:
        print("usage: quality_model_wform.py <Model.md> [<Model.md> ...]")
        return 2
    overall = 0
    for path in argv:
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                content = fh.read()
        except OSError as exc:
            print("[FEHLER] {}: {}".format(path, exc))
            overall = 1
            continue
        res = validate_model(content)
        if res["prose_only"]:
            print("[PROSE] {}: 0 ### W-Bloecke, aber W{{n}}-Erwaehnungen -> Prosa-Model "
                  "(BL-243 AK-S4 Backfill-Kandidat)".format(path))
            overall = 1
        elif res["violations"]:
            print("[VIOLATIONS] {}: {}/{} gold".format(path, res["gold_count"], res["total"]))
            for v in res["violations"]:
                why = []
                if v["missing"]:
                    why.append("fehlt: " + ", ".join(v["missing"]))
                if v["status_value"] and not v["status_canonical"]:
                    why.append("Status nicht-kanonisch: " + v["status_value"])
                print("    {}: {}".format(v["w_id"], "; ".join(why) or "non-gold"))
            overall = 1
        else:
            print("[GOLD] {}: {}/{} W-Bloecke gold-form (BL-243 Truth-Atomic-First)".format(
                path, res["gold_count"], res["total"]))
    return overall


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
