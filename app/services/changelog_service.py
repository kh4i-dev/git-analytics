from datetime import datetime, timedelta, UTC
from sqlalchemy.orm import Session
from app.repositories.changelog_repository import ChangelogRepository
from app.services.release_notes_service import ReleaseNotesService

CHANGELOG_MAPPING = {
    "feat": "Added",
    "fix": "Fixed",
    "refactor": "Changed",
    "perf": "Changed",
    "style": "Changed",
    "docs": "Other",
    "chore": "Other",
    "ci": "Other",
    "test": "Other",
    "breaking": "Changed",
    "other": "Other"
}

CHANGELOG_SECTIONS = {
    "Added": "✨ Added (Tính năng mới)",
    "Fixed": "🐛 Fixed (Sửa lỗi)",
    "Changed": "♻️ Changed (Thay đổi / Cải tiến)",
    "Other": "🔧 Other (Tài liệu / Chore / Khác)"
}

class ChangelogService:
    @staticmethod
    def generate_changelog(
        db: Session,
        repo_id: int,
        branch: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        group_by: str = "week"
    ) -> dict:
        repo_changelog = ChangelogRepository(db)
        
        from_date_dt = None
        if from_date:
            from_date_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        to_date_dt = None
        if to_date:
            to_date_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            
        commits = repo_changelog.get_commits_for_changelog(
            repo_id=repo_id,
            branch=branch,
            from_date=from_date_dt,
            to_date=to_date_dt
        )
        
        # Grouping container
        time_groups = {}
        
        for commit in commits:
            dt = commit.committed_at
            if not dt:
                continue
                
            # Parse key based on grouping mode
            if group_by == "month":
                group_key = dt.strftime("%Y-%m")
                group_title = dt.strftime("Tháng %m-%Y")
            else:  # week
                # Start of week (Monday)
                start_of_week = dt.date() - timedelta(days=dt.weekday())
                group_key = start_of_week.strftime("%Y-%m-%d")
                group_title = f"Tuần {start_of_week.strftime('%d-%m-%Y')}"
                
            if group_key not in time_groups:
                time_groups[group_key] = {
                    "title": group_title,
                    "sections": {sec: [] for sec in CHANGELOG_SECTIONS.keys()}
                }
                
            parsed = ReleaseNotesService.parse_commit_message(commit.message)
            ctype = parsed["type"]
            section = CHANGELOG_MAPPING.get(ctype, "Other")
            
            time_groups[group_key]["sections"][section].append({
                "short_sha": commit.sha[:7],
                "scope": parsed["scope"],
                "description": parsed["description"],
                "author": commit.author_login or commit.author_name,
                "html_url": commit.html_url
            })
            
        # Format Markdown Output
        md_lines = []
        md_lines.append("# Changelog")
        md_lines.append("")
        md_lines.append("Tất cả các thay đổi nổi bật đối với dự án này sẽ được ghi lại trong tệp này.")
        md_lines.append("Định dạng dựa trên [Keep a Changelog](https://keepachangelog.com/) chuẩn.")
        md_lines.append("")
        
        # Sort time groups descending
        sorted_keys = sorted(time_groups.keys(), reverse=True)
        
        sections_display = {}
        
        if not sorted_keys:
            md_lines.append("## [Unreleased]")
            md_lines.append("")
            md_lines.append("*Không có thay đổi nào được tìm thấy.*")
        else:
            for key in sorted_keys:
                grp = time_groups[key]
                md_lines.append(f"## {grp['title']}")
                md_lines.append("")
                
                has_content = False
                for sec, items in grp["sections"].items():
                    if items:
                        has_content = True
                        md_lines.append(f"### {sec}")
                        md_lines.append("")
                        for item in items:
                            scope_str = f"**{item['scope']}**: " if item["scope"] else ""
                            author_str = f" by @{item['author']}" if item["author"] else ""
                            sha_link = f"([`{item['short_sha']}`]({item['html_url']}))" if item["html_url"] else f"(`{item['short_sha']}`)"
                            md_lines.append(f"- {scope_str}{item['description']}{author_str} {sha_link}")
                        md_lines.append("")
                if not has_content:
                    md_lines.append("*Không có thay đổi nào.*")
                    md_lines.append("")
                    
            # Let's map sections for frontend rendering
            for key in sorted_keys:
                grp = time_groups[key]
                sections_display[grp["title"]] = {
                    CHANGELOG_SECTIONS[sec]: items for sec, items in grp["sections"].items() if len(items) > 0
                }
                
        markdown = "\n".join(md_lines)
        return {
            "markdown": markdown,
            "sections": sections_display,
            "commit_count": len(commits),
            "date_range": f"{from_date or ''} - {to_date or ''}"
        }
