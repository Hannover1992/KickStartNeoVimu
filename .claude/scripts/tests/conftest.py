"""conftest.py — Import-Infrastruktur fuer .claude/scripts/tests/

Fuegt .claude/scripts/ zum sys.path hinzu, damit `import adr_index` (und andere
Skripte in .claude/scripts/) ohne relative-Import-Hacks funktioniert.

Import-Infrastruktur ONLY — keine Test-Logik.
"""
import sys
from pathlib import Path

# .claude/scripts/ auf sys.path setzen (Elternverzeichnis dieses conftest.py)
_SCRIPTS_DIR = Path(__file__).parent.parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
