from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .model import VerifyReport


def write_receipt(root: Path, relpath: str, report: VerifyReport) -> Path:
    path = root / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ok": report.ok,
        "report": report.to_dict(),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def read_receipt(root: Path, relpath: str) -> dict | None:
    path = root / relpath
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))
