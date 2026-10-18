## What and why

<!-- One paragraph: the business question or defect, and the change. Link the issue if any. -->

## Model changes

- [ ] No semantic model change
- [ ] Tables / columns changed (list):
- [ ] Measures added / changed (the `model-diff` comment on this PR lists them)
- [ ] Business rule changed → `docs/findings.md` and `powerbi/measures.md` updated

## Evidence

<!-- Reconciliation query result (sql/90_checks.sql) and, for report changes, before/after screenshots. -->

## Checklist

- [ ] `python powerbi/build_pbip.py` re-run and committed (the generator is the source of truth)
- [ ] `python powerbi/validate_pbip.py` passes locally
- [ ] `sqlfluff lint sql` passes locally
- [ ] Numbers reconciled against `OLIST.MARTS.V_KPI_MONTHLY`
