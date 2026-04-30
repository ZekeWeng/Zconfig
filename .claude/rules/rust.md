---
paths:
  - "**/*.rs"
  - "**/Cargo.toml"
  - "**/Cargo.lock"
---

# Idiomatic Rust (2024 edition, 1.85+)

## Ownership & Borrowing

- Accept `&str`, not `&String`. Accept `&[T]`, not `&Vec<T>`. Strict supersets with zero constraints on the caller's allocation.
- Return owned types (`String`, `Vec<T>`) from constructors/builders. Take borrows in consumers — "consumers borrow, producers own."
- Use `Cow<'a, str>` when a function sometimes borrows and sometimes allocates (normalization, escaping). Avoids forcing allocation in the common path.
- Never `.clone()` to appease the borrow checker. Restructure scopes, split `&mut` lifetimes (NLL lets you reborrow), or pass ownership.
- Prefer `impl Into<String>` / `impl AsRef<Path>` only at API edges. Internally settle into one canonical type.

## Error Handling

- Libraries: define a typed error enum with `thiserror`. Use `#[source]`/`#[from]` on every wrapped cause so `Error::source()` chains survive.
- Applications: use `anyhow::Result<T>` and `.context("reading config")` at every boundary. The chained context *is* your stack trace.
- Convert errors with `?`. Never match-and-rewrap when `From` already exists.
- `panic!`/`unwrap`/`expect` is acceptable only for violated *internal* invariants. Never for user input, I/O, or parsing. Prefer `expect("why this cannot fail")` so the message documents the invariant.
- Do not expose `Box<dyn Error>` in library public APIs. Callers lose the ability to match variants.

## Option Patterns

- `Option<T>` over sentinels. Reach for combinators (`.map`, `.and_then`, `.ok_or_else`, `.unwrap_or_default`) before writing `match`.
- Use `let ... else { return ...; }` for refutable binds with early exit. Flattens nested `if let`.
- Use `if let` chains with `&&` (Rust 2024 edition) to avoid pyramid matching.
- `.ok_or_else(|| err)` over `.ok_or(err)` when constructing the error is non-trivial. Lazy evaluation.
- Never `.unwrap()` in production paths. `#![deny(clippy::unwrap_used, clippy::expect_used)]` in binaries is a strong default.

## Trait Design

- Prefer `impl Trait` in argument position for simple generic fns. Switch to `<T: Trait>` only when you need to name or reuse the type parameter.
- Use associated types when there is one canonical impl per type (`Iterator::Item`). Use generic parameters when multiple impls make sense (`From<T>`).
- Reach for `dyn Trait` when you need heterogeneous collections or to minimize binary size. Use generics (monomorphization) when hot-path performance matters.
- Apply the newtype pattern to gain orphan-rule freedom and unit safety (`struct UserId(u64)`). Zero runtime cost.
- Keep traits object-safe (no generic methods, `Self: Sized` fences) when `dyn` use is plausible. `async fn` and RPIT in traits are stable (1.75+) but are not dyn-compatible — use `async_trait` for dynamic dispatch or refactor to concrete types.
- Do not write Java-style getters/setters. Expose fields as `pub` on plain data, or return `&T` from a single accessor.

## Iterators

- Iterator chains over index loops. They fuse, vectorize, and eliminate bounds checks.
- `iter.collect::<Result<Vec<_>, _>>()?` short-circuits on the first error. Standard pattern for fallible maps.
- Reach for `itertools` (`chunks`, `group_by`, `dedup_by`, `tuple_windows`) before rolling your own.
- Iterators are lazy — ending a chain without `collect`/`for_each`/`count` is dead code. Clippy warns.
- Prefer `.iter().copied()` or `.cloned()` at the call site over `.map(|x| *x)` / `.map(|x| x.clone())`.

## Async

- Tokio has won for multi-threaded runtimes. Pick it unless you have a concrete reason (`smol` for embedded-ish; `async-std` is effectively abandoned).
- `async fn` in traits is stable since 1.75. Use directly in internal traits. For public library traits prefer returning `-> impl Future<Output = T> + Send` to pin Send bounds.
- Never call `block_on` inside async code. Deadlocks single-threaded runtimes, wastes workers on multi-threaded ones.
- `tokio::select!` for racing a small, fixed set of futures. `JoinSet` for dynamic N-task fan-out with batch cancellation on drop.
- Hold no `MutexGuard` across `.await`. Use `tokio::sync::Mutex` only when you genuinely must — otherwise restructure to message-passing (`mpsc`).
- Async closures (`async || { ... }`) are stable in Rust 2024. Prefer over `|| async move { ... }` for capturing borrows.

## Lifetimes

- Trust elision. Only name a lifetime when the signature relates multiple inputs to an output or two outputs share a borrow.
- Avoid `'static` bounds in library APIs unless you truly require ownership/thread-escape. They virally infect callers.
- Use `PhantomData<&'a T>` / `PhantomData<fn(&'a T)>` to tie an unused lifetime or variance without storing data.
- If a struct grows three lifetime parameters, reconsider the design. Own the data or restructure into an arena.

## Performance

- `Box<[T]>` over `Vec<T>` for immutable-after-build collections. One word smaller, signals intent.
- `Arc<T>` only when sharing across threads. `Rc<T>` within a thread. Plain ownership by default. Atomics are not free.
- `Arc<Mutex<T>>` is a code smell as default state sharing. Prefer `mpsc`/`watch` channels, `Arc<RwLock>`, or sharded locks.
- `parking_lot` is no longer necessary for most cases — std `Mutex` became competitive in 1.62. Use `parking_lot` only when benchmarks prove it.
- Use the `bytes` crate (`Bytes`, `BytesMut`) for zero-copy network buffers. Avoid `Vec<u8>` memcpys on I/O hot paths.
- Measure before optimizing. `cargo flamegraph`, `criterion`, `#[inline]` only with evidence.
- Prefer `LazyLock<T>` (stable 1.80) over `once_cell::sync::Lazy` in new code.

## Tooling & Macros

- Enforce `cargo fmt` (default `rustfmt.toml`) and `cargo clippy --all-targets -- -D warnings -W clippy::pedantic` in CI.
- Derive `Debug, Clone, PartialEq, Eq, Hash` on data types as a matter of course. Derive `Copy` only for ≤ 16-byte POD.
- Use `rust-analyzer` as the single source of IDE truth. Disable competing language servers.
- Reach for `macro_rules!` before proc macros. Proc macros have heavy compile-time cost and poor IDE ergonomics — only write one when repetition is large and genuinely unavoidable.
- Put `#![warn(missing_docs, rust_2018_idioms)]` on library crates.

## Anti-Patterns

- `.clone()` sprinkled to silence the borrow checker. A design failure, not a fix.
- `.unwrap()` in `main`/handlers. Use `?` with `anyhow::Result<()>` from `main`.
- `Arc<Mutex<T>>` as default "shared state." Almost always a channel or ownership redesign is correct.
- `Box<dyn Error>` as a library error type. Forces string-matching on callers. Use `thiserror` enums.
- `&String`, `&Vec<T>`, `&Box<T>` parameters. Always narrow to `&str`, `&[T]`, `&T`.
- Getter/setter-shaped Rust imitating OOP classes. Express invariants via types and consuming methods.
- Premature generics / trait explosion. Concrete first, generalize on the *second* caller, never the first.
- `impl<T> From<T> for MyError where T: Error` blankets. Conflicts with `?` ergonomics downstream.

## Sources

- [Rust 1.85.0 + 2024 edition announcement](https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/)
- [async fn and RPIT in traits](https://blog.rust-lang.org/2023/12/21/async-fn-rpit-in-traits/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)
- [Clippy Lints reference](https://rust-lang.github.io/rust-clippy/master/index.html)
- [Rust for Rustaceans — Jon Gjengset](https://rust-for-rustaceans.com/)
