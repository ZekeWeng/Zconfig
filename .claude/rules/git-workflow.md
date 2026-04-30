# Git Workflow

- Use `git` for local operations and `gh` for all PR operations
- Push with `git push -u origin <branch>` — never force-push shared branches
- Open PRs as drafts: `gh pr create --draft` — mark ready-for-review only after tests pass and self-review is clean
- Each PR should be a single logical change — if it spans two concerns, split into two branches
- Never amend a pushed commit unless explicitly asked

# Commit Message Format

Format: `<type>: <short description>`

| Type       | Use when                                                  |
|------------|-----------------------------------------------------------|
| `feat`     | New feature                                               |
| `fix`      | Bug fix                                                   |
| `docs`     | Documentation only                                        |
| `style`    | Formatting, whitespace (no logic change)                  |
| `refactor` | Code change that neither fixes a bug nor adds a feature   |
| `perf`     | Performance improvement                                   |
| `test`     | Adding or updating tests                                  |
| `build`    | Build system or external dependencies                     |
| `ci`       | CI configuration files and scripts                        |
| `chore`    | Other changes that don't modify src or test files         |
| `revert`   | Revert a previous commit                                  |

- Subject line under 50 characters
- One concern per commit — never bundle formatting, refactoring, and features together
- Write commit messages that explain **why**, not what
- Verify changes are tightly scoped before committing

# Branch Naming

Format: `<type>/<folder>/<short-description>`

Examples: `feat/nvim/add-lsp-keybinds`, `fix/zsh/path-export-order`

- Max ~40 characters, use `-` as word separators
