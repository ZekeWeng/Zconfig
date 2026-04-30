---
name: scaffold
description: Scaffold a new feature with boilerplate files, tests, and documentation.
argument-hint: "[feature-name] [description]"
allowed-tools: Bash, Read, Edit, Write, Glob, Grep
disable-model-invocation: true
---

# Scaffold Feature: $ARGUMENTS

## Steps

1. Analyze the existing project structure to understand conventions:
   - File naming patterns
   - Directory organization
   - Import/export style
   - Test file locations and patterns
2. Create the feature files following existing conventions
3. Create corresponding test files with basic test structure
4. Update any barrel exports or index files
5. Run linters/type checks to verify everything compiles

## Rules
- Follow existing project conventions exactly — don't introduce new patterns
- Include basic happy-path tests at minimum
- Wire up the feature so it's importable but not necessarily integrated
