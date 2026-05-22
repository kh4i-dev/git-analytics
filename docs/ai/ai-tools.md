# Git Analytics — AI Tools & Workspace Architecture

This document outlines the features, architecture, configurations, and frontend-backend decoupling for the AI Tools suite within the Git Analytics platform.

---

## 1. Feature Overview

The AI Workspace offers a professional developer toolkit designed to run either through Bring-Your-Own-Key (BYOK) encrypted credentials or a secure server-configured Cloud AI preview channel.

### A. Commit Message Generator
* **Description**: Generates short, highly descriptive conventional commit messages from git diff sequences.
* **Input**: Standard git diff (untracked or staged) containing standard headers.
* **Output**: Strictly-formatted Conventional Commit message (e.g., `feat(analytics): add streak tracking engine`).

### B. PR Diff Reviewer
* **Description**: Performs a comprehensive line-by-line code review of a pull request diff or branch changes.
* **Input**: Standard git diff comparing your feature branch against `main`.
* **Output**: Structural assessment focusing on **Logic Errors**, **Performance Bottlenecks**, **Security Vulnerabilities**, and **Missing Tests**.

### C. Repo Assistant (Natural Language Q&A)
* **Description**: A conversational workspace for asking natural-language questions about codebase architecture, repository history, or contributor performance.
* **Context**: Powered by automated repository-metadata retrieval (commits, pull requests, issues, and contributor mappings).

---

## 2. Technical Architecture & Modular Layout

To ensure clean code separation, visual scalability, and testable modules, the AI tools codebase has been fully refactored, dividing a large monolithic HTML layout into decoupled Jinja2 components, standalone static ES6 scripts, and vanilla CSS assets.

### Directory Mapping

```
templates/
├── ai_tools.html                  # Main layout skeleton
└── ai_tools/                      # Jinja2 template components
    ├── _workspace_header.html     # Header, active repository title, & provider status
    ├── _status_badges.html        # Decoupled system/provider badge render logic
    ├── _repo_selector.html        # Repository and branch interactive selector
    ├── _provider_settings.html    # Quick-access BYOK config indicators
    ├── _quick_actions.html        # Developer playbook buttons (e.g. "Draft Release Notes")
    ├── _commit_generator.html     # Commit message interface (diff input/output)
    ├── _pr_reviewer.html          # PR Review interface (diff input/output)
    ├── _repo_assistant.html       # Chat container, input, and repository instructions
    ├── _chat_messages.html        # Reusable component for chat bubble history
    ├── _developer_playbook.html   # Advanced engineering playbook guidance panel
    └── _modals.html               # Config/Settings popup containers

static/
├── css/
│   └── ai_tools.css               # Styling rules for Dark SaaS theme layout
└── js/
    ├── ai_tools.js                # Core controller coordinating tab transitions and forms
    ├── repo_context.js            # Repository/branch selection & local context sync
    ├── ai_assistant.js            # Repo Assistant chat engine & prompt playback controls
    └── markdown_renderer.js       # Client-side Markdown parser and codeblock highlighting
```

---

## 3. Dynamic Client-Side Interactions

* **Vanilla JavaScript & Decoupling**: All client interactions (submitting forms, playing back pre-filled playbook prompts, rendering chat histories, or executing code review triggers) are fully managed via vanilla ES6 modules loaded at the root layout.
* **Static Assets Routing Convention**: When rendering pages from nested sub-routers (such as `dashboard_router`), using standard Jinja `url_for('static', filename='...')` can lead to sub-path mismatching. To bypass this, templates load static files via direct absolute paths:
  ```html
  <link rel="stylesheet" href="/static/css/ai_tools.css">
  <script src="/static/js/ai_tools.js" defer></script>
  ```
* **Client-Side Markdown Rendering**: The `markdown_renderer.js` module dynamically parses AI responses into beautiful Markdown HTML elements (e.g. headers, paragraphs, bold indicators) and adds code syntax copy blocks for code reviews and commit suggestions.

---

## 4. Context Resolution & APIs

### Context-Clearing Endpoint (`/api/v1/ai/clear-context`)
To ensure that conversational context stays relevant and does not mix unrelated information when a user switches repositories or branches:
* Switching the active repository or branch in the selector UI triggers a background POST request to `/api/v1/ai/clear-context`.
* This resets the in-memory/session chat history on the server, ensuring that subsequent questions strictly query the active repo context.

---

## 5. Security & Key Localities

* **Encrypted DB Persistence**: All Bring-Your-Own-Key (BYOK) configurations are encrypted in the local database using the server-side `ENCRYPTION_KEY` using symmetric Fernet encryption.
* **Settings Masking**: Keys are never returned in plain text to the UI. The dashboard displays only configuration markers (`Needs setup` vs `Configured`).
* **Zero-Log Policy**: Usage tracking logs only record status, provider metrics, and token usage counts to calculate daily quota events. Code diffs, prompt inputs, and AI answers are never logged.
