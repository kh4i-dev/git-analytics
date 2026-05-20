# ADR-0001: Use GitHub OAuth `repo` scope with read-only business logic

## Status
Accepted

## Context
GitHub REST API requires the `repo` scope to read data from private repositories (commits, PRs, issues). There is no read-only scope for private repo data — `repo` inherently grants write access as well.

The system is an analytics dashboard that only needs to **read** repository data. It never creates, updates, or deletes anything on GitHub.

### Alternatives considered

1. **No scope (public only)** — Safe but excludes private repos. Many student/personal projects are private, severely limiting usefulness.
2. **`repo` scope** — Full access to public + private repos. Includes write permissions that the app does not need.
3. **GitHub App with fine-grained permissions** — Can grant read-only access specifically. More complex to set up (requires app installation flow, webhook setup).

## Decision
Use GitHub OAuth App with `repo` + `read:user` scopes. Enforce read-only at the application level:

- Only call GitHub GET endpoints (list repos, list commits, list PRs, list issues)
- Never call any POST/PUT/PATCH/DELETE GitHub endpoints
- Store token server-side only; never expose to frontend
- Do not log tokens

## Consequences

- **Pro**: Can analyze both public and private repositories
- **Pro**: Simple OAuth flow, well-documented, easy to implement for MVP
- **Pro**: Good demo — can show private repo analytics
- **Con**: Users must trust the app with write-capable scope
- **Con**: A bug or security breach could theoretically allow writes
- **Mitigation**: Read-only enforcement in service layer; token never reaches frontend
- **Future**: Migrate to GitHub App with fine-grained permissions for production
