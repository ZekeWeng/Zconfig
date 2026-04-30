---
name: fix-issue
description: Fix a GitHub issue by number. Reads the issue, implements a fix, writes tests, and creates a PR.
argument-hint: "[issue-number]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
disable-model-invocation: true
---

# Fix GitHub Issue $ARGUMENTS

## Context
- Issue details: !`gh issue view $ARGUMENTS 2>/dev/null || echo "Could not fetch issue $ARGUMENTS — provide details manually."`

## Steps

1. Read and understand the issue above
2. Explore the relevant code to understand the root cause
3. Implement the fix with minimal, focused changes
4. Write or update tests that cover the fix
5. Run the test suite to verify nothing is broken
6. Create a commit with a descriptive message referencing the issue
7. Create a PR linking the issue

## Rules
- Keep changes minimal — only fix what the issue describes
- Always write a failing test first when possible
- Reference the issue number in the commit message (e.g., "Fixes #$ARGUMENTS")
