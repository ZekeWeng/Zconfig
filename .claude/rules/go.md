---
paths:
  - "**/*.go"
  - "**/go.mod"
  - "**/go.sum"
---

# Idiomatic Go (1.22+)

## Interfaces

- Accept interfaces, return concrete types. Callers constrain input; producers keep flexibility.
- Define interfaces in the consuming package, not the implementing one. The consumer owns the contract.
- Keep interfaces 1–3 methods. Large interfaces are a design smell (`io.Reader` is the archetype).
- Do not create an interface until you have a second implementation or a real mocking need. "The bigger the interface, the weaker the abstraction."
- Use `var _ Iface = (*Impl)(nil)` for compile-time conformance checks on exported implementations.

## Error Handling

- Wrap with `fmt.Errorf("doing X: %w", err)` to preserve the chain. Use `%v` only when intentionally obscuring.
- Use `errors.Is` for sentinel comparison and `errors.As` for typed extraction. Never string-match on `.Error()`.
- Sentinel `ErrFoo` for static conditions; typed errors (`type NotFoundError struct{...}`) when callers need context.
- Handle an error exactly once: either log-and-stop or wrap-and-return, never both.
- Error strings are lowercase and unpunctuated so they compose when wrapped (`"open config: permission denied"`).
- Never `panic` in a library. Reserve panic for truly unrecoverable programmer bugs.
- Collapse `if err != nil { return err }` ladders with early returns. Never use `else` for the happy path.

## Concurrency

- Every goroutine must have a known owner and a known termination condition. No fire-and-forget.
- Keep functions synchronous; let the caller decide concurrency. Concurrency is an implementation detail.
- Use `golang.org/x/sync/errgroup` for fan-out with cancellation and error propagation. Default over raw `sync.WaitGroup`.
- Share memory by communicating (channels) for ownership transfer. Use `sync.Mutex` for protecting small fields. Pick the simpler one.
- Unbuffered or size-1 channels only. Any other buffer size needs a written justification.
- Close channels on the sender side, never the receiver. Never close a channel you don't own.
- Use `context.Context` cancellation — not a separate `done` channel — for graceful shutdown.

## Context

- `ctx context.Context` is always the first parameter. Never store it in a struct field.
- Pass `context.Background()` only at program entry points (`main`, tests). Derive everywhere else.
- Always `defer cancel()` from `WithCancel`/`WithTimeout`/`WithDeadline`. Leaked cancellations leak goroutines.
- Pass a deadline with every outbound RPC/DB/HTTP call. Unbounded calls are bugs waiting to happen.
- `context.Value` is for request-scoped data (trace IDs, auth), not for passing optional arguments.

## Struct Composition

- Prefer embedding for "has-a plus method forwarding." Do not embed to simulate inheritance.
- Keep structs shallow. More than two levels of embedding obscures method resolution.
- Export fields when the zero value is usable. Require a constructor (`NewX`) when invariants must hold.
- Pointer receiver when the method mutates, the struct is large, or the type has a pointer receiver anywhere. Then use it consistently for every method on the type.

## Generics (1.18+)

- Reach for generics only when the alternative is runtime type assertion, code duplication, or `reflect`.
- Use generics for container/algorithm code (`slices`, `maps`, `sync/atomic.Pointer[T]`). Keep interfaces for behavior polymorphism.
- Prefer stdlib constraints (`cmp.Ordered`, `comparable`) over hand-rolled ones.
- If a generic signature needs more than two type parameters, the abstraction is probably wrong.

## Package Design

- Name packages for what they provide (`http`, `parse`). Never by role (`utils`, `common`, `helpers`, `models`, `types`).
- One concept per package. Import cycles mean you've drawn the boundary wrong, not that Go is broken.
- Put truly private code under `internal/`. Everything else is part of your API contract.
- Prefer fewer, larger packages over deep trees. Go's only access modifiers are upper/lower-case.
- Package names are lowercase, no underscores, singular, and short. Callers prepend the name at every use site.

## Testing

- Table-driven tests with `t.Run(tc.name, ...)`. Subtests give selective reruns and clear failure output.
- Call `t.Parallel()` in leaf tests. In Go 1.22+ the loop variable is per-iteration — no `tc := tc` dance needed.
- Prefer stdlib `testing` + `cmp.Diff` over testify. Assertion DSLs hide which line failed and bury diffs.
- Put fixtures in `testdata/` (Go ignores it in builds). Use golden files with a `-update` flag for large expected outputs.
- `t.Helper()` in test helpers so failures report the caller's line. `t.Cleanup` instead of hand-rolled defers.
- No global state in tests. Use `t.TempDir()`, `t.Setenv`, fresh fixtures per test.

## Performance

- Profile first (`pprof`, `testing.B` benchmarks). Never optimize from intuition.
- Pre-size slices and maps when the cap is known (`make([]T, 0, n)`). Avoids rehashing/regrowth.
- Use `sync.Pool` only for hot, short-lived allocations with measurable GC pressure. Easy to misuse.
- Avoid `any`/`interface{}` in hot paths. Boxing allocates and defeats inlining.
- Prefer `strconv` over `fmt` for primitive conversions (2–3× faster). Reuse `[]byte` buffers instead of re-converting from strings.

## Go 1.22+ Features to Prefer

- `log/slog` for structured logging. Retire `log`, logrus, zap-for-new-code.
- `slices` and `maps` packages (`slices.Sort`, `slices.Contains`, `maps.Keys`) instead of hand-rolled loops.
- Range-over-int (`for i := range 10`) for counted loops. Range-over-func (1.23) for custom iterators returning `iter.Seq[T]`.
- Rely on 1.22's per-iteration loop variable scoping. Closures and goroutines capture correctly by default.
- `http.ServeMux` patterns with methods and wildcards (`"GET /users/{id}"`) instead of third-party routers for simple services.

## Anti-Patterns

- Naked `return` in any function longer than a few lines. Named returns as documentation only.
- `interface{}`/`any` as a "flexible" parameter type. If you don't know the type, neither does the caller.
- Side-effectful `init()` functions (registering globals, opening connections). Construct explicitly in `main`.
- Dot imports (`import . "pkg"`) outside of test files.
- `GetFoo()` getters. Call it `Foo()`. Reserve `Get` for operations that do real work.
- Ignoring errors with `_` without a comment explaining why it's safe.
- Global mutable state. Pass dependencies through constructors.
- `math/rand` for anything security-adjacent. Use `crypto/rand`.

## Sources

- [Effective Go](https://go.dev/doc/effective_go)
- [Go Code Review Comments](https://go.dev/wiki/CodeReviewComments)
- [Google Go Style Decisions](https://google.github.io/styleguide/go/decisions.html)
- [Uber Go Style Guide](https://github.com/uber-go/guide/blob/master/style.md)
- [Dave Cheney — Practical Go](https://dave.cheney.net/practical-go/presentations/qcon-china.html)
