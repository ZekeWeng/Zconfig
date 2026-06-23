# Working style

Behavioral guidelines that bias toward caution over speed. For trivial tasks, use judgment. These complement the code-shape rules in `general.md` and the architectural rules in `architecture.md` — they govern **how** you work, not what the code looks like.

## Think before coding

Don't assume. Don't hide confusion. Surface tradeoffs.

- State assumptions explicitly before implementing — if uncertain, ask
- If multiple interpretations exist, present them — never pick silently
- If a simpler approach exists, say so — push back when warranted
- If something is unclear, stop, name what's confusing, and ask

## Simplicity first

Minimum code that solves the problem. Nothing speculative.

- Write the simplest code that solves the problem — no speculative abstractions
- No features beyond what was asked
- No abstractions for single-use code — three similar lines beat a premature abstraction
- No "flexibility," configurability, feature flags, or extension points until a second use case exists
- No error handling for impossible scenarios
- Delete dead code — don't comment it out or leave `// removed` markers
- If 200 lines could be 50, rewrite it
- Senior-engineer check: "Would they call this overcomplicated?" If yes, simplify

## Surgical changes

Touch only what you must. Clean up only your own mess.

- Don't "improve" adjacent code, comments, or formatting
- Don't refactor things that aren't broken
- Match existing style, even if you'd do it differently
- If you notice unrelated dead code, mention it — don't delete it
- Remove imports/variables/functions that **your** changes orphaned
- Don't remove pre-existing dead code unless asked
- The test: every changed line should trace directly to the user's request

## Goal-driven execution

Define success criteria up front. Loop until verified.

Transform tasks into verifiable goals:
- "Add validation" → "Write tests for invalid inputs, then make them pass"
- "Fix the bug" → "Write a test that reproduces it, then make it pass"
- "Refactor X" → "Ensure tests pass before and after"

For multi-step tasks, state a brief plan before starting:

```
1. <step> → verify: <check>
2. <step> → verify: <check>
3. <step> → verify: <check>
```

Strong success criteria let you loop independently. Weak criteria ("make it work") require constant clarification.

## Signal that these are working

- Fewer unnecessary changes in diffs
- Fewer rewrites caused by overcomplication
- Clarifying questions arrive **before** implementation, not after mistakes
