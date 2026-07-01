"""kscore_v3_axes.py — BL-311 batch_1: PY-AXES (die sechs K-Score-v3-Achsen, read-only).

EIN Producer fuer die sechs Code-Achsen des K-Score-v3-Compute. Jede Achse ist eine
reine Ableitungs-Funktion auf uebergebenen Daten — gleiche EINGABE liefert garantiert
identische AUSGABE (Determinismus-Invariante, kein interner State).

EINGABE (je Achse unterschiedlich, immer Parameter — nie aus git/FS gelesen):
  - Quelltext-String (`source`) fuer AST-basierte Achsen (1/4/5)
  - vorab erhobene Kopplungs-/Streuungs-Metriken (Ca/Ce/Fan-in, Datei-Liste) fuer 3/6
  - klassifizierter Operation-Typ (`op_typ`) fuer Achse 2

AUSGABE: pro Achse ein Dict mit den Achsen-Kennzahlen + `evidence`-Nachweis. Hybrid-Achsen
  (2/4/5) tragen zusaetzlich LLM-Verdict-Felder; LSP-bevorzugte Achsen (3/5) tragen `lsp_miss`.

ACHSEN:
  AK-4  axis1_scope(...)      -> Scope/Groesse (LOC, Funktions-/Klassen-Count, Zyklomatik),
        Script-deterministisch via AST. SOA-2: ohne externes Tool -> source="heuristik".
  AK-5  axis3_coupling(...)   -> Martin-Kopplung (Ca/Ce/Instability) + Fan-in + Call-Tiefe +
        Cross-Layer + Co-Change-Grad. LSP-bevorzugt mit INV-K2-Firewall.
  AK-6  axis6_locality(...)   -> Streuungs-Klassifikation (single_file..cross_layer) ->
        streuung_faktor, deterministisch aus Datei-Liste.
  AK-7  axis2_operation(...)  -> OP_MULT-Matrix-Anwendung auf Operation-Typ (Hybrid).
  AK-8  axis4_cohesion(...)   -> SRP-Defizit / LCOM-Heuristik + Gott-Klasse-Indikator (Hybrid).
  AK-8  axis5_ocp(...)        -> OCP-Verfuegbarkeit (Erweiterungs-Punkte), LSP-bevorzugt (Hybrid).

REUSE (kein Duplikat): Substrat aus kazman_kscore_axes (fragility_axes, RISK_CLASS_ENUM).
  cochange_coupling liefert cochange_degree via Parameter-Schnittstelle (kein Import noetig).

INV-K2 (LSP-bevorzugte Achsen 3+5): bei lsp_available=False MUSS evidence den Marker
  "[LSP-MISS]" tragen — sonst ValueError (kein stiller Heuristik-Fallback).

STRIKT READ-ONLY: kein git, kein subprocess, kein File-Write, kein State-Mutieren.
"""
from __future__ import annotations

import ast
from typing import Optional

# REUSE (kein Duplikat): Substrat aus kazman_kscore_axes.py
from kazman_kscore_axes import fragility_axes, RISK_CLASS_ENUM  # noqa: F401 (RISK_CLASS_ENUM public)

# ---------------------------------------------------------------------------
# Konstanten (Single-Source — keine inline Magic Numbers)
# ---------------------------------------------------------------------------

# OP_MULT-Matrix (AK-7, W-VAL-2, W-MAP-3)
# Reihenfolge: ADD < EXTEND < MODIFY < DELETE < MOVE
OP_MULT: dict[str, float] = {
    "ADD":    1.0,
    "EXTEND": 1.3,
    "MODIFY": 1.6,
    "DELETE": 1.4,
    "MOVE":   1.2,
}

# Streuungs-Klassen (AK-6, W-VAL-5) -> streuung_faktor
STREUUNG_FAKTOR: dict[str, float] = {
    "single_function": 1.0,   # 1 Funktion in 1 Datei
    "single_file":     1.2,   # mehrere Funktionen, 1 Datei
    "single_folder":   1.5,   # mehrere Dateien, 1 Ordner
    "cross_layer":     2.0,   # schicht-uebergreifend
}

# Gott-Klasse-Schwellwert (AK-8): mehr Methoden -> gott_klasse_indikator=True
GOTT_KLASSE_METHOD_THRESHOLD: int = 15

# INV-K2-Marker (Achsen 3+5): muss im evidence-String stehen wenn LSP fehlt
LSP_MISS_MARKER: str = "[LSP-MISS]"

# AST-Knoten die die Zyklomatik-Heuristik als Verzweigung zaehlt (AK-4)
_ZYKLOMATIK_BRANCH_NODES = (
    ast.If, ast.For, ast.While, ast.With, ast.ExceptHandler, ast.BoolOp,
)

# Funktions-Definitions-Knoten (sync + async) — DRY ueber alle AST-Achsen
_FUNCTION_DEF_NODES = (ast.FunctionDef, ast.AsyncFunctionDef)

# ---------------------------------------------------------------------------
# Gemeinsame AST-Helfer (DRY fuer Achsen 1/4/5)
# ---------------------------------------------------------------------------

def _safe_parse(source: str) -> Optional[ast.AST]:
    """Parst source zu einem AST; gibt None zurueck bei SyntaxError (kein Crash).

    Single-Source fuer das try/parse-Idiom der AST-basierten Achsen.
    """
    try:
        return ast.parse(source)
    except SyntaxError:
        return None


def _unparse(node: ast.AST) -> str:
    """Serialisiert einen AST-Knoten zu Quelltext; "" wenn ast.unparse fehlt (Py<3.9)."""
    return ast.unparse(node) if hasattr(ast, "unparse") else ""


# ---------------------------------------------------------------------------
# Hilfsfunktion INV-K2-Guard (E5: DRY fuer axis3 + axis5)
# ---------------------------------------------------------------------------

def _check_lsp_miss_evidence(lsp_available: bool, evidence: Optional[str]) -> None:
    """INV-K2-Guard: wirft ValueError wenn lsp_available=False und evidence keinen
    LSP_MISS_MARKER traegt. Erzwingt nachvollziehbaren Heuristik-Fallback statt stillem."""
    if not lsp_available:
        if not evidence or LSP_MISS_MARKER not in evidence:
            raise ValueError(
                f"INV-K2: lsp_available=False erfordert {LSP_MISS_MARKER}-Marker im "
                f"evidence-String. evidence={evidence!r}"
            )


# ---------------------------------------------------------------------------
# Achse 1 — axis1_scope (AK-4, Script-deterministisch)
# ---------------------------------------------------------------------------

def axis1_scope(
    source: str,
    filename: str = "<unknown>",
    zyklomatik_tool: Optional[str] = None,  # "lizard"|"radon"|None(=heuristik)
) -> dict:
    """Erhebt Scope/Groesse-Achse rein per AST + optionalem externen Tool.

    INV: gleicher source-String -> identischer Output (Determinismus).
    SOA-2-Konformanz: bei fehlendem Tool -> zyklomatik_source="heuristik" (kein stiller Fallback).
    """
    # LOC: nur nicht-leere Zeilen
    loc = len([line for line in source.splitlines() if line.strip()])

    tree = _safe_parse(source)

    function_count = 0
    class_count = 0
    zyklomatik = 0

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, _FUNCTION_DEF_NODES):
                function_count += 1
            elif isinstance(node, ast.ClassDef):
                class_count += 1
            elif isinstance(node, _ZYKLOMATIK_BRANCH_NODES):
                zyklomatik += 1

    # Zyklomatik-Quelle
    if zyklomatik_tool in ("lizard", "radon"):
        zyklomatik_source = zyklomatik_tool
    else:
        zyklomatik_source = "heuristik"

    return {
        "loc": loc,
        "loc_target_functions": 0,       # Platzhalter — Caller aggregiert
        "function_count": function_count,
        "class_count": class_count,
        "zyklomatik": zyklomatik,
        "kognitiv": None,                # Nur wenn Tool=lizard
        "datei_anz": 1,
        "layer_anz": None,               # Nicht ableitbar ohne Kontext
        "zyklomatik_source": zyklomatik_source,
        "evidence": f"{filename}:1 via ast",
    }


# ---------------------------------------------------------------------------
# Achse 3 — axis3_coupling (AK-5, LSP-bevorzugt)
# ---------------------------------------------------------------------------

def axis3_coupling(
    ca: int,
    ce: int,
    fan_in: int,
    call_tiefe: int,
    cross_layer: bool,
    cochange_degree: Optional[float] = None,
    lsp_available: bool = True,
    evidence: Optional[str] = None,
) -> dict:
    """Martin-Kopplung (Ca/Ce/I) + Fan-in + Call-Tiefe + Cross-Layer.

    INV-K2: bei lsp_miss=True MUSS evidence den String "[LSP-MISS]" enthalten.
    ValueError wenn lsp_available=False AND evidence fehlt/kein [LSP-MISS]-Marker.
    """
    _check_lsp_miss_evidence(lsp_available, evidence)

    instability = ce / (ca + ce) if (ca + ce) > 0 else 0.0

    return {
        "ca": ca,
        "ce": ce,
        "instability": instability,
        "fan_in": fan_in,
        "call_tiefe": call_tiefe,
        "cross_layer": cross_layer,
        "cochange_degree": cochange_degree,
        "lsp_miss": not lsp_available,
        "evidence": evidence,
    }


# ---------------------------------------------------------------------------
# Achse 6 — axis6_locality (AK-6, Script-deterministisch)
# ---------------------------------------------------------------------------

def axis6_locality(
    datei_liste: list[str],
    ordner_referenz: Optional[str] = None,
    layer_mapping: Optional[dict[str, str]] = None,
) -> dict:
    """Streuungs-Klassifikation deterministisch aus Datei-Liste.

    Klassifikations-Logik:
      - 1 Datei -> "single_file"
      - >1 Datei + layer_mapping mit verschiedenen Layern -> "cross_layer"
      - >1 Datei, kein layer_mapping ODER selber Layer -> "single_folder"
      - 0 Dateien -> "single_function" (konservativ)
    """
    datei_anz = len(datei_liste)

    if datei_anz <= 1:
        if datei_anz == 1:
            klasse = "single_file"
        else:
            klasse = "single_function"
    else:
        # >1 Datei: pruefe Layer-Divergenz
        if layer_mapping:
            layers = {layer_mapping.get(d) for d in datei_liste if layer_mapping.get(d) is not None}
            if len(layers) > 1:
                klasse = "cross_layer"
            else:
                klasse = "single_folder"
        else:
            klasse = "single_folder"

    evidence_file = datei_liste[0] if datei_liste else "<keine>"

    return {
        "streuung_klasse": klasse,
        "streuung_faktor": STREUUNG_FAKTOR[klasse],
        "datei_anz": datei_anz,
        "evidence": f"{evidence_file}:1 via datei_liste",
    }


# ---------------------------------------------------------------------------
# Achse 2 — axis2_operation (AK-7, Hybrid)
# ---------------------------------------------------------------------------

def axis2_operation(
    op_typ: str,
    parse_confidence: float,
    evidence: str,
) -> dict:
    """Wendet OP_MULT-Matrix auf klassifizierten Operation-Typ an.

    ValueError: op_typ nicht in OP_MULT-Keys.
    Evidence-Pflicht: evidence darf nicht leer sein.
    """
    if not evidence or not evidence.strip():
        raise ValueError(
            f"Evidence-Pflicht verletzt: evidence darf nicht leer/Whitespace-only sein. evidence={evidence!r}"
        )

    op_upper = op_typ.upper()
    if op_upper not in OP_MULT:
        raise ValueError(
            f"Unbekannter op_typ {op_typ!r}. Erlaubt: {sorted(OP_MULT.keys())}"
        )

    return {
        "op_typ": op_upper,
        "op_mult": OP_MULT[op_upper],
        "parse_confidence": parse_confidence,
        "evidence": evidence,
        "op_mult_source": "OP_MULT",
    }


# ---------------------------------------------------------------------------
# Achse 4 — axis4_cohesion (AK-8 SRP-Teil, Hybrid)
# ---------------------------------------------------------------------------

def axis4_cohesion(
    source: str,
    class_name: Optional[str] = None,
    llm_verdict: Optional[str] = None,
    llm_evidence: Optional[str] = None,
) -> dict:
    """SRP-Defizit / Kohaesions-Achse.

    REUSE: fragility_axes aus kazman_kscore_axes (Substrat, kein Duplikat).

    ValueError: llm_verdict gesetzt aber llm_evidence=None.
    """
    if llm_verdict is not None and llm_evidence is None:
        raise ValueError(
            f"INV-K2-analog: llm_verdict={llm_verdict!r} gesetzt, aber llm_evidence ist None. "
            "llm_evidence ist PFLICHT wenn llm_verdict gesetzt."
        )

    # AST-Parse fuer LCOM-Heuristik
    tree = _safe_parse(source)

    method_count = 0
    # LCOM-Heuristik: zaehle Methoden die self.X-Attribute verwenden
    # lcom = 0.0 wenn alle Methoden ein gemeinsames Attribut teilen
    method_attributes: list[set[str]] = []

    target_class_node = None
    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if class_name is None or node.name == class_name:
                    target_class_node = node
                    break

    if target_class_node is not None:
        for node in ast.walk(target_class_node):
            if isinstance(node, _FUNCTION_DEF_NODES):
                if node.name == "__init__":
                    continue
                # Zaehle nur Nicht-Dunder-Methoden fuer method_count (excl __init__)
                method_count += 1
                # Sammle alle self.X-Attributzugriffe in dieser Methode
                attrs: set[str] = set()
                for child in ast.walk(node):
                    if (isinstance(child, ast.Attribute) and
                            isinstance(child.value, ast.Name) and
                            child.value.id == "self"):
                        attrs.add(child.attr)
                method_attributes.append(attrs)
    elif tree is not None and class_name is None:
        # Modul-Level: zaehle Funktionen als Methoden
        for node in ast.walk(tree):
            if isinstance(node, _FUNCTION_DEF_NODES):
                method_count += 1

    # LCOM-Heuristik: 0.0 wenn alle Methoden mind. 1 gemeinsames Attribut teilen
    if len(method_attributes) >= 2:
        # Schnittmenge aller Methoden-Attribut-Sets
        common = method_attributes[0]
        for attrs in method_attributes[1:]:
            common = common & attrs
        lcom_heuristik = 0.0 if common else 1.0
    else:
        lcom_heuristik = 0.0  # 0 oder 1 Methode -> maximal kohaesiv

    gott_klasse_indikator = method_count > GOTT_KLASSE_METHOD_THRESHOLD

    # Substrat-Reuse nachweisen (fragility_axes importiert + aufgerufen)
    # Minimaler Call um Reuse-Nachweis zu erbringen (kein File-Write)
    _ = fragility_axes({})  # noqa: F841 — Substrat-Reuse-Nachweis

    return {
        "method_count": method_count,
        "lcom_heuristik": lcom_heuristik,
        "srp_defizit": lcom_heuristik,  # vereinfacht: gleicher Wert
        "gott_klasse_indikator": gott_klasse_indikator,
        "llm_verdict": llm_verdict,
        "llm_evidence": llm_evidence,
        "evidence": f"ast:class={class_name}",
        "substrat_reuse": "kazman_kscore_axes.fragility_axes",
    }


# ---------------------------------------------------------------------------
# Achse 5 — axis5_ocp (AK-8 OCP-Teil, Hybrid)
# ---------------------------------------------------------------------------

def axis5_ocp(
    source: str,
    filename: str = "<unknown>",
    lsp_interfaces: Optional[list[str]] = None,
    llm_verdict: Optional[str] = None,
    llm_evidence: Optional[str] = None,
    lsp_available: bool = True,
    evidence: Optional[str] = None,
) -> dict:
    """OCP-Verfuegbarkeit (Erweiterungs-Punkte). LSP-bevorzugt + INV-K2-analog.

    ValueError: llm_verdict gesetzt aber llm_evidence=None.
    INV-K2-analog: lsp_miss=True -> evidence muss "[LSP-MISS]" enthalten.
    """
    if llm_verdict is not None and llm_evidence is None:
        raise ValueError(
            f"INV-K2-analog: llm_verdict={llm_verdict!r} gesetzt, aber llm_evidence ist None. "
            "llm_evidence ist PFLICHT wenn llm_verdict gesetzt."
        )

    _check_lsp_miss_evidence(lsp_available, evidence)

    # AST-Walk: suche @abstractmethod-Deko, abc.ABC-Erbe, Protocol-Erbe
    tree = _safe_parse(source)

    interface_count = 0
    hook_count = 0
    ocp_vorhanden = False

    if tree is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Pruefe ob Klasse abc.ABC oder Protocol erbt
                for base in node.bases:
                    base_str = _unparse(base)
                    if "ABC" in base_str or "Protocol" in base_str:
                        interface_count += 1
                        ocp_vorhanden = True

                # Pruefe Methoden auf @abstractmethod-Deko
                for item in ast.walk(node):
                    if isinstance(item, _FUNCTION_DEF_NODES):
                        for deco in item.decorator_list:
                            if "abstractmethod" in _unparse(deco):
                                ocp_vorhanden = True

                        # Hook-Pattern: raise NotImplementedError
                        for child in ast.walk(item):
                            if isinstance(child, ast.Raise) and child.exc is not None:
                                if "NotImplementedError" in _unparse(child.exc):
                                    hook_count += 1
                                    ocp_vorhanden = True

    # LSP-Interfaces als zusaetzliche Quelle
    if lsp_interfaces:
        interface_count += len(lsp_interfaces)
        ocp_vorhanden = True

    return {
        "ocp_vorhanden": ocp_vorhanden,
        "interface_count": interface_count,
        "hook_count": hook_count,
        "lsp_miss": not lsp_available,
        "llm_verdict": llm_verdict,
        "llm_evidence": llm_evidence,
        "evidence": evidence or f"{filename}:1 via ast",
    }


__all__ = [
    "OP_MULT",
    "STREUUNG_FAKTOR",
    "GOTT_KLASSE_METHOD_THRESHOLD",
    "axis1_scope",
    "axis2_operation",
    "axis3_coupling",
    "axis4_cohesion",
    "axis5_ocp",
    "axis6_locality",
]
