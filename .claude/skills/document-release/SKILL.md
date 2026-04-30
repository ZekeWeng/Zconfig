---
name: document-release
description: Update project documentation to match what was just shipped. Catches stale READMEs, outdated CLI help, orphaned config docs.
argument-hint: "[optional: PR number or commit range like 'origin/main..HEAD']"
allowed-tools: Bash, Read, Edit, Glob, Grep
disable-model-invocation: true
---

# Document Release

## Context

### Changes to document
!`if [ -n "$ARGUMENTS" ] && echo "$ARGUMENTS" | grep -qE '^[0-9]+$'; then gh pr diff $ARGUMENTS 2>/dev/null; elif [ -n "$ARGUMENTS" ]; then git log --stat "$ARGUMENTS"; else git log origin/HEAD..HEAD --stat 2>/dev/null || git log -10 --stat; fi`

## Scan for stale docs

From the diff above, identify changed behavior. Then check each of these surfaces for staleness:

1. Top-level `README.md` — feature lists, install steps, quick-start commands
2. `docs/` tree (if present) — any page that mentions a changed symbol
3. Inline CLI `--help` strings — for any CLI whose flags or subcommands changed
4. `.env.example` — if any env var was added/renamed/removed
5. `.claude/rules/*.md` — if coding conventions shifted
6. `.claude/skills/*/SKILL.md` — if skill behavior or arguments changed
7. `install.sh` and `setup/*.sh` comments — if install flow changed
8. `Makefile` targets — if a new entry point was added

## Update

For each stale doc, make the minimal edit to match reality. Rules:

- Never invent features that weren't shipped.
- Preserve the tone and structure of the existing doc.
- Prefer editing an existing section to adding a new one.
- If a doc is irreparably outdated (wrong framing, not just wrong details), flag for human rewrite — don't try to salvage.

## Output

- **Updated**: file list, one-line reason each
- **Already current**: files checked and clean
- **Flagged for human**: docs that need a rewrite, not an edit
