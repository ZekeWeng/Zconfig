---
paths:
  - "**/*auth*"
  - "**/*login*"
  - "**/*password*"
  - "**/*secret*"
  - "**/*token*"
  - "**/*crypt*"
  - "**/*session*"
  - "**/*api*"
  - "**/*middleware*"
---

# Security Rules

## Input Boundaries

- Never trust external input — validate and sanitize at the system boundary, then pass clean domain types inward
- Parameterize all database queries — never interpolate user input into SQL or query strings
- Sanitize and escape user input before rendering in HTML, shell commands, or log output
- Validate and sanitize file paths to prevent directory traversal (`../`)
- Reject unexpected input shapes early — don't let malformed data propagate through layers

## Secrets and Credentials

- Never hardcode secrets, tokens, or credentials — always use environment variables or a secret manager
- Never log sensitive data (passwords, tokens, PII, session IDs)
- Use constant-time comparison for secrets and tokens to prevent timing attacks
- Rotate and scope credentials to minimum required permissions

## Authentication and Authorization

- Authenticate at the edge (adapter layer), then pass verified identity into core
- Authorize at the domain level — business rules decide access, not transport-layer middleware alone
- Session tokens must be cryptographically random, HTTP-only, secure, and scoped

## Transport and Headers

- Set appropriate CORS, CSP, and security headers for web services
- Use HTTPS everywhere — reject plaintext in production
- Rate-limit authentication endpoints and sensitive operations
