# Audit rounds

Each audit round lives in `audits/<yyyy-mm-dd>/` (a suffix such as `2026-10-01_security` is fine) and follows the
shared format checked by `py_ci_shared.audit_round_format`:

* every finding is a `### <ID> (<severity>) -- <title>` heading (`SEC-1`, `PERF-3` ...), followed by a
  `**Disposition:** RESOLVED|WON'T FIX|DEFERRED|NOT A DEFECT -- <reason>` line; continuation headings go at `####`;
* the round keeps a `TRACKER.md` with one table row per finding and a `Disposition` column;
* once every row is closed the round moves, unchanged, to `audits/implemented/<yyyy-mm-dd>/`.

`TRACKER.md` in this directory is the index across rounds: one row per round. No round has been run yet.
