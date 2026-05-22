# Git Analytics — Development Roadmap

This document outlines the evolutionary roadmap for the Git Analytics platform. It tracks completed milestones and maps out future architectural phases.

---

## Phase 1: Core Engineering Toolkit (Completed)
* **Goal**: Establish the foundational analytical engine and snapshot reporting system.
* **Capabilities**:
  * Repository analytics (commits, pull requests, and issues).
  * Branch-aware analytics with dynamic dropdown branch switching.
  * 365-day GitHub-style contribution heatmaps.
  * Quantitative health scoring algorithms.
  * Engineering snapshot reports (release notes, changelogs, risk insights) serialized immutably.
  * PDF and Excel spreadsheet exports.
  * Secure Bring-Your-Own-Key (BYOK) and Cloud AI Preview gateways.
  * Client-side Markdown parser and interactive AI prompt playbooks.

---

## Phase 2: Asynchronous Sync Queue & Resilience (Completed)
* **Goal**: Shift from simple synchronous blocking requests to resilient background jobs.
* **Capabilities**:
  * Decoupled single-process background sync worker queue.
  * Automated job retry mechanisms with backoff algorithms.
  * Robust rate-limit protection (restricting updates if GitHub token is near exhaustion).
  * Sync status badges (pending, syncing, success, failed) synced in real-time.

---

## Phase 3: Global Multi-Repository Intelligence (Completed)
* **Goal**: Elevate analytics from single repositories to global cross-repository dashboards.
* **Capabilities**:
  * Global overview dashboard aggregating metrics across all connected repositories.
  * Unified contribution timelines and hour-of-day/day-of-week heatmaps.
  * Dynamic cross-repo author contribution leaderboards.
  * Global KPI aggregation (average merge times, issue closure rates, contribution streaks).
  * Interactive repository, branch, and author filters.

---

## Phase 4: Hosted SaaS & Enterprise Foundation (Planned)
* **Goal**: Prepare the platform for multi-user hosting, commercial quotas, and enterprise-grade security.
* **Capabilities**:
  * Multi-process async sync engine with durable message brokers (e.g. Redis/Celery).
  * Tenant isolation schemas (ensuring clean data partitioning between user workspaces).
  * Hardened Cloud AI billing and daily usage/quota tracking.
  * Password-protected public sharing and expiring download links.
  * Automated cron-scheduled report generation and email notifications.
  * Advanced Contributor Identity Resolution (AI-powered alias matching, email mapping, and confidence scoring).
  * Enterprise RBAC (Role-Based Access Control) and Single Sign-On (SSO).

---

## Key Core Principles

1. **Grounded Over Hallucination**: Do not fabricate intelligence or metrics; represent raw codebase activity accurately.
2. **Immutability of History**: Snapshots must remain unmutated captures of point-in-time metrics.
3. **Secret Locality**: Sensitive credentials and keys must remain server-side and fully encrypted.
4. **Avoid premature complexity**: Keep the SQLite development and local running simple before scaling to enterprise deployments.
