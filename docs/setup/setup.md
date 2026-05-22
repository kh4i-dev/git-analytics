# Git Analytics — Local Setup & Walkthrough Guide

This document provides complete instructions to set up, initialize, run, and navigate the Git Analytics platform on your local machine.

---

## 1. System Prerequisites & Environment

Before starting, ensure your local system meets the following requirements:
* **Python**: Version 3.10, 3.11, or 3.12 (Python 3.12 is recommended and fully tested).
* **Git**: CLI installed and configured.
* **Database**: SQLite is used for local development (default database file `git_analytics.db`).

---

## 2. Fast Local Installation

Follow these sequential steps to boot the application on your local machine:

### Step A: Clone and Configure Environment
1. Clone the project to your directory.
2. In the project root, copy the example environment file:
   ```bash
   cp .env.example .env
   ```
3. Open `.env` and fill in the minimum required variables (see Section 3 below).

### Step B: Install Python Virtual Environment
Using standard Python virtual environments:
```powershell
# 1. Create the virtual environment
python -m venv .venv

# 2. Activate the environment
.venv\Scripts\Activate.ps1

# 3. Upgrade pip and install package requirements
pip install -r requirements.txt
```

### Step C: Initialize Database Migrations
Run Alembic migrations to build tables and establish indices:
```powershell
.venv\Scripts\alembic upgrade head
```

### Step D: Boot the Development Server
Fire up the FastAPI development runner:
```powershell
.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
The application will be live at: **`http://localhost:8000`**

---

## 3. Environment Parameters (`.env`)

Configure the following parameters in your local `.env` file:

```env
# Core Server Configuration
APP_ENV=local
DEBUG=true
SECRET_KEY=generate_a_secure_random_key_here
ENCRYPTION_KEY=generate_a_secure_fernet_key_here

# GitHub OAuth Credentials
GITHUB_CLIENT_ID=your_github_oauth_client_id
GITHUB_CLIENT_SECRET=your_github_oauth_client_secret

# Optional Server-Side Cloud AI Keys (Preview only)
OPENAI_API_KEY=server_side_openai_api_key
GEMINI_API_KEY=server_side_gemini_api_key
CLAUDE_API_KEY=server_side_claude_api_key
```

*Note: Generating a Fernet key can be done by running:*
```powershell
.venv\Scripts\python.exe -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 4. End-to-End Walkthrough

Once the server is booted, use the following operational flow to navigate the features:

### 1. Authentication
* Open `http://localhost:8000` in your browser.
* Click **Login with GitHub** and authorize the OAuth request (requesting `repo` and `read:user` scopes).
* Once authenticated, you will be redirected to the secure **Overview Dashboard**.

### 2. Connection and Data Sync
* Go to the **Repositories** page in the sidebar.
* The system fetches your personal public and private repositories.
* Click **Connect** next to any repository to mount it to the local dashboard.
* Click **Sync** to trigger data aggregation. The backend fetches commits, PRs, issues, and authors, updating the state automatically from `pending` to `syncing` and finally `success`.

### 3. Explore Analytics Dashboards
* **Overview**: Health score gauge (0-100), executive cards, and activity timeline.
* **Commits**: Activity lines, author contributions, git heatmaps, and recent commit feeds.
* **Pull Requests**: Open/merged ratio, average merge turnaround time, and author PR loads.
* **Issues**: Label spreads, open/closed counts, and average resolution speed.

### 4. Interactive AI Tools
* Open **AI Tools** in the sidebar.
* **Commit Suggestion**: Paste a git diff into the text box and click Generate.
* **PR Code Review**: Paste branch diff changes to run a security and quality inspection.
* **Repo Assistant**: Ask natural-language questions about codebase structure or history.

### 5. Snapshot Reports and Exporting
* Open the **Reports** page.
* Generate a periodic Engineering Report to freeze current metrics into an immutable snapshot.
* Edit custom titles, toggle **Anonymize** to mask repository names on public views, and click **Publish** to generate a public capability URL.
* Download reports directly as **PDF** snapshots or **Excel** raw spreadsheets.
