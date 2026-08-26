<!-- A clear PR description is the team's real changelog — /catchup and teammates read these. Explain the what and the why. -->

## Summary

<!-- What does this change and why? Link the spec (docs/superpowers/specs/) or ADR (docs/decisions/) if there is one. -->

## Shared-context checklist

- [ ] Does this change a convention in `CLAUDE.md` or `.claude/rules/`? If yes, update it in this PR.
- [ ] Does this warrant an ADR in `docs/decisions/` (a non-obvious architectural decision)? If yes, add one.
- [ ] Docs updated and `mkdocs build --strict` passes (if `docs/` changed).
- [ ] BigQuery/proc changes are oracle-gated (`0,0,0`) and don't touch live R2 without explicit sign-off.
