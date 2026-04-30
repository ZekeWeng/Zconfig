---
name: ship
description: Sync base, run tests, push the current branch, open a draft PR on GitHub. Stops on test failures — never ships red.
argument-hint: "[optional: PR title]"
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
---

# Ship

## Preflight

!`git status --short`
!`git rev-parse --abbrev-ref HEAD`
!`git log --oneline @{upstream}..HEAD 2>/dev/null || echo "(no upstream or no new commits)"`

## Steps

1. **Detect default branch.**
   ```bash
   default=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null | sed 's|^origin/||')
   ```
   If unset, stop and ask — never guess.

2. **Sync.** `git fetch origin`. If the current branch is behind `origin/$default`, rebase onto it. If conflicts, stop — rebasing is the user's call to resolve.

3. **Test.** Detect the project test command (`package.json` scripts, `Makefile`, `justfile`, `pytest`, `go test ./...`, `cargo test`). Run it. **If tests fail, stop and report.** Never ship red.

4. **Self-review.** Run `git diff origin/$default..HEAD`. Confirm:
   - No debug prints (`console.log`, `print()`, `dbg!`)
   - No commented-out code blocks
   - No stray files (`.DS_Store`, `*.swp`, editor backups)
   - No secrets in the diff

5. **Push.** `git push -u origin $(git rev-parse --abbrev-ref HEAD)`.

6. **Open draft PR.**
   ```bash
   gh pr create --draft \
     --title "${ARGUMENTS:-<synthesize from commit subjects>}" \
     --body "$(cat <<'EOF'
   ## Summary
   <1–3 bullets of what this changes>

   ## Test plan
   - [ ] <how to verify the change manually>
   - [ ] <relevant test file that covers the change>
   EOF
   )"
   ```

7. **Verify.** Print the PR URL so the user can open it.

## Rules

- **Draft by default.** Mark ready-for-review only when the user explicitly asks.
- **Never force-push** shared branches.
- **Never skip tests.** If the repo has no test suite, report that and ask whether to proceed.
- **PR body must include a test plan.** A summary alone is not enough.
- Test plans should state how a human would verify — not just "ran the tests."
