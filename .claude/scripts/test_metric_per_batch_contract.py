#!/usr/bin/env python3
"""
BL-266 AK-S4: metric_per_batch Producer-Consumer Schema-Vertrag-Test.

Der Wurzel-Fix gegen die Schema-Drift-Fehlerklasse: ein Refactor erweitert den KONSUMENTEN
(_SDF_berater_modusEntscheidung liest neue metric_per_batch-Felder), ohne den PRODUZENTEN
(_IDF_berater_metricPlanner schreibt sie) nachzuziehen -> stille ?? null No-Ops.

Dieser Test extrahiert beide Feld-Listen aus den Markdown-Skills und FAILT bei Drift
(Konsument liest ein Feld, das kein Produzent schreibt). Damit wird der Drift kuenftig RED
statt still — die Klasse, die BL-239/BL-231 run-dead machte.

Lauf: py -3 .claude/scripts/test_metric_per_batch_contract.py   (exit 0 = gruen)
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
COMMANDS = os.path.normpath(os.path.join(HERE, "..", "commands"))
PRODUCER = os.path.join(COMMANDS, "_IDF_berater_metricPlanner.md")
CONSUMER = os.path.join(COMMANDS, "_SDF_berater_modusEntscheidung.md")

# Felder, die metricPlanner NUR konditional (BL-203, SCHRITT 3.5 per_pl_evaluation != null) schreibt.
# Sie HABEN einen Producer-Pfad -> zaehlen als PRODUCED (struktureller Drift-Check, nicht Laufzeit-Praesenz).
KNOWN_OPTIONAL = {"pl_srs_max", "pl_k_score_avg", "pl_bottleneck_ct"}


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def extract_produced(text):
    """Autoritative Producer-Liste = das `required_keys = { ... }`-Set-Literal (INV-METRIC-SCHEMA-1).
    Plus die metric_per_batch[...]-Dict-Literal-Keys (SCHRITT 2 Output) als Fallback/Ergaenzung."""
    produced = set()
    # (a) required_keys-Set-Literal (die maschinell-stabile Schema-Pflicht-Deklaration)
    m = re.search(r"required_keys\s*=\s*\{([^}]+)\}", text)
    if m:
        produced |= set(re.findall(r"""["']([a-z_]+)["']""", m.group(1)))
    # (b) metric_per_batch[...]-Dict-Zuweisungen: "feld": wert  (SCHRITT 2 + spaetere Spiegel)
    #     nur innerhalb von metric_per_batch-Schreib-Bloecken (Heuristik: Zeilen "feld": ...)
    for block in re.findall(r"metric_per_batch\[[^\]]+\]\s*(?:=|\.)\s*\{(.*?)\}", text, re.DOTALL):
        produced |= set(re.findall(r"""["']([a-z_]+)["']\s*:""", block))
    # (c) explizite Spiegel-Schreibungen: metric_per_batch[sb].feld = ...
    produced |= set(re.findall(r"metric_per_batch\[[^\]]+\]\.([a-z_]+)\s*=", text))
    return produced | KNOWN_OPTIONAL


def extract_consumed(text):
    """Consumer-Reads = die zwei kanonischen Lese-Idiome in modusEntscheidung."""
    consumed = set()
    # a) batch_metric.<feld>   (batch_metric = metric_per_batch[current_sub_batch_id])
    consumed |= set(re.findall(r"batch_metric\.([a-z_]+)", text))
    # b) metric_per_batch[current_sub_batch_id].<feld>  bzw [sb].<feld>
    consumed |= set(re.findall(r"metric_per_batch\[[^\]]+\]\.([a-z_]+)", text))
    # Zuweisungs-Artefakt rausfiltern (falls der Consumer selbst irgendwo schreibt — sollte er nicht)
    return consumed


def compute_drift(producer_text, consumer_text):
    """Reine Drift-Funktion (testbarer Kern, BL-381 AK-3 / W-AK3-2): liefert die sortierte Liste
    der Konsum-Felder OHNE Producer (consumed - produced). Leer = kein Drift.

    Auf echte Producer/Consumer-Texte angewandt = der Live-Schema-Vertrag; auf synthetische Texte
    angewandt = der Beweis, dass ein NEUES Konsum-Feld ohne Producer GEFANGEN wird (RED)."""
    return sorted(extract_consumed(consumer_text) - extract_produced(producer_text))


def main():
    prod = extract_produced(read(PRODUCER))
    cons = extract_consumed(read(CONSUMER))
    drift = sorted(cons - prod)

    print("PRODUCED (metricPlanner):", ", ".join(sorted(prod)) or "(leer)")
    print("CONSUMED (modusEntscheidung):", ", ".join(sorted(cons)) or "(leer)")
    print()
    if drift:
        print("FAIL — DRIFT: Konsument liest %d Feld(er), die kein Produzent schreibt:" % len(drift))
        for f in drift:
            print("   * metric_per_batch[*].%s  (gelesen, NIE geschrieben -> ?? null No-Op)" % f)
        print("\nBL-266: jedes Drift-Feld muss verdrahtet (Producer schreibt) ODER der Consumer-Read entfernt werden.")
        return 1
    print("OK — kein Drift: jedes konsumierte metric_per_batch-Feld hat einen Producer.")
    return 0


# ─────────────────────────────────────────────────────────────────────────────────────
# BL-381 batch_3 (AK-3): pytest-Guards. Die obige main()-CLI bleibt der menschen-lesbare
# Live-Report; diese Funktionen machen den Drift-Vertrag pytest-kollektierbar UND beweisen den
# RED-Pfad (Konsum-Feld ohne Producer wird gefangen, W-AK3-2). Lead-verify aus Repo-Root.
# ─────────────────────────────────────────────────────────────────────────────────────

# Die neuen BL-381-Achsen, die als per-Batch-Felder andocken (AK-3 + AK-6 code-Teil).
BL381_NEW_AXIS_FIELDS = [
    "decoupling_level",          # AK-1 (kazman_screening_metrics)
    "propagation_cost",          # AK-1 (kazman_screening_metrics)
    "co_commit_coupling",        # AK-2 (kazman_kscore_axes)
    "coupling_structural",       # AK-6 structural (Ca/Ce)
    "coupling_temporal_resource",  # AK-6 temporal/resource (co-commit)
]


def test_live_contract_no_drift():
    """Happy-Path / Nicht-Regression: die ECHTEN metricPlanner/modusEntscheidung-Skills haben
    keinen Drift (jedes konsumierte metric_per_batch-Feld hat einen Producer). Bleibt gruen,
    solange jedes neue Konsum-Feld einen Producer bekommt."""
    drift = compute_drift(read(PRODUCER), read(CONSUMER))
    assert drift == [], (
        "metric_per_batch-Drift: Konsument liest ohne Producer: %r "
        "(BL-266/BL-381: Producer schreiben ODER Consumer-Read entfernen)" % drift
    )


def test_drift_detector_catches_consume_without_producer():
    """RED-KERN (W-AK3-2): ein NEUES Konsum-Feld OHNE Producer MUSS gefangen werden. Wir fuettern
    synthetischen Producer-/Consumer-Text, in dem der Consumer ein Feld liest, das im Producer
    fehlt — compute_drift MUSS es als Drift melden. (Genau dieser Mechanismus laesst die
    Live-Erweiterung RED werden, wenn man ein neues per-Batch-Feld nur konsumiert.)"""
    producer = 'required_keys = {"srs_max", "k_score_avg"}\n'
    consumer = "batch_metric.srs_max\nbatch_metric.decoupling_level\n"
    drift = compute_drift(producer, consumer)
    assert "decoupling_level" in drift, (
        "Drift-Detektor hat ein Konsum-ohne-Producer-Feld DURCHGEWUNKEN (W-AK3-2 verletzt): %r" % drift
    )


def test_drift_detector_green_when_producer_present():
    """Gegenprobe (Happy-Path des Detektors): sobald der Producer das Feld schreibt, ist KEIN
    Drift mehr — der Detektor blockt nicht faelschlich ein verdrahtetes Feld."""
    producer = 'required_keys = {"srs_max", "decoupling_level"}\n'
    consumer = "batch_metric.srs_max\nbatch_metric.decoupling_level\n"
    assert compute_drift(producer, consumer) == []


def test_new_axis_fields_have_producer():
    """AK-3-Verdrahtung: jede neue BL-381-Achse, die als per-Batch-Feld gefuehrt wird, hat einen
    Producer in metricPlanner (required_keys ODER metric_per_batch-Dict-Literal). Konsum-ohne-
    Producer waere nach W-AK3-2 ein Defekt — hier wird die Producer-SEITE positiv belegt."""
    prod = extract_produced(read(PRODUCER))
    missing = [f for f in BL381_NEW_AXIS_FIELDS if f not in prod]
    assert missing == [], (
        "BL-381 per-Batch-Felder OHNE Producer in metricPlanner: %r "
        "(AK-3: jedes neue Konsum-Feld braucht einen Producer)" % missing
    )


def test_consumed_new_fields_are_subset_of_produced():
    """Vollstaendigkeit der Erweiterung: SOWEIT der Consumer eine neue BL-381-Achse liest, MUSS
    sie produziert sein (kein stiller ?? null No-Op). Felder, die der Consumer (noch) nicht liest,
    sind erlaubt (Producer-only forward-compat, analog gap_status)."""
    prod = extract_produced(read(PRODUCER))
    cons = extract_consumed(read(CONSUMER))
    consumed_new = [f for f in BL381_NEW_AXIS_FIELDS if f in cons]
    drift_new = [f for f in consumed_new if f not in prod]
    assert drift_new == [], "Neue BL-381-Achse konsumiert ohne Producer: %r" % drift_new


def test_main_cli_returns_zero_on_live_contract():
    """Die menschen-lesbare CLI (main) bleibt der Live-Gate: exit 0 auf den echten Skills."""
    assert main() == 0


if __name__ == "__main__":
    sys.exit(main())
