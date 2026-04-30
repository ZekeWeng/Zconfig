---
name: refactor
description: Behavior-preserving code restructure. Runs tests before and after — refuses to proceed if the baseline is red.
argument-hint: "[target file/function/module and the desired restructure]"
allowed-tools: Bash, Read, Edit, Glob, Grep
disable-model-invocation: true
---

# Refactor: $ARGUMENTS

## Invariant

**A refactor does not change behavior.** Every test that passed before must pass after. Every observable effect must remain the same. If you're changing what the code does, that's a feature change — use a different skill.

## Steps

1. **Baseline.** Run the project's test command. If anything is red, **stop** — fix the failing test first (separately), then resume.
2. **Restructure.** Apply the minimal change described in $ARGUMENTS. No feature additions. No API surface changes. No "while I'm here" fixes.
3. **Re-test.** Run the test command again. Every baseline-passing test must still pass.
4. **Diff review.** Run `git diff`. Every hunk should be pure restructure — extraction, renaming, reordering, dedup. If you see added branches or new logic, revert those hunks.

## Hard Stops

- Baseline tests fail → stop, do not refactor. Report which test failed.
- Re-test reveals a regression → revert, report which test broke.
- Scope creep appears mid-refactor → revert the creep, keep the core restructure, note the follow-up.

## Output

- **Baseline**: N tests passing before
- **Changes**: one line per file touched
- **Re-test**: N tests passing after (must equal baseline)
- **Follow-ups**: anything surfaced that shouldn't land in this refactor
