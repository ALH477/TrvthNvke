from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ClaimKind(str, Enum):
    FILE_EXISTS = "file_exists"
    DIR_EXISTS = "dir_exists"
    GLOB_COUNT = "glob_count"
    FILE_CONTAINS = "file_contains"
    JSON_POINTER = "json_pointer"
    TOML_KEY = "toml_key"
    COMMAND = "command"
    HEADING = "heading"
    REL_LINK = "rel_link"
    VERSION_SYNC = "version_sync"
    PYTHON_SYMBOL = "python_symbol"
    ENTRYPOINT = "entrypoint"
    PROSE = "prose"  # bound prose with no machine check; still tracked


ALLOWED_KINDS = {k.value for k in ClaimKind}


@dataclass
class Claim:
    id: str
    kind: str
    source: str  # "block" | "fence" | "policy"
    path: str  # document path
    start_line: int
    end_line: int
    severity: str = Severity.ERROR.value
    attrs: dict[str, Any] = field(default_factory=dict)
    body: str = ""
    ignored: bool = False

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        return d


@dataclass
class Finding:
    claim_id: str | None
    path: str
    line: int
    severity: str
    code: str
    message: str
    evidence: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class VerifyReport:
    ok: bool
    docs: list[str]
    claims: int
    checked: int
    passed: int
    failed: int
    warnings: int
    findings: list[Finding]
    receipts: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "docs": self.docs,
            "claims": self.claims,
            "checked": self.checked,
            "passed": self.passed,
            "failed": self.failed,
            "warnings": self.warnings,
            "findings": [f.to_dict() for f in self.findings],
            "receipts": self.receipts,
        }
