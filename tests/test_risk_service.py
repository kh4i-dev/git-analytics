import pytest
from datetime import datetime, timedelta, UTC
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.db.base import Base
from app.models.user import User
from app.models.repository import Repository
from app.models.branch import Branch
from app.models.pull_request import PullRequest
from app.models.issue import Issue
from app.models.contributor import Contributor
from app.models.commit import Commit
from app.services.risk_insight_service import RiskInsightService


def test_risk_insight_service_all_rules() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, class_=Session)
    db = session_factory()

    try:
        # 1. Create a User
        user = User(
            github_id=999,
            github_login="risk-tester",
            encrypted_github_token="encrypted"
        )
        db.add(user)
        db.commit()

        # 2. Create Repositories
        # Repo 1: Active
        repo_active = Repository(
            user_id=user.id,
            github_repo_id=101,
            owner="risk-tester",
            name="repo-active",
            full_name="risk-tester/repo-active",
            is_private=False,
            default_branch="main",
            html_url="https://github.com/risk-tester/repo-active",
            created_at=datetime.now(UTC) - timedelta(days=60),
            last_synced_at=datetime.now(UTC) - timedelta(minutes=10),
            last_sync_status="success"
        )
        # Repo 2: Inactive (>14 days)
        repo_inactive = Repository(
            user_id=user.id,
            github_repo_id=102,
            owner="risk-tester",
            name="repo-inactive",
            full_name="risk-tester/repo-inactive",
            is_private=False,
            default_branch="main",
            html_url="https://github.com/risk-tester/repo-inactive",
            created_at=datetime.now(UTC) - timedelta(days=60),
            last_synced_at=datetime.now(UTC) - timedelta(days=20),
            last_sync_status="success"
        )
        # Repo 3: Failed Sync
        repo_failed_sync = Repository(
            user_id=user.id,
            github_repo_id=103,
            owner="risk-tester",
            name="repo-failed",
            full_name="risk-tester/repo-failed",
            is_private=False,
            default_branch="main",
            html_url="https://github.com/risk-tester/repo-failed",
            created_at=datetime.now(UTC) - timedelta(days=5),
            last_synced_at=datetime.now(UTC) - timedelta(days=1),
            last_sync_status="failed",
            last_sync_error="API limit reached"
        )
        db.add_all([repo_active, repo_inactive, repo_failed_sync])
        db.commit()

        # Seed recent commit to Repo 1 (so it remains active)
        c_active = Commit(
            repo_id=repo_active.id,
            sha="a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1",
            message="feat: push some updates",
            author_name="risk-tester",
            author_email="test@example.com",
            author_login="risk-tester",
            committed_at=datetime.now(UTC) - timedelta(days=1),
            branch_name="main",
            html_url="https://github.com/risk-tester/repo-active/commit/a1a1a1a"
        )
        # Seed stale commit to Repo 2 (>14 days ago)
        c_inactive = Commit(
            repo_id=repo_inactive.id,
            sha="i1i1i1i1i1i1i1i1i1i1i1i1i1i1i1i1i1i1i1i1",
            message="feat: initial commit",
            author_name="risk-tester",
            author_email="test@example.com",
            author_login="risk-tester",
            committed_at=datetime.now(UTC) - timedelta(days=20),
            branch_name="main",
            html_url="https://github.com/risk-tester/repo-inactive/commit/i1i1i1i"
        )
        db.add_all([c_active, c_inactive])
        db.commit()

        # Seed Stale Branch in Repo 1 (>30 days ago)
        branch_stale = Branch(
            repository_id=repo_active.id,
            github_branch_name="stale-feature",
            is_default=False,
            created_at=datetime.now(UTC) - timedelta(days=40),
            synced_at=datetime.now(UTC) - timedelta(days=40)
        )
        # Stale commit on this branch
        c_stale_branch = Commit(
            repo_id=repo_active.id,
            sha="s2s2s2s2s2s2s2s2s2s2s2s2s2s2s2s2s2s2s2s2",
            message="feat: work on stale feature",
            author_name="risk-tester",
            author_email="test@example.com",
            committed_at=datetime.now(UTC) - timedelta(days=40),
            branch_name="stale-feature",
            html_url="https://github.com/risk-tester/repo-active/commit/s2s2s2s"
        )
        db.add(branch_stale)
        db.add(c_stale_branch)
        db.commit()

        # Seed Open PR open too long (>7 days ago) in Repo 1
        pr_old = PullRequest(
            repo_id=repo_active.id,
            number=42,
            title="Sleek UI redesign",
            state="open",
            html_url="https://github.com/risk-tester/repo-active/pull/42",
            author_login="risk-tester",
            created_at=datetime.now(UTC) - timedelta(days=10),
            updated_at=datetime.now(UTC) - timedelta(days=10)
        )
        db.add(pr_old)
        db.commit()

        # Seed Old unresolved issue (>30 days ago) in Repo 1
        issue_old = Issue(
            repo_id=repo_active.id,
            number=7,
            title="Database slow query issues",
            state="open",
            html_url="https://github.com/risk-tester/repo-active/issues/7",
            author_login="risk-tester",
            created_at=datetime.now(UTC) - timedelta(days=35),
            updated_at=datetime.now(UTC) - timedelta(days=35)
        )
        db.add(issue_old)
        db.commit()

        # Seed High Bus Factor in Repo 1 (let's create 5 commits total in last 90 days, 4 by Alice, 1 by Bob)
        # (c_active + c_stale_branch are already 2 commits. Let's add 3 more to reach minimum 5 commits)
        b1 = Commit(
            repo_id=repo_active.id,
            sha="b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1",
            message="feat: additional changes 1",
            author_name="Alice",
            author_login="alice",
            author_email="alice@example.com",
            committed_at=datetime.now(UTC) - timedelta(days=5),
            branch_name="main",
            html_url="https://github.com/risk-tester/repo-active/commit/b1b1b1b"
        )
        b2 = Commit(
            repo_id=repo_active.id,
            sha="b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2",
            message="feat: additional changes 2",
            author_name="Alice",
            author_login="alice",
            author_email="alice@example.com",
            committed_at=datetime.now(UTC) - timedelta(days=4),
            branch_name="main",
            html_url="https://github.com/risk-tester/repo-active/commit/b2b2b2b"
        )
        b3 = Commit(
            repo_id=repo_active.id,
            sha="b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3b3",
            message="feat: additional changes 3",
            author_name="Alice",
            author_login="alice",
            author_email="alice@example.com",
            committed_at=datetime.now(UTC) - timedelta(days=3),
            branch_name="main",
            html_url="https://github.com/risk-tester/repo-active/commit/b3b3b3b"
        )
        # Note: c_active, c_stale_branch were by "risk-tester" (2 commits).
        # Alice has 3 commits. Let's make one more by Alice to reach >=80% threshold (4 out of 5 commits)
        b4 = Commit(
            repo_id=repo_active.id,
            sha="b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4b4",
            message="feat: additional changes 4",
            author_name="Alice",
            author_login="alice",
            author_email="alice@example.com",
            committed_at=datetime.now(UTC) - timedelta(days=2),
            branch_name="main",
            html_url="https://github.com/risk-tester/repo-active/commit/b4b4b4b"
        )
        db.add_all([b1, b2, b3, b4])
        db.commit()

        # Run risk evaluation
        risks = RiskInsightService.detect_risks(db, user_id=user.id)
        
        # Verify detected risks
        rule_ids = [r["rule_id"] for r in risks]
        
        # 1. Inactive Repo (repo-inactive)
        assert "inactive_repo" in rule_ids
        
        # 2. Stale branch (stale-feature)
        assert "stale_branch" in rule_ids
        
        # 3. PR open too long (PR #42)
        assert "pr_open_too_long" in rule_ids
        
        # 4. Old open issue (Issue #7)
        assert "unresolved_issues" in rule_ids
        
        # 5. Failed sync (repo-failed)
        assert "stale_sync" in rule_ids
        
        # 6. Bus Factor (Alice has 4 out of 6 commits ~ 66.7%, so under 80% threshold)
        # Let's verify Alice doesn't trigger bus factor since it is under 80%
        bus_factor_risks = [r for r in risks if r["rule_id"] == "bus_factor"]
        assert len(bus_factor_risks) == 0

        # Let's add 5 more commits by Alice to make it 9 out of 11 commits (~81.8% >= 80%)
        for i in range(5):
            c = Commit(
                repo_id=repo_active.id,
                sha=f"alicecommit{i}a1a1a1a1a1a1a1a1a1a1a1a1a1a1a1a",
                message=f"feat: alice commit {i}",
                author_name="Alice",
                author_login="alice",
                author_email="alice@example.com",
                committed_at=datetime.now(UTC) - timedelta(days=1),
                branch_name="main",
                html_url=f"https://github.com/risk-tester/repo-active/commit/alicecommit{i}"
            )
            db.add(c)
        db.commit()

        risks_new = RiskInsightService.detect_risks(db, user_id=user.id)
        new_rule_ids = [r["rule_id"] for r in risks_new]
        assert "bus_factor" in new_rule_ids

        # Verify summary counts
        summary = RiskInsightService.get_risk_summary(db, user_id=user.id)
        assert summary["total"] == len(risks_new)
        assert summary["high"] >= 1  # Bus Factor is high, PR open too long is high

    finally:
        db.close()
        engine.dispose()
