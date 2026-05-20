# ADR-0002: Use commit list endpoint only — no per-commit detail calls

## Status
Accepted

## Context
GitHub REST API returns commit metadata (sha, message, author, date) from the list endpoint `GET /repos/{owner}/{repo}/commits`. However, `stats` (additions/deletions) and `files` are only available from the detail endpoint `GET /repos/{owner}/{repo}/commits/{sha}` — requiring one request per commit.

A repository with 1,000 commits would need ~1,010 requests to get full detail vs ~10 requests for list-only.

### Alternatives considered

1. **List only** — ~10 requests/1000 commits. No additions/deletions. Dashboard: frequency, timeline, contributor breakdown.
2. **Full detail** — ~1,010 requests/1000 commits. Rich stats but extreme API cost, slow sync, high rate limit risk.
3. **Hybrid** — List all + detail for N recent commits. Balanced but adds complexity.

## Decision
MVP uses list endpoint only. Do not call the per-commit detail endpoint.

Fields stored: sha, message, author_name, author_email, author_login, committed_at, committer info, html_url.

Fields NOT stored: additions, deletions, changed_files, file list, patch/diff.

## Consequences

- **Pro**: Sync is fast (~10 requests per 1000 commits)
- **Pro**: Minimal rate limit risk
- **Pro**: Sufficient for core analytics (frequency, timeline, contributor stats)
- **Con**: Cannot show "lines of code contributed" or "file change heatmap"
- **Future**: Add hybrid mode (detail for N recent commits) or a separate `commit_stats` table
