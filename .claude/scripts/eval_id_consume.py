"""
eval_id_consume.py — BL-383 batch_PL4 (AK-6): Eval-Gate als Konsument-PER-ID
(read-only Schema-Konsum der BL-380/382-Truth-Nodes).

Das Eval-Gate (BL-383) fuehrt KEINEN neuen Truth-Node-Typ ein (W-DOM-1). Es ist ein
Bewertungs-KONSUMENT, der die produzierten BL-380 `quality_scenario`-Nodes (SOLL) und
BL-382 `adr`-Nodes (Drift-Bezug) PER STABILER ID liest:
  - QS-ID-Format:  `{BL-SLUG}.QS-{n}`   (BL-380 W-DOM-4)
  - ADR-ID-Format: `{BL-SLUG}.ADR-{n}`  (BL-382 W-DOM-4, identisch zum ADR_EDGE_ID-Schema)
`{BL-SLUG}` = BL-309-lokales Praefix (`[A-Za-z0-9][A-Za-z0-9._-]*`), `{n}` = `\\d+`.

WARUM per ID, nicht per Vault-Pfad (W-DOM-2): robust gegen Vault-Reorganisation; der
Eval-Befund (`eval_finding.ref_node`) bleibt rueckverfolgbar zum EXAKTEN SOLL-Knoten.

W-INTEROP-1 (Schema-Konsum-Erbe): BL-383 konsumiert EXAKT das produzierte BL-380/382-
Schema (read-only). Es erfindet KEINE Schema-Abweichung (sonst Rueckkanal-BL, SOA-2 —
NICHT still hier). Die Feld-Reader sind Single-Source aus `quality_model_wform.py` (die
BL-380/382-Producer-Validator-Primitive), damit Konsum + Produktion NIE divergieren.

KEIN Producer-Apparat: kein Vault-Write, keine ID-Vergabe, kein Validator-Zweig fuer
einen neuen Node-Typ, kein INV-MODUS-Hook. Reiner read-only Konsum (W-DOM-1).

INTEROP-ERBE (forward_verify, NICHT jetzt-testbar): der Abgleich gegen die FINALE BL-380/
382-Impl (SOA-2) + die FINALE-Impl-Drift (Interop-Erbe) laeuft beim naechsten echten
Lauf — hier ist nur das ID-/Schema-Konsum-CONTRACT testbar, nicht der Live-Korpus.

CLI: `py eval_id_consume.py <Model.md> [--ref <ID>]`  (read-only).
  ohne --ref : listet die konsumierbaren QS-/ADR-Nodes (per ID).  exit 0.
  mit  --ref : loest die ID gegen das Model auf.  exit 0=ok / 1=unbekannt-od-malformed / 2=usage.
"""

import argparse
import re
import sys

import quality_model_wform as qmw

# ── ID-Referenz-Regex (AK-6) ──────────────────────────────────────────────────
# {BL-SLUG}.QS-{n} / {BL-SLUG}.ADR-{n}. Das {BL-SLUG}-Praefix-Schema ist identisch zum
# ADR_EDGE_ID in quality_model_wform (Single-Source der Praefix-Grammatik). Anker ^...$ —
# eine Vault-Pfad-Referenz (mit '/' oder '#') matcht NIE.
_SLUG = r"[A-Za-z0-9][A-Za-z0-9._-]*"
QS_ID_RE = re.compile(r"^" + _SLUG + r"\.QS-\d+$")
ADR_ID_RE = re.compile(r"^" + _SLUG + r"\.ADR-\d+$")


def is_qs_id(ref):
    """AK-6: True, wenn `ref` eine wohlgeformte `{BL-SLUG}.QS-{n}`-Referenz ist."""
    return bool(ref) and bool(QS_ID_RE.match(str(ref)))


def is_adr_id(ref):
    """AK-6: True, wenn `ref` eine wohlgeformte `{BL-SLUG}.ADR-{n}`-Referenz ist."""
    return bool(ref) and bool(ADR_ID_RE.match(str(ref)))


def classify_ref_id(ref):
    """AK-6: ordnet eine ref_node-ID ihrem SOLL-Knoten-Typ zu.
      -> 'qs'      fuer `{BL-SLUG}.QS-{n}`
      -> 'adr'     fuer `{BL-SLUG}.ADR-{n}`
      -> 'pattern' fuer einen sonstigen nicht-leeren Token OHNE Pfad-Zeichen (PatternLibrary-
                   Treffer-ID, AK-3 ref_node) — weder QS noch ADR, aber eine valide lokale ID.
      -> None      fuer malformed / Vault-Pfad (mit '/' oder '#') / leer.
    """
    if not ref:
        return None
    s = str(ref).strip()
    if is_qs_id(s):
        return "qs"
    if is_adr_id(s):
        return "adr"
    # Vault-Pfad/Anchor (verboten, W-DOM-2) -> malformed.
    if "/" in s or "#" in s or not s:
        return None
    # sonst: eine lokale Pattern-Treffer-ID (AK-3). Whitespace = malformed.
    if re.match(r"^[A-Za-z0-9][A-Za-z0-9._-]*$", s):
        return "pattern"
    return None


# ── read-only Schema-Konsum (per ID gegen produzierte BL-380/382-Nodes) ───────

# Welche Felder pro Knoten-Typ konsumiert werden (read-only, EXAKT das produzierte Schema,
# W-INTEROP-1). Die Werte werden ueber die quality_model_wform-Reader gezogen (Single-Source).
_QS_CONSUME_FIELDS = ["metric", "threshold", "method", "endpoint_type", "endpoint_ref"]
_ADR_CONSUME_FIELDS = qmw.ADR_NYGARD_FIELDS + ["betrifft_baustein"]


def _consume_qs_fields(body):
    """Liest die BL-380 response_measure-/endpoint-Felder aus einem quality_scenario-Body
    (read-only). response_measure-Tripel liegt verschachtelt — der generische
    _eval_field_value-Reader (Single-Source) greift die indentierten Skalare."""
    return {k: qmw._eval_field_value(body, k) for k in _QS_CONSUME_FIELDS}


def _consume_adr_fields(body):
    """Liest die BL-382 Nygard-Felder + betrifft_baustein aus einem adr-Body (read-only)."""
    out = {}
    for k in _ADR_CONSUME_FIELDS:
        if k == "status":
            out[k] = qmw._adr_status_value(body)
        else:
            out[k] = qmw._adr_field_value(body, k)
    return out


def load_consumable_nodes(content):
    """AK-6 (W-INTEROP-1): parst ein Model und indiziert die KONSUMIERBAREN BL-380/382-Nodes
    PER ID. Liefert {id: {"kind": "quality_scenario"|"adr", "w_id": ..., "fields": {...}}}.

    read-only — kein Schema-Edit, kein Write, KEIN neuer Node-Typ (W-DOM-1). Nur die
    bestehenden quality_scenario- + adr-Typen werden gelesen (plain-W/eval_finding ignoriert).
    Knoten ohne eigene `id:` werden uebersprungen (per-ID-Adressierung braucht eine ID)."""
    index = {}
    for block in qmw.parse_w_blocks(content):
        body = block["body"]
        if qmw._is_quality_scenario(body):
            kind, fields = "quality_scenario", _consume_qs_fields(body)
        elif qmw._is_adr(body):
            kind, fields = "adr", _consume_adr_fields(body)
        else:
            continue
        node_id = qmw._adr_node_id(body)  # generischer `id:`-Reader (QS + ADR teilen ihn)
        if not node_id:
            continue
        index[node_id] = {"kind": kind, "w_id": block["w_id"], "fields": fields}
    return index


def resolve_ref_node(ref, content):
    """AK-6: loest eine ref_node-ID gegen die im Model produzierten Nodes auf.
    -> der konsumierte Knoten {kind, w_id, fields} ODER None, wenn:
       - die ID malformed ist (kein QS-/ADR-Format, z.B. Vault-Pfad), ODER
       - die ID wohlgeformt, aber NICHT im Model produziert ist (dangling Referenz).
    Negativ-Aufloesung = der Befund haengt NICHT an einem existenten SOLL-Knoten."""
    kind = classify_ref_id(ref)
    if kind not in ("qs", "adr"):
        return None
    return load_consumable_nodes(content).get(str(ref).strip())


def validate_ref_consumable(ref, content):
    """AK-6: prueft EINE ref_node-ID gegen das Producer-Model (read-only).
    -> [] (ok: ID-format-valide UND im Model produziert) ODER Violation-Liste:
       - 'ref_node.malformed-id-format(<ref>)'  wenn kein QS-/ADR-ID-Format
       - 'ref_node.dangling(<ref>)'             wenn format-valide aber nicht produziert."""
    violations = []
    kind = classify_ref_id(ref)
    if kind not in ("qs", "adr"):
        violations.append("ref_node.malformed-id-format(%s)" % ref)
        return violations
    if resolve_ref_node(ref, content) is None:
        violations.append("ref_node.dangling(%s)" % ref)
    return violations


# ── CLI ───────────────────────────────────────────────────────────────────────

def _print(msg):
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"))


def main(argv):
    parser = argparse.ArgumentParser(
        prog="eval_id_consume.py",
        description="BL-383 AK-6: Eval-Gate Konsument-per-ID (read-only Schema-Konsum)",
        add_help=False,
    )
    parser.add_argument("model", nargs="?")
    parser.add_argument("--ref", default=None, help="ref_node-ID gegen das Model aufloesen")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    if not args.model:
        _print("usage: eval_id_consume.py <Model.md> [--ref <ID>]")
        return 2
    try:
        with open(args.model, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    except OSError as exc:
        _print("[FEHLER] {}: {}".format(args.model, exc))
        return 2

    if args.ref is None:
        index = load_consumable_nodes(content)
        _print("[KONSUM] {}: {} konsumierbare Node(s) (per ID, read-only)".format(
            args.model, len(index)))
        for node_id, node in sorted(index.items()):
            _print("    {} [{}]".format(node_id, node["kind"]))
        return 0

    # --ref: aufloesen.
    violations = validate_ref_consumable(args.ref, content)
    if violations:
        _print("[VIOLATION] {}: {}".format(args.ref, "; ".join(violations)))
        return 1
    node = resolve_ref_node(args.ref, content)
    _print("[OK] {} -> {} (w_id={})".format(args.ref, node["kind"], node["w_id"]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
