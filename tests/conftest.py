"""Make the project root importable no matter where pytest is run from.

Without this, `logic_utils` only resolves when pytest happens to be invoked
from the project root (which is what puts the root on sys.path). Running
`pytest` from inside tests/, or from an IDE's test runner, would fail at
collection with ModuleNotFoundError.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
