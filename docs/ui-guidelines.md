# Git Analytics — UI/UX Guidelines

---

## Design Direction

- **Inspired by**: GitHub, Vercel, Linear
- **Theme**: Dark SaaS
- **Layout**: Compact analytics
- **Approach**: Typography-first, responsive dashboard
- **Tone**: Engineering-grade, professional

---

## Layout

### Dashboard Pages
- Overview: summary cards + key charts
- Commits: frequency, by contributor, recent list
- Pull Requests: status, merge time, by author
- Issues: open/closed, by label, time to close
- Insights: heatmap, streaks, health score, activity patterns

### Components
- **Sidebar**: Navigation with icons, active state highlight
- **Topbar**: Repository selector + user menu
- **Cards**: Summary metrics with icons, color accents
- **Tables**: Responsive with horizontal scroll, sorted columns
- **Charts**: Chart.js line/bar/doughnut with dark theme colors

---

## Design Patterns

### Responsive Tables
- `overflow-x: auto` for horizontal scroll
- Compact padding, mono-spaced numbers
- Status badges with color coding

### Sync Status Badges
- `pending` → gray/yellow
- `syncing` → blue with spinner
- `success` → green
- `failed` → red

### Health Score Widget
- Gauge 0-100
- Color gradient: red → yellow → green
- Composite metric from commit frequency, PR merge rate, issue closure

### Branch Selector
- Dropdown for multi-branch selection
- Per-branch analytics mode
- Branch-specific sync controls

---

## Heatmap

The contribution heatmap follows specific layout rules:

- CSS grid with fixed cell sizing
- `overflow-x: auto` for horizontal scroll
- `fit-content` inner grid (no flex-wrap hacks)
- No infinite canvas expansion
- Aligned month labels
- Responsive cell spacing
- Loading/skeleton state
- Tooltip on hover showing date + count

---

## Typography

- System font stack (`-apple-system, BlinkMacSystemFont, "Segoe UI", ...`)
- Mono-spaced numbers in data tables
- Compact line-height for dense analytics views
- Small secondary text for metadata

---

## Color Palette (Dark Theme)

| Role | Color |
|---|---|
| Background | `#0d1117` |
| Surface | `#161b22` |
| Border | `#30363d` |
| Text | `#e6edf3` |
| Text muted | `#8b949e` |
| Accent | `#58a6ff` |
| Success | `#3fb950` |
| Warning | `#d29922` |
| Danger | `#f85149` |
