"""pytest-Konfiguration fuer .claude/scripts-Suiten.

Registriert die Test-Typ-Marker (BL-227 C-5 Stage-Labeling), damit
`@pytest.mark.testtyp_unit` / `@pytest.mark.testtyp_integration` keine
PytestUnknownMarkWarning erzeugen und per `-m` selektierbar sind.
"""


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "testtyp_unit: Stage 1 — Unit (Format/Schema, isoliert)."
    )
    config.addinivalue_line(
        "markers",
        "testtyp_integration: Stage 3 — Integration (end-zu-end via echtem Subprozess).",
    )
