# General Coding Standards

## Simplicity First

- Write the simplest code that solves the problem — no speculative abstractions
- Three similar lines are better than a premature abstraction
- Don't add configurability, feature flags, or extension points until a second use case exists
- Delete dead code — don't comment it out or leave `// removed` markers

## Naming and Clarity

- Names are the primary documentation — make them precise and descriptive
- Functions: verb phrases that describe what they do (`parseConfig`, `validateEmail`)
- Booleans: `is`, `has`, `should`, `can` prefixes (`isValid`, `hasPermission`)
- Avoid generic names: `data`, `info`, `item`, `result`, `handle`, `process`, `manager`
- If a name needs a comment to explain it, the name is wrong

## Functions and Modularity

- Each function does **one thing** — if you use "and" to describe it, split it
- Functions should be short enough to read without scrolling
- Limit parameters to 3 — group related params into a config/options object beyond that
- Pure functions over stateful methods where possible — easier to test and reason about
- Compose small functions rather than writing long procedural blocks

## Error Handling

- Handle errors explicitly at every level — never swallow exceptions silently
- Fail fast at system boundaries (user input, API responses, file I/O) with clear error messages
- Internal code can trust validated data — don't re-validate at every layer
- Use typed/structured errors where the language supports it — not bare strings

## Code Organization

- Group by feature/domain, not by technical role (prefer `users/repo.ts` over `repos/userRepo.ts`)
- Keep related code close together — minimize the number of files you need open to understand a feature
- Prefer editing existing files over creating new ones — file proliferation is a code smell
- Never commit secrets, credentials, or API keys — use environment variables
