"""Audit rounds under ``audits/`` stay countable by machine: ``py_ci_shared.audit_round_format``.

No round has been run in this repo yet, so the round checks below run over an empty set on purpose; what is checked
today is that the layout they read exists: ``audits/`` with its README and a cross-round ``TRACKER.md`` whose table
the shared parser finds. The first dated round is then held to the full format from the day it lands.
"""

from __future__ import annotations

import re
from pathlib import Path

from py_ci_shared.audit_round_format import assert_rounds_filed, finding_problems, round_files, tracker_status_cells

AUDITS = Path(__file__).resolve().parents[1] / "audits"
# The round-directory naming the shared checks select on.
DATED = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _round_dirs() -> list[Path]:
    return [d for parent in (AUDITS, AUDITS / "implemented") if parent.is_dir() for d in parent.iterdir() if d.is_dir() and DATED.match(d.name)]


def test_audits_layout_exists() -> None:
    assert (AUDITS / "README.md").is_file(), f"{AUDITS}/README.md is missing"
    rows = tracker_status_cells(AUDITS / "TRACKER.md")
    # None means no table with a Disposition/Status column parsed: every count over the tracker would read zero.
    assert rows is not None, f"{AUDITS}/TRACKER.md has no table with a Disposition or Status column"
    assert len(rows) == len(_round_dirs()), f"TRACKER.md lists {len(rows)} round(s) but {len(_round_dirs())} dated round directories exist"


def test_rounds_are_countable() -> None:
    files = round_files(AUDITS)
    assert len({f.parent for f in files}) == len(_round_dirs()), "a dated round directory holds no .md findings file"
    cache: dict[tuple[str, str], bool] = {}
    problems: list[str] = []
    for path in files:
        found = finding_problems(path, dir_cache=cache)
        if found is None:
            problems.append(f"{path.parent.name}: no finding carries a **Disposition:**, so nothing in it can be counted")
        else:
            problems.extend(found)
    assert not problems, "\n  ".join(["audit rounds that cannot be counted:", *sorted(set(problems))])


def test_rounds_are_filed_where_their_trackers_say() -> None:
    # min_trackers follows the rounds on disk: 0 while there are none, and every dated round needs its TRACKER*.md.
    assert_rounds_filed(AUDITS, min_trackers=len(_round_dirs()))
