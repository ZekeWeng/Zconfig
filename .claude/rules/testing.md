---
paths:
  - "**/*test*"
  - "**/*spec*"
  - "**/__tests__/**"
  - "**/*_test.*"
---

# Testing Rules

## Test Architecture (Aligned with Hex)

- **Core/domain tests**: Pure unit tests — no mocks, no I/O, no setup. If core logic needs mocks to test, the dependency direction is wrong.
- **Port tests**: Contract tests that verify any adapter implementing the port satisfies the expected behavior.
- **Adapter tests**: Integration tests that hit real external systems (DB, filesystem, APIs) — mocks here hide real bugs.
- **End-to-end tests**: Wire everything through the composition root and test full flows sparingly.

## Test Quality

- Each test verifies **one behavior** — name it as a sentence describing that behavior
- Tests must be independent — no shared mutable state, no ordering dependencies
- Structure every test as arrange / act / assert — keep each section visually distinct
- Prefer realistic test data over trivial placeholder values (`"jane@example.com"` not `"test"`)
- Test error paths and edge cases, not just happy paths
- A test that never fails is not testing anything — verify it can actually catch a regression

## What Not to Do

- Don't mock what you own — if you control the code, test it directly
- Don't test implementation details (private methods, internal state) — test behavior through public interfaces
- Don't write tests that duplicate the implementation logic — that just locks in bugs
- Don't ignore flaky tests — fix them or delete them, never skip and forget
