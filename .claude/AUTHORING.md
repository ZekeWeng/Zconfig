# Authoring rules & skills

How to write and format the files in `.claude/rules/` and `.claude/skills/`. This
guide is the standard those files conform to. It lives in `.claude/` — **not**
`.claude/rules/` — on purpose: every `.md` under `rules/` auto-loads into context
each session, so a guide placed there would burn tokens for nothing.

## How they load (why structure matters)

| Mechanism | Loads when | Use for |
|-----------|-----------|---------|
| `rules/*.md`, no frontmatter | Every session, like `.claude/CLAUDE.md` | Always-on principles |
| `rules/*.md` with `paths:` frontmatter | Only when Claude touches matching files | Language- or area-specific rules |
| `skills/<name>/SKILL.md` | On `/invoke`, or automatically if model-invocable | Multi-step procedures |

Rules are **context, not enforcement** — a later instruction can override them, and
contradictory rules get resolved arbitrarily. Keep them specific, concise, and
non-conflicting. For hard enforcement (must run before every commit, etc.), use a hook.

Sources: [memory docs](https://code.claude.com/docs/en/memory) ·
[skill best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

## Rule template

```
---
# Include ONLY for path-scoped rules. Omit entirely for always-on rules.
paths:
  - "engine/**/*.py"
---

# <Topic>

<One sentence: what this rule governs and when it applies.>

## <Section>
- <Imperative, verifiable bullet — "Use X, not Y" / "Never Z">

## Sources        (optional — only when codifying an external spec)
- [Title](url)
```

- **Always-on** rule → no frontmatter. **Path-scoped** → `paths:` with quoted globs
  (`"**/*.py"`); brace-expand multiple extensions as `"src/**/*.{ts,tsx}"`.
- H1 is a plain noun phrase — no decorative `— subtitle`.
- One-line purpose under the H1 so Claude knows the rule's remit at a glance.
- H2 sections grouped general → specific; one concept per bullet.
- Tables for enumerations (layers, commit types). **Bold** only the operative word.
- Target ≤ 80 lines; scope or split anything longer.

## Skill template (command class)

For user-invoked `/commands` (`commit`, `ship`, `review`, …):

```
---
name: <imperative, lowercase-hyphen, ≤64 chars, no "claude"/"anthropic">
description: <third person; what it does + when to use; ≤1024 chars>
argument-hint: "[what to pass]"
allowed-tools: <minimal set>
disable-model-invocation: true   # user-only command skills
# context: fork                  # optional: run in an isolated subagent
# agent: <type>                  # optional: only meaningful with context: fork
---

# <Title>

<Optional one-line intent + cross-ref to the rule it follows.>

## Context        (only if it injects state; quote "$ARGUMENTS" in any bash)
- <label>: !`<cmd>`

## Steps
1. <numbered, imperative>

## Rules / Hard stops
- <guardrails — "Never …">

## Output
- <what to return>
```

- Frontmatter order: `name → description → argument-hint → allowed-tools →
  disable-model-invocation → context → agent → model`.
- Body ≤ 500 lines; push detail into sibling files referenced one level deep.
- Quote `"$ARGUMENTS"` (or guard numerics) in injected bash; prefer indexed `$1`;
  use quoted heredocs (`<<'EOF'`) for PR bodies.

## Skill template (capability class)

For skills the model should auto-invoke (e.g. `tutor`):

- **Omit** `disable-model-invocation`.
- Write a verbose, third-person `description` with explicit trigger phrases and a
  "Use when… / Do NOT use when…" clause — that text is what drives auto-selection.
- Organize the body around principles + a workflow loop rather than Context/Steps.

## Naming, ordering, layout

- **Rules:** kebab-case topic noun (`git-workflow.md`, `testing.md`).
- **Skills:** imperative verb matching its `/command` (`commit`, `ship`).
- **In-file order:** frontmatter → H1 → purpose line → H2 sections → optional Sources.
- **Layout:** flat directories while ≤ ~12 files; add subdirectories only if it grows.

## Markdown conventions

- One H1; H2 for sections; sentence-case headers; bullets over paragraphs.
- Tables for enumerations; fenced blocks for templates, examples, and commands.
- Em-dash for asides (house style). No trailing "Sources" unless citing a spec.
