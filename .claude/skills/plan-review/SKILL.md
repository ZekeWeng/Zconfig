---
name: plan-review
description: Engineering review of a plan. Locks architecture, data flow, edge cases, and tests. Forces hidden assumptions into the open.
argument-hint: "[path-to-plan.md or inline plan description]"
allowed-tools: Read, Glob, Grep
disable-model-invocation: true
context: fork
---

# Plan Review: $ARGUMENTS

Review the plan above in five passes. Don't skip passes — each one catches a different class of defect.

## Pass 1: Architecture

- Does the plan respect `.claude/rules/architecture.md` (hex / ports & adapters)?
- Which layer does each new component live in — core, port, or adapter?
- Are dependencies pointing inward? Flag any inward-leaking adapter type.

## Pass 2: Data Flow

- Write the data path in prose: input → adapter → port → core → port → adapter → output.
- Where does validation happen? (Boundaries only, per `.claude/rules/general.md`.)
- Where does mutable state live? Who owns it?

## Pass 3: Edge Cases

List the edges the plan currently does **not** handle:
- Empty / max-size / malformed inputs
- Concurrent callers
- Partial failures — retry semantics? idempotency?
- Timeouts, disk full, process killed mid-operation
- Migration/upgrade paths for existing data

## Pass 4: Hidden Assumptions

Call out every assumption the plan relies on. For each: "What if this isn't true?"
- Invariants about data shape or ordering
- Availability of external systems
- Performance assumptions (latency, throughput, memory)
- Cardinality ("we'll only ever have N of X")

## Pass 5: Tests

For each new unit, name the test(s) that would verify it. Structure per `.claude/rules/testing.md`:
- Core: pure unit tests, no mocks
- Ports: contract tests
- Adapters: integration tests against real systems

## Output

- **Architecture verdict**: pass / needs-changes (with specifics)
- **Missing edge cases**: bulleted list
- **Hidden assumptions**: bulleted list, ranked by risk
- **Test plan**: one line per test, grouped by layer
- **Overall**: approve / revise / re-scope
