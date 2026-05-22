# Git Analytics — Roadmap

---

## Phase 1: Engineering Toolkit (Current)

**Status**: Active — strong foundation established

### In Scope
- Repository analytics (commits, PRs, issues per repo)
- Contributor analytics (per-contributor profiles)
- Branch analytics (multi-branch sync, branch selector)
- Commit heatmap (365-day GitHub-style grid)
- KPI scoring & repository health score
- Engineering dashboard (Overview, Commits, PRs, Issues, Insights)
- Executive overview cards
- Engineering Reports (immutable snapshots)
- PDF / Excel export
- Release notes generation
- Changelog generation
- Risk insights
- Public capability URL sharing (revoke, token rotation, anonymization)
- AI Workspace (commit message gen, PR review, repo assistant, BYOK/Cloud Preview)

### NOT in Scope (Phase 1)
- Large-scale worker fleet — current sync queue remains single-process
- Cross-repo aggregation — single-repo only
- Contributor identity resolution — simple mapping only
- Scheduled report generation — manual generation only
- Multi-user workspace — single-user
- Billing / subscription
- Password-protected reports
- Expiring public links
- SEO public reports
- Enterprise RBAC
- High-stakes cross-repo KPI

---

## Phase 2: Single-Repo AI Insight Engine (Next)

### Planned
- AI insight layer across all analytics
- AI repo assistant improvements
- AI PR review enhancements
- AI summary engine
- Scheduled report generation groundwork
- Provider output quality and repo-context improvements
- Cloud AI quota/billing hardening

---

## Phase 3: Hosted / SaaS Foundation

### Planned
- External worker deployment model
- Multi-process async sync engine
- Retry/recovery observability
- Durable queue deployment strategy
- Tenant isolation architecture
- Rate-limit aware scheduling
- Stale sync detection & recovery

---

## Phase 4: Multi-Repo Intelligence

### Planned
- Cross-repo analytics
- Contributor identity resolution (aliases, email mapping, confidence scoring)
- Workspace / team analytics
- Organization-level intelligence
- Executive overview across repos
- Multi-repo reports

---

## Future Operating System Update

Deferred capabilities (not on active roadmap):
- Workspace-level KPIs
- Cross-repo contributor ranking
- Multi-repo report snapshots
- Enterprise RBAC
- Team management
- Organization membership

---

## Key Principles

1. **Trust > fake intelligence** — never fabricate AI results
2. **Immutable snapshots** — reports are point-in-time captures
3. **Stable analytics first** — foundation before embellishment
4. **Document limitations honestly** — known limits are explicit
5. **Avoid premature enterprise complexity** — no enterprise features until Phase 3+
6. **Avoid scope creep** — each phase has hard boundaries
7. **Vision != implementation target** — Engineering Operating System is vision, not current target
