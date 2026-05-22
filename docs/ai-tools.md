# Git Analytics — AI Tools

---

## Overview

The AI Workspace provides three AI-powered tools for developers. AI calls use either encrypted BYOK provider keys or the hosted-preview Cloud AI configuration supplied by the server.

---

## Tools

### Commit Message Generator
- **Purpose**: Generate conventional commit messages from staged changes
- **Input**: Staged diff or description of changes
- **Output**: Formatted commit message (conventional commits style)
- **Provider Readiness**: OpenAI, Gemini, Claude through configured provider keys

### PR Diff Reviewer
- **Purpose**: AI-powered code review for pull request diffs
- **Input**: PR diff or partial code changes
- **Output**: Review with code quality, security, performance notes
- **Provider Readiness**: OpenAI, Gemini, Claude through configured provider keys

### Repo Assistant
- **Purpose**: Natural language Q&A over repository data
- **Input**: Question about repository (e.g., "Who contributed most last month?")
- **Output**: Answer based on synced data context
- **Provider Readiness**: OpenAI, Gemini, Claude through configured provider keys

---

## AI Modes

### BYOK
- Stores OpenAI, Gemini, or Claude API keys encrypted in the database
- Never renders saved raw key values back to the browser
- Sends AI requests to the selected provider when a tool runs

### Git Analytics Cloud AI
- Uses server-side provider configuration only
- Can route OpenAI-compatible Cloud traffic through a server-configured gateway
- Runs as Preview until quota and billing policy are production-ready

---

## Design Principles

- **No fake AI responses**: When AI is unavailable, show clear error states — never fabricate results
- **Provider states**: Each tool shows when provider configuration is missing
- **Secret locality**: Personal and Cloud provider keys stay server-side
- **Clear failures**: Provider and quota errors surface as explicit UI error states

---

## Architecture

```
User → Route → AI Tool Service → AI Settings Service → encrypted key or Cloud ENV
                         │
                         └→ Provider Gateway → OpenAI | Gemini | Claude | Cloud gateway
                                                → Response
```

Cloud preview usage records provider, operation, status, and coarse token metadata only. It does not persist prompts, diffs, or provider secrets.
