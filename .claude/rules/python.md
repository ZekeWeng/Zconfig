---
paths:
  - "**/*.py"
  - "**/pyproject.toml"
---

# Idiomatic Python (3.12+)

## Typing

- Use PEP 604 unions (`X | Y`, `T | None`) and PEP 585 built-in generics (`list[int]`, `dict[str, Foo]`). Never `Optional`, `Union`, `List`, `Dict` in new code.
- Prefer PEP 695 syntax (`class Repo[T]:`, `def first[T](xs: list[T]) -> T:`) over `TypeVar`/`Generic`.
- Type parameters and return values on all public APIs. Local variables only when inference fails.
- Accept `Iterable`/`Mapping`/`Sequence` from `collections.abc` in parameters; return concrete `list`/`dict`. Liberal in, strict out.
- Use `Self` for fluent/builder returns instead of forward-referencing the class name.
- Use `Protocol` for structural typing of third-party or duck-typed objects; reserve `ABC` for owned hierarchies with explicit inheritance.
- `TypedDict` with `NotRequired` is for JSON/dict shapes at IO boundaries only — otherwise use a dataclass.
- Use `ParamSpec` + `Concatenate` for decorators that preserve the wrapped signature.
- Run `pyright` (or `mypy --strict`) in CI. Untyped code is unverified code.

## Data Modeling

- `@dataclass(slots=True, frozen=True)` is the default for internal value objects — stdlib, zero deps, fast.
- Reach for `attrs` when you need converters, composable validators, or `__init_subclass__` hooks dataclasses lack.
- Use Pydantic only at trust boundaries (HTTP, CLI, config, DB rows). It is a parser, not a model library — don't litter it through core.
- Never put ORM/JSON annotations on domain models; translate at the adapter layer.
- Prefer `kw_only=True` for models with more than 3 fields — positional construction gets unreadable.

## Error Handling

- Derive a single package-root exception (e.g. `AppError`) and subclass from it. Callers filter one hierarchy.
- Chain with `raise NewError(...) from err` to preserve causality. Use `from None` only when deliberately hiding.
- Never `except Exception:` (or bare `except:`) without re-raising or logging with traceback.
- Catch the narrowest type that fits. If the list gets long, the abstraction is wrong.
- Use `ExceptionGroup` + `except*` only when genuinely parallel failures must surface together (concurrent tasks, validation passes).
- Fail loudly at boundaries, trust internally. No defensive re-validation between layers.

## Async

- Use `asyncio.TaskGroup` (3.11+) for any fan-out. It cancels siblings on failure and propagates via `ExceptionGroup`.
- `asyncio.gather` is legacy — `return_exceptions=True` silently swallows, and sibling failures leak tasks.
- Use `asyncio.timeout()` context manager for deadlines, not `wait_for`.
- Never mix sync blocking I/O into async code. Wrap with `asyncio.to_thread` or keep the function sync.
- Don't call `asyncio.run()` from library code — only at the process entry point.
- Prefer `anyio` for Trio/asyncio portability and cleaner cancellation semantics.
- Every `create_task` must be awaited or owned by a `TaskGroup`. Orphan tasks get GC'd mid-flight.

## Iteration & Comprehensions

- Comprehensions are for mapping/filtering one collection into another. If you see nested `for` or `if/else` doing work, write a loop.
- Use generator expressions (`sum(x*x for x in xs)`) for aggregation. Don't materialize lists you immediately consume.
- Reach for `itertools` (`pairwise`, `batched` (3.12+), `chain`, `groupby`) before hand-rolling index math.
- Unpack with `*rest` and starred assignment rather than slicing.

## Context Managers

- Any acquire/release pair (file, lock, transaction, tempdir, subprocess) belongs in a `with` block.
- Write new ones with `@contextlib.contextmanager`. Only drop to `__enter__`/`__exit__` when the object's lifecycle is the class's primary concern.
- Use `contextlib.ExitStack` for variable-length or conditional resource acquisition instead of nested `with`.
- Async resources use `async with` + `@asynccontextmanager`. Never mix sync and async cleanup.

## Performance

- Add `slots=True` to dataclasses instantiated at scale — cuts memory ~40% and speeds attribute access.
- `functools.cached_property` for expensive per-instance computation; `functools.cache` (not `lru_cache(None)`) for pure functions.
- Profile before optimizing — `cProfile`/`py-spy` over intuition.
- String-building in a hot loop uses `"".join(parts)`, never `+=`.

## Tooling

- Ruff is the formatter and linter — it subsumes Black, isort, flake8, pyupgrade, pydocstyle.
- Use `uv` for install, lock, venv, and script running. pip/poetry/pip-tools/pyenv are obsolete for new projects.
- Pyright is the default type checker. Use mypy only if a dependency requires its plugins.
- Pytest: `tmp_path`, parametrize over loops, fixtures over setup/teardown, one assertion concept per test.
- Enforce `ruff check`, formatter, and type-check in both pre-commit AND CI. Local-only checks get bypassed.

## Project Structure

- Use `src/` layout — prevents accidental imports from repo root and forces install-before-test.
- Single `pyproject.toml`. No `setup.py`, no `requirements.txt`, no `setup.cfg`.
- Declare dev deps in `[dependency-groups]` (PEP 735) as `dev`, `test`, `docs`. Not as optional extras.
- Pin runtime deps loosely (`>=`); pin dev deps exactly via `uv.lock`.
- Group code by feature/domain (`users/`, `billing/`), not by layer (`models/`, `views/`).

## Anti-Patterns

- Never use mutable defaults (`def f(x=[])`) — use `None` and assign inside.
- `pathlib.Path` everywhere. `os.path` is a smell outside of legacy compat shims.
- `isinstance(x, Foo)` for type checks. `type(x) == Foo` breaks on subclasses and lies under `Union`.
- No `from pkg import *` in library code — breaks static analysis and shadows names silently.
- `enumerate`/`zip` instead of `range(len(...))`. No C-style indexing.
- Don't catch an exception just to re-raise it unchanged. Don't log and re-raise (pick one).
- `print` is not logging — use the `logging` module with a named logger per module.
- Don't write getters/setters. Use attributes; promote to `@property` only when behavior is added.

## Sources

- [PEP 695 – Type Parameter Syntax](https://peps.python.org/pep-0695/)
- [PEP 654 – Exception Groups and except*](https://peps.python.org/pep-0654/)
- [PEP 735 – Dependency Groups](https://peps.python.org/pep-0735/)
- [Ruff docs](https://docs.astral.sh/ruff/)
- [uv docs](https://docs.astral.sh/uv/)
