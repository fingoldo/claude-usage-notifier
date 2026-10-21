"""The pyutilz code_audit scanners find nothing in this repository.

There is no advisory tier: a finding either blocks or is fixed, or it is suppressed at its site with
``# audit-exempt: <check> -- <reason>``. A new scanner that fires here is a real defect or a new exemption to justify.
"""

from __future__ import annotations

from pathlib import Path

from pyutilz.dev.code_audit import registry

ROOT = Path(__file__).resolve().parents[1]


def test_code_audit_finds_nothing() -> None:
    findings = registry.run_all_checked(ROOT)[0]
    assert findings == [], "\n".join(f"{f.check} {f.file}:{f.line} {f.summary}" for f in findings)
