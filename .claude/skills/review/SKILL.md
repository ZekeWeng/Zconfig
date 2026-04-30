---
name: review
description: Perform a thorough code review on staged changes or a PR.
argument-hint: "[PR-number-or-blank-for-staged]"
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
context: fork
agent: general-purpose
---

# Code Review

## Context

### Changes to review
!`if [ -n "$ARGUMENTS" ]; then gh pr diff $ARGUMENTS; else git diff --cached; fi`

### PR description (if applicable)
!`if [ -n "$ARGUMENTS" ]; then gh pr view $ARGUMENTS; else echo "Reviewing staged changes (no PR)."; fi`

## Review Checklist

Analyze the changes above for:

1. **Correctness**: Logic errors, off-by-one, null/undefined handling, race conditions
2. **Security**: Injection vulnerabilities, exposed secrets, auth bypasses, OWASP top 10
3. **Performance**: N+1 queries, unnecessary allocations, missing indexes, unbounded loops
4. **Maintainability**: Naming clarity, dead code, missing error handling, code duplication
5. **Tests**: Adequate coverage, edge cases, test quality

## Output Format

For each finding, provide:
- **Severity**: critical / warning / nit
- **File:line**: exact location
- **Issue**: what's wrong
- **Suggestion**: how to fix it

End with a summary: approve, request changes, or needs discussion.
