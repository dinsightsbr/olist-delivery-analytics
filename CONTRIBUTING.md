# Contributing

Small project, strict habits.

1. **Branch from `main`**, name it `feat/...`, `fix/...` or `docs/...`.
2. **The generator is the source of truth for the report.** Change `powerbi/build_pbip.py`, run it,
   then `python powerbi/validate_pbip.py`. If you edited something in Power BI Desktop, port the change
   into the generator before opening the PR (the `pbip-validate` job warns on drift).
3. **SQL changes** go through `sqlfluff lint sql` locally (`pre-commit install` does it on commit) and
   must keep every query in `sql/90_checks.sql` returning `TRUE`.
4. **Business rules** change in exactly one place (`sql/30_marts.sql`), and `docs/findings.md`,
   `powerbi/measures.md` and the appendix page follow.
5. **Open a pull request** with the template filled in. CI posts the semantic-model diff and the AI SQL
   review; the owner reviews and merges with a linear history.

Commit messages use [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`,
`docs:`, `ci:`, `chore:`).
