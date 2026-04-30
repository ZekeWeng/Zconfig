---
name: investigate
description: Root-cause debugging. Traces data flow, tests hypotheses, hard-stops after 3 failed fixes to force re-analysis.
argument-hint: "[bug description or error message]"
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
context: fork
---

# Investigate: $ARGUMENTS

## Protocol

1. **Reproduce.** Confirm the bug with a minimal, deterministic repro. If you can't reproduce, stop and ask for more detail.
2. **Trace.** Walk the data/control flow from the failure point **backwards**. Cite `file:line` for each hop.
3. **Hypothesize.** Write down the suspected root cause in one sentence *before* touching any code.
4. **Verify.** Apply the minimal fix. Re-run the repro. Done only when the repro passes.

## Hard Stop: three-strike rule

If three attempted fixes fail to resolve the bug, **stop changing code**. Continuing past three attempts turns debugging into whack-a-mole. Instead return:

- What you tried (each attempt, why it didn't work)
- What the trace actually showed
- Which assumption from step 3 is now suspect

The point of stopping is to force re-analysis, not to hide progress.

## Output

Either:
- **Fixed** — root cause (1 sentence), `file:line` of the fix, repro command to verify.
- **Stopped at 3** — trace summary, each attempt, the assumption that's now suspect.
