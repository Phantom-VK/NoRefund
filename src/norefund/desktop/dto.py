"""Convert core dataclasses into JSON-safe structures for the JS bridge.

Field names are preserved exactly. The frontend's TypeScript interfaces in
`frontend/src/lib/types.ts` mirror these one-for-one; if you change a core
dataclass field you must change the interface too (nothing enforces this at
build time — see the round-trip test in tests/test_desktop_api.py).
"""

from __future__ import annotations

import dataclasses
from datetime import date, datetime
from enum import Enum
from pathlib import Path
from typing import Any


def to_jsonable(obj: Any) -> Any:
    """Recursively convert `obj` into something `json.dumps` accepts."""
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return {
            f.name: to_jsonable(getattr(obj, f.name)) for f in dataclasses.fields(obj)
        }
    if isinstance(obj, Path):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Enum):
        return to_jsonable(obj.value)
    if isinstance(obj, dict):
        return {str(k): to_jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set, frozenset)):
        return [to_jsonable(v) for v in obj]
    return str(obj)
