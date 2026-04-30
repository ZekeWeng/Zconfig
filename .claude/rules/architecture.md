# Architecture — Hexagonal / Ports & Adapters

## Core Principle

Dependencies point **inward**. The domain core knows nothing about the outside world.

```
Adapters → Ports (interfaces) → Core Domain
```

## Layers

| Layer | Contains | Depends on |
|-------|----------|------------|
| **Core** | Business logic, domain models, value objects | Nothing external |
| **Ports** | Interfaces that define how core talks to / is called by the outside | Core types only |
| **Adapters** | Implementations of ports — HTTP handlers, DB repos, CLI, filesystem | Ports + Core |
| **Composition root** | Wiring — instantiates adapters, injects into core | Everything (this is the only place) |

## Rules

- Core domain logic must have **zero** external dependencies — no shell, OS, network, framework, or editor coupling
- Define explicit ports (interfaces/contracts) at every boundary between core and the outside world
- Adapters implement ports — they wrap external concerns and translate to/from domain types
- Never leak adapter types into core — if core needs data from outside, define a port that returns domain types
- The composition root is the **only** place that knows about concrete adapters
- When adding new functionality, always ask: does this belong in core, a port, or an adapter?

## Dependency Direction Violations to Watch For

- Core importing an HTTP library, database driver, or filesystem package
- A domain model containing serialization annotations (JSON tags, ORM decorators)
- Business logic directly calling `fetch()`, `fs.readFile()`, `exec()`, or equivalent
- An adapter calling another adapter — route through core or create a shared port

## Module Boundaries

- Each module/package should have a **single public entry point** (barrel export, facade, or public API surface)
- Modules communicate through their public interfaces, never by reaching into internals
- If two modules need shared types, extract them into a shared domain/types module — don't create circular imports
- A module that imports from more than 3 other modules is likely doing too much — split it
