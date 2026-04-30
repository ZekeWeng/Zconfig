---
name: research
description: Deep research on a topic using web search and codebase exploration. Returns a structured summary.
argument-hint: "[topic or question]"
allowed-tools: WebSearch, WebFetch, Read, Glob, Grep
disable-model-invocation: true
context: fork
agent: Explore
---

# Research: $ARGUMENTS

Thoroughly research the topic above using both web sources and the local codebase.

## Approach

1. Search the web for current best practices, documentation, and community consensus
2. Search the local codebase for existing patterns, implementations, or related code
3. Cross-reference findings — identify gaps between current code and best practices

## Output

Provide a structured summary with:
- **Key findings** (bullet points)
- **Relevant code** in this project (file paths and line numbers)
- **Recommendations** (actionable next steps)
- **Sources** (URLs for web sources)
