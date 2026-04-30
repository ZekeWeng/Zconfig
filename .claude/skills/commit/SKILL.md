---
name: commit
description: Write a conventional commit from staged changes. Groups by concern — refuses to bundle formatting with logic.
argument-hint: "[optional: scope hint]"
allowed-tools: Bash, Read
disable-model-invocation: true
---

# Commit

## Context
- Staged diff: !`git diff --cached`
- Unstaged: !`git diff --stat`
- Recent log: !`git log --oneline -10`
- Scope hint: $ARGUMENTS

## Steps

1. Inspect the staged diff. Group hunks by concern — if formatting and logic are mixed, stop and report.
2. Pick the single `<type>` that fits per `.claude/rules/git-workflow.md`. Never combine types.
3. Write a subject line under 50 chars. The body explains **why**, not what.
4. Create the commit. Print the result of `git log -1` to confirm.

## Rules

- One concern per commit. If the staged diff spans multiple concerns, report and ask the user to re-stage.
- Never use `-a` / `--all` — only commit what's explicitly staged.
- Never `--amend` a pushed commit unless the user explicitly asks.
- Never bypass hooks (`--no-verify`, `--no-gpg-sign`) unless the user explicitly asks.
