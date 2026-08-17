"""Desktop shell: pywebview window, JS bridge, and DTO marshalling.

Holds no business logic — every computation lives in `norefund.core`. This
package only creates the window, exposes `core` to JavaScript, and converts
dataclasses to JSON-safe dicts.
"""

from __future__ import annotations
