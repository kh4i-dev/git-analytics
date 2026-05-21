# Git Analytics — Walkthrough

End-to-end user flow for the Engineering Intelligence Platform.

---

## 1. Authentication

1. Navigate to `http://localhost:8000`
2. Click **Login with GitHub**
3. Authorize the OAuth app (scope: `repo` + `read:user`)
4. Redirected to dashboard home

## 2. Connect a Repository

1. Go to **Repositories** page
2. Browse your GitHub repos (public and private)
3. Click **Connect** on a repo to add it for analysis
4. Repo appears with status `pending`

## 3. Sync Data

1. Click **Sync** on any connected repo
2. System checks GitHub rate limit (warns if < 50 remaining)
3. Sync fetches commits, PRs, issues (full first, incremental after)
4. Status updates: pending → syncing → success/failed
5. Sync badges show current state with color coding

## 4. Explore Analytics

### Overview
- Summary cards: total commits, PRs, issues, last sync
- Health score gauge (0-100)
- Executive overview cards: velocity, contributors, trends

### Commits
- Commits per day/week chart
- By contributor breakdown
- Recent commits list
- Heatmap (365-day GitHub-style contribution grid)

### Pull Requests
- Status distribution (open/closed/merged)
- Average merge time
- PRs by author

### Issues
- Open vs closed chart
- By label distribution
- Average time to close

### Insights
- Activity score
- Coding streaks (current, longest)
- Time-of-day distribution
- Weekday distribution
- Conventional commit keywords

## 5. Branch Analytics

1. Select a repository with synced data
2. Use the **Branch Selector** to switch branches
3. Each branch shows independent analytics
4. Branch-specific sync supported (sync all branches or selected)

## 6. AI Workspace

### Commit Message Generator
1. Paste staged diff or describe changes
2. Click **Generate** — AI produces conventional commit message
3. Copy or regenerate

### PR Diff Reviewer
1. Paste PR diff or partial code changes
2. Click **Review** — AI analyzes code, suggests improvements
3. Review includes: code quality, security, performance notes

### Repo Assistant
1. Ask questions in natural language about your repository
2. Examples: "Who contributed the most last month?", "What's the merge rate?"
3. AI answers based on synced data context

### AI Modes
- **Local Fallback**: Runs on-device, no API key needed
- **Future Hosted**: OpenAI/Gemini/BYOK (Phase 2)

## 7. Engineering Reports

1. Navigate to **Reports** page
2. Click **Generate Report** for a repository
3. System creates immutable snapshot of current analytics
4. Report includes:
   - Generated title (repo + date range)
   - Date range and as-of timestamp
   - Release notes
   - Changelog
   - Risk insights
   - Summary metrics

### Sharing
1. Open a report
2. Click **Publish** to create capability URL
3. Copy public link to share
4. Revoke any time — public access removed, private report kept
5. Republish after revoke creates new token

### Report Management
- **Custom Title**: Edit display title (doesn't overwrite generated)
- **Anonymize**: Hide repository name in public view
- **Revoke**: Remove public access
- **Delete**: Permanently remove report

## 8. Export

- **PDF Export**: Download report as PDF
- **Excel Export**: Download raw data as spreadsheet

## 9. Logout

Click **Logout** in sidebar. Session cookie cleared. Re-login required.
