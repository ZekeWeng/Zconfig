---
paths:
  - "**/*.tsx"
  - "**/*.ts"
  - "**/*.jsx"
  - "**/*.js"
  - "**/tsconfig*.json"
---

# Idiomatic TypeScript + React (React 19, TS 5.x)

## React 19 Core

- Default to Server Components. Opt into `"use client"` only at interactivity boundaries — push the directive as far down the tree as possible to minimize shipped JS.
- Never import a Server Component from a Client Component. Pass it through `children` instead — canonical composition fix for the one-way import rule.
- Use the `use()` hook to unwrap promises and context in render. Prefer over `useContext` in new code. Use with Suspense boundaries for data.
- Reach for Actions (`<form action={fn}>` + `useActionState`) before wiring manual `onSubmit` + `useState` + `try/catch`. You get pending, error, and optimistic state for free.
- Pair `useOptimistic` with an Action for any mutation likely to succeed. Removes spinners on the happy path without losing rollback on failure.
- Pass `ref` as a regular prop. Do not write new `forwardRef` code — it's slated for removal.
- Stop writing `useMemo`, `useCallback`, and `React.memo` in new code once the React Compiler is enabled. Keep them only as escape hatches for third-party reference-equality contracts or measured regressions.

## Hooks Discipline

- Effects are for synchronizing with external systems, not for React-to-React data flow — fetching, subscribing, imperatively touching the DOM. Nothing else.
- Derive, don't store. Compute values during render from existing props/state. `useMemo` only if profiling proves the computation expensive.
- Reset child state by changing its `key`, not by writing an effect that calls `setState` on prop change.
- Subscribe to external mutable stores with `useSyncExternalStore`. Never with `useEffect` + `setState` — tears under concurrent rendering.
- Keep `react-hooks/exhaustive-deps` on. Never silence with a comment — if the dep is "wrong," the code is wrong.
- Lift event-driven side effects into event handlers, not effects. Analytics on click belongs in `onClick`, not an effect keyed on state.

## Component Composition

- Accept `children` (or named render-slot props) before adding a seventh configuration prop. Composition scales; prop explosion does not.
- Build compound components (`Tabs.Root`/`Tabs.List`/`Tabs.Trigger`) when siblings share implicit state — flat API, co-located state.
- Lift state only to the nearest common ancestor. Reach for context only when prop drilling crosses ~3 layers of unrelated intermediaries.
- Split contexts by update frequency. A single `AppContext` that changes often will re-render half your tree.

## State Management

- Local `useState` → lifted state → context → external store. In that order, no skipping.
- Server state is not client state. Own it with TanStack Query (or RTK Query / SWR). Never re-invent caching, refetching, and dedupe with `useEffect`.
- Use Zustand for the small slice of genuinely global client state (auth, theme, UI modes). Redux Toolkit only for enforced patterns or time-travel debugging at scale.
- Use Jotai when state is atomic and highly derived. Zustand when state is interconnected and store-shaped.
- Never store server data in Redux/Zustand "just in case" — it drifts from the query cache.

## TypeScript Patterns

- Model state and variant props as discriminated unions, not optional-everything objects. `{ status: 'idle' } | { status: 'error', error: Error }` makes impossible states unrepresentable.
- Use `satisfies` to validate shape without widening literals. Preserves `as const` narrowing while enforcing the contract.
- Prefer `as const` over manual literal unions for config objects and enums. Then derive the type.
- Use branded types for IDs and unsafe-looking primitives (`type UserId = string & { __brand: 'UserId' }`). Kills argument-order bugs.
- Type children as `ReactNode`. Do not use `React.FC` — it implicitly injects `children` and historically broke generics.
- Never narrow with `as`. Narrow with control flow, `in`, `typeof`, or user-defined type guards. A cast is a silent lie.
- Treat `any` as a bug and `unknown` as a to-do. `unknown` must be narrowed before use.
- Switch on the discriminant directly (`switch (props.kind)`), not on a destructured copy. Destructuring before the switch loses narrowing.

## Async Data

- Fetch with TanStack Query / SWR. Not `useEffect` + `fetch` + `setState` — otherwise you reimplement caching, retries, dedupe, and cancellation badly.
- Place a Suspense boundary and an Error Boundary per route, and again around any independently-loading region. Shared boundaries create whole-page fallbacks.
- Hoist data requirements to the route/loader level to avoid request waterfalls. A child that fetches after the parent resolves is a waterfall.
- Prefer parallel queries (`useQueries`, `Promise.all`, RSC parallel fetches) over sequential awaits when requests are independent.

## Forms

- Default to uncontrolled inputs + `FormData` inside a React 19 Action. Let the platform manage state.
- Reach for React Hook Form for fine-grained validation UX, field arrays, or cross-field logic. It's uncontrolled under the hood, so re-renders stay cheap.
- Validate with Zod and derive TS types from the schema (`z.infer`). One source of truth for runtime + compile-time.
- Re-validate on the server even when the client validated. Client validation is UX, not security.

## Performance

- Use stable, content-derived keys. Never the array index for lists that reorder, insert, or delete.
- Virtualize lists above ~500 items (react-window). Don't bother below ~50. Measure before reaching further.
- Code-split at the route with `React.lazy` + `Suspense`. Split heavy leaf components (editors, charts) the same way.
- Memoize context *values*, or split the context, when consumers only care about part of it. Otherwise every consumer re-renders on any change.
- Profile with the React Profiler + a production build before optimizing. Dev-mode numbers lie.

## Accessibility

- Reach for a real `<button>`, `<a href>`, `<label>`, `<nav>`, `<dialog>` before a `<div>` with ARIA. Semantic HTML ships keyboard and screen-reader behavior for free.
- Use ARIA only when no native element fits. Prefer `aria-*` state over role invention.
- Manage focus on route change, modal open/close, and async content reveal. Return focus to the trigger on close.
- Never remove the focus outline without replacing it with an equally visible indicator.
- Run `eslint-plugin-jsx-a11y` in CI and spot-check with a screen reader. Automated tools catch ~half of issues.

## Anti-Patterns

- `useEffect` that fetches and `setState`s — use a query library.
- `useState` seeded from props, kept in sync by an effect — derive during render or use `key` to reset.
- `key={index}` on dynamic lists — silent bug factory.
- Prop drilling past three layers of uninterested components — use composition or context.
- `useMemo`/`useCallback` sprinkled defensively — especially with Compiler enabled, it's noise and can hide bugs via stale closures.
- `as SomeType` to silence the compiler — narrow properly or fix the type.
- A single monolithic context holding unrelated slices — split it.
- Business logic inside JSX event handlers — extract pure functions so they're testable.

## Sources

- [React 19 release notes](https://react.dev/blog/2024/12/05/react-19)
- [You Might Not Need an Effect](https://react.dev/learn/you-might-not-need-an-effect)
- [React Compiler](https://react.dev/learn/react-compiler/introduction)
- [TanStack Query vs client state](https://tanstack.com/query/latest/docs/framework/react/guides/does-this-replace-client-state)
