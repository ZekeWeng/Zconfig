---
name: audit-security
description: Repo-wide security audit using OWASP Top 10 and STRIDE threat modeling. Reports findings with exploit scenarios and concrete fixes.
allowed-tools: Bash, Read, Glob, Grep
disable-model-invocation: true
context: fork
agent: Explore
---

# Security Audit

Sweep the entire repository for vulnerabilities. Use both frameworks below — they catch different classes.

## OWASP Top 10

1. Broken access control
2. Cryptographic failures (weak hashes, hardcoded keys, unpinned TLS)
3. Injection (SQL, shell, XSS, template, command)
4. Insecure design (trust boundaries, missing rate limits)
5. Security misconfiguration (overly permissive settings, default creds)
6. Vulnerable / outdated components (unpinned deps, known-CVE versions)
7. Authentication failures (weak session, missing MFA enforcement)
8. Software / data integrity failures (`curl | sh`, unverified downloads, unsigned packages)
9. Security logging failures (missing audit trail for sensitive ops)
10. Server-side request forgery (SSRF)

## STRIDE

- **S**poofing identity
- **T**ampering with data
- **R**epudiation (no audit trail)
- **I**nformation disclosure (secrets in logs, world-readable creds)
- **D**enial of service (unbounded input, expensive ops on untrusted input)
- **E**levation of privilege

## Checklist for dotfiles-style repos

- `.env` gitignored? (Verify, don't assume.)
- Any `curl | sh` or `wget | bash`?
- Plugin managers pulling from unpinned branches/tags?
- Shell scripts with unquoted variable expansion in command positions?
- `.claude/settings*.json` with wildcard permissions too broad?
- SSH config / gitconfig storing credentials in plaintext?

## Output

For each finding:
- **Severity**: Critical / High / Medium / Low / Info
- **File:line**: exact location
- **Issue**: one sentence
- **Exploit scenario**: concrete attack path — not hypothetical
- **Fix**: specific code change

Group findings by severity. End with what you checked and found clean.

## Rules

- No invented findings. If the repo is clean, say so plainly.
- Verify assumptions (e.g. "`.env` is gitignored") before listing as clean.
- Flag dual-use patterns (`curl | sh`, broad Bash allowlists) even when "working as intended."
