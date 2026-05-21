# Git Analytics — AI Tools

---

## Overview

The AI Workspace provides three AI-powered tools for developers. In Phase 1, all tools support **Local Fallback Mode** (no API key required). Hosted providers (OpenAI, Gemini, BYOK) are Phase 2.

---

## Tools

### Commit Message Generator
- **Purpose**: Generate conventional commit messages from staged changes
- **Input**: Staged diff or description of changes
- **Output**: Formatted commit message (conventional commits style)
- **Provider Readiness**: ✅ Local fallback — Phase 1

### PR Diff Reviewer
- **Purpose**: AI-powered code review for pull request diffs
- **Input**: PR diff or partial code changes
- **Output**: Review with code quality, security, performance notes
- **Provider Readiness**: ✅ Local fallback — Phase 1

### Repo Assistant
- **Purpose**: Natural language Q&A over repository data
- **Input**: Question about repository (e.g., "Who contributed most last month?")
- **Output**: Answer based on synced data context
- **Provider Readiness**: ✅ Local fallback — Phase 1

---

## AI Modes

### Local Fallback (Phase 1)
- Runs entirely on-device
- No external API calls
- No API key required
- Limited by local compute resources
- All three tools available

### Hosted Provider (Phase 2 — Future)
- OpenAI provider
- Gemini provider
- BYOK (bring-your-own-key)
- Cloud inference pipeline
- Hybrid local/cloud execution strategy

---

## Design Principles

- **No fake AI responses**: When AI is unavailable, show clear error states — never fabricate results
- **Provider/TODO states**: Each tool shows its current provider readiness (Local / Hosted-TODO)
- **BYOK documented**: Architecture for custom API keys is documented, not yet implemented
- **Clear fallback path**: If hosted provider fails, fall back to local mode

---

## Architecture

```
User → Route → AI Service → AI Provider (Local | Future: Hosted)
                                     → Response
```

In Phase 1, the local provider is the only implementation. The provider interface is designed for drop-in replacement with OpenAI/Gemini adapters in Phase 2.
