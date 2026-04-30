---
name: retro
description: Weekly engineering retrospective. Surfaces shipping streak, stuck PRs, and fragile zones that needed rework.
argument-hint: "[optional: range like '7 days' or '2026-04-15..2026-04-22']"
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
context: fork
---

# Retro: ${ARGUMENTS:-last 7 days}

## Data

### Commits in range
!`RANGE="${ARGUMENTS:-7 days}"; git log --since="$RANGE ago" --pretty=format:"%ad %h %s" --date=short 2>/dev/null | head -80`

### PRs merged in range
!`gh pr list --state merged --search "merged:>$(date -v-7d +%Y-%m-%d 2>/dev/null || date -d '7 days ago' +%Y-%m-%d)" --json number,title,mergedAt,author --limit 30 2>/dev/null | head -60`

### Open drafts
!`gh pr list --state open --draft --json number,title,createdAt --limit 20 2>/dev/null`

### Fix-on-fix signal (commits whose subject references a fix)
!`git log --since="${ARGUMENTS:-7 days} ago" --grep="^fix" --pretty=format:"%h %s" 2>/dev/null | head -30`

## Analyze

1. **Shipped** — what actually merged. Group by area (nvim / zsh / scripts / claude / ...).
2. **Stuck** — open drafts older than 7 days. For each, name the likely blocker (tests? review? scope creep?).
3. **Fragile zones** — files or modules that needed more than one fix commit in the range. These are the hotspots to stabilize next.
4. **Streak** — consecutive days with at least one commit.
5. **What's new in the stack** — skills, rules, or tooling added in the range that changed how work gets done.

## Output

- **Shipped this period**: bullets grouped by area
- **Stuck**: each draft + likely blocker
- **Fragile zones**: files/modules ranked by fix-commit count
- **Streak**: N days
- **One question for next period**: the single decision that would unblock the biggest stuck item

## Rules

- Don't invent reasons for why something's stuck — if the signal isn't clear, say "unclear — ask."
- Keep it to one screen. Retros that scroll don't get read.
