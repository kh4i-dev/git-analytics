from datetime import datetime, UTC
from sqlalchemy.orm import Session
from app.repositories.risk_repository import RiskRepository

class RiskInsightService:
    @staticmethod
    def detect_risks(db: Session, user_id: int, repo_id: int | None = None) -> list[dict]:
        repo_risks = RiskRepository(db)
        
        # 1. Inactive Repositories
        inactive_repos = repo_risks.get_inactive_repositories(user_id, threshold_days=14)
        # 2. Stale Branches
        stale_branches = repo_risks.get_stale_branches(user_id, threshold_days=30)
        # 3. Open PRs too long
        old_prs = repo_risks.get_old_open_prs(user_id, threshold_days=7)
        # 4. Old open issues
        old_issues = repo_risks.get_old_open_issues(user_id, threshold_days=30)
        # 5. Inactive contributors
        inactive_contribs = repo_risks.get_inactive_contributors(user_id, threshold_days=14)
        # 6. Bus factor risks
        bus_factors = repo_risks.get_bus_factor_risks(user_id, threshold_percentage=0.8)
        # 7. Stale syncs
        stale_syncs = repo_risks.get_stale_syncs(user_id, threshold_hours=24)
        
        detected = []
        
        # Inactive Repos
        for item in inactive_repos:
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            last_commit = item["last_commit_at"]
            detail = (
                f"Kho lưu trữ không có commit nào trong 14 ngày qua (Commit gần nhất: {last_commit.strftime('%Y-%m-%d')})"
                if last_commit else
                "Kho lưu trữ chưa có commit nào được đồng bộ"
            )
            detected.append({
                "rule_id": "inactive_repo",
                "name": "Repo không hoạt động",
                "severity": "medium",
                "affected": repo.full_name,
                "repo_id": repo.id,
                "detail": detail,
                "detected_at": datetime.now(UTC).isoformat()
            })
            
        # Stale Branches
        for item in stale_branches:
            branch = item["branch"]
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            last_commit = item["last_commit_at"]
            detail = (
                f"Nhánh '{branch.github_branch_name}' không có commit mới trong 30 ngày qua (Hoạt động gần nhất: {last_commit.strftime('%Y-%m-%d')})"
                if last_commit else
                f"Nhánh '{branch.github_branch_name}' chưa có commit được đồng bộ"
            )
            detected.append({
                "rule_id": "stale_branch",
                "name": "Branch cũ chưa merge",
                "severity": "low",
                "affected": f"{repo.name}:{branch.github_branch_name}",
                "repo_id": repo.id,
                "detail": detail,
                "detected_at": datetime.now(UTC).isoformat()
            })
            
        # Open PRs too long
        for item in old_prs:
            pr = item["pr"]
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            detected.append({
                "rule_id": "pr_open_too_long",
                "name": "PR mở quá lâu",
                "severity": "high",
                "affected": f"{repo.name}#{pr.number}",
                "repo_id": repo.id,
                "detail": f"Pull Request #{pr.number} '{pr.title}' đã mở trong {item['days_open']} ngày chưa được merge",
                "detected_at": datetime.now(UTC).isoformat(),
                "url": pr.html_url
            })
            
        # Old unresolved issues
        for item in old_issues:
            issue = item["issue"]
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            detected.append({
                "rule_id": "unresolved_issues",
                "name": "Issue tồn đọng",
                "severity": "medium",
                "affected": f"{repo.name}#{issue.number}",
                "repo_id": repo.id,
                "detail": f"Issue #{issue.number} '{issue.title}' đã ở trạng thái Open trong {item['days_open']} ngày",
                "detected_at": datetime.now(UTC).isoformat(),
                "url": issue.html_url
            })
            
        # Inactive Contributors
        for item in inactive_contribs:
            contrib = item["contributor"]
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            last_commit = item["last_commit_at"]
            detail = (
                f"Thành viên không đóng góp commit nào trong 14 ngày qua (Hoạt động gần nhất: {last_commit.strftime('%Y-%m-%d')})"
                if last_commit else
                "Chưa ghi nhận đóng góp nào"
            )
            detected.append({
                "rule_id": "low_contributor",
                "name": "Contributor ít hoạt động",
                "severity": "low",
                "affected": contrib.display_name or contrib.github_login or "Thành viên ẩn danh",
                "repo_id": repo.id,
                "detail": detail,
                "detected_at": datetime.now(UTC).isoformat()
            })
            
        # Bus Factor Risks
        for item in bus_factors:
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            percentage_str = f"{item['percentage'] * 100:.1f}"
            detected.append({
                "rule_id": "bus_factor",
                "name": "Bus factor cao",
                "severity": "high",
                "affected": repo.full_name,
                "repo_id": repo.id,
                "detail": f"Thành viên '{item['top_contributor']}' chiếm {percentage_str}% số lượng commit ({item['top_commits']}/{item['total_commits']}) trong 90 ngày qua",
                "detected_at": datetime.now(UTC).isoformat()
            })
            
        # Stale Syncs
        for item in stale_syncs:
            repo = item["repo"]
            if repo_id and repo.id != repo_id:
                continue
            detected.append({
                "rule_id": "stale_sync",
                "name": "Đồng bộ bị lỗi / chậm trễ",
                "severity": "medium",
                "affected": repo.full_name,
                "repo_id": repo.id,
                "detail": item["detail"],
                "detected_at": datetime.now(UTC).isoformat()
            })
            
        return detected

    @staticmethod
    def get_risk_summary(db: Session, user_id: int, repo_id: int | None = None) -> dict:
        risks = RiskInsightService.detect_risks(db, user_id, repo_id=repo_id)
        
        summary = {
            "total": len(risks),
            "high": sum(1 for r in risks if r["severity"] == "high"),
            "medium": sum(1 for r in risks if r["severity"] == "medium"),
            "low": sum(1 for r in risks if r["severity"] == "low"),
            "by_repo": {}
        }
        
        # Calculate by repo
        for r in risks:
            rid = r["repo_id"]
            if rid not in summary["by_repo"]:
                summary["by_repo"][rid] = {
                    "total": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                }
            summary["by_repo"][rid]["total"] += 1
            summary["by_repo"][rid][r["severity"]] += 1
            
        return summary
