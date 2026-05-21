import re
from datetime import datetime
from sqlalchemy.orm import Session
from app.repositories.release_notes_repository import ReleaseNotesRepository

COMMIT_TYPES = {
    "feat":     "✨ Tính năng mới",
    "fix":      "🐛 Sửa lỗi",
    "docs":     "📝 Tài liệu",
    "refactor": "♻️ Refactor",
    "chore":    "🔧 Chore",
    "perf":     "⚡ Hiệu năng",
    "test":     "🧪 Tests",
    "style":    "💄 Style",
    "ci":       "👷 CI/CD",
    "breaking": "💥 Breaking Changes",
    "other":    "🧪 Khác",
}

CONVENTIONAL_REGEX = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|chore|ci|build|revert)(?:\(([^)]+)\))?(!)?:\s(.+)",
    re.IGNORECASE
)

class ReleaseNotesService:
    @staticmethod
    def parse_commit_message(message: str | None) -> dict:
        if not message:
            return {"type": "other", "scope": None, "description": "", "is_breaking": False}
        
        # Trim leading/trailing spaces and take the first line for header parsing
        first_line = message.strip().split("\n")[0].strip()
        
        # Check for breaking change anywhere in the message body
        is_breaking = "BREAKING CHANGE" in message or "BREAKING CHANGES" in message
        
        match = CONVENTIONAL_REGEX.match(first_line)
        if match:
            ctype = match.group(1).lower()
            scope = match.group(2)
            breaking_bang = match.group(3) is not None
            description = match.group(4).strip()
            
            if breaking_bang:
                is_breaking = True
                
            # If revert is matched, map it to fix or keep as other
            if ctype == "revert":
                ctype = "fix"
            elif ctype == "build":
                ctype = "chore"
                
            return {
                "type": "breaking" if is_breaking else ctype,
                "scope": scope,
                "description": description,
                "is_breaking": is_breaking
            }
        else:
            return {
                "type": "breaking" if is_breaking else "other",
                "scope": None,
                "description": first_line,
                "is_breaking": is_breaking
            }

    @staticmethod
    def generate_release_notes(
        db: Session,
        repo_id: int,
        branch: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        version_tag: str = "",
    ) -> dict:
        repo_notes = ReleaseNotesRepository(db)
        
        from_date_dt = None
        if from_date:
            from_date_dt = datetime.fromisoformat(from_date.replace("Z", "+00:00"))
        to_date_dt = None
        if to_date:
            to_date_dt = datetime.fromisoformat(to_date.replace("Z", "+00:00"))
            
        commits = repo_notes.get_commits_for_release(
            repo_id=repo_id,
            branch=branch,
            from_date=from_date_dt,
            to_date=to_date_dt
        )
        
        # Initialize groups
        groups = {k: [] for k in COMMIT_TYPES.keys()}
        
        for commit in commits:
            parsed = ReleaseNotesService.parse_commit_message(commit.message)
            ctype = parsed["type"]
            if ctype not in groups:
                ctype = "other"
                
            groups[ctype].append({
                "sha": commit.sha,
                "short_sha": commit.sha[:7],
                "message": commit.message,
                "author": commit.author_login or commit.author_name,
                "date": commit.committed_at.isoformat() if commit.committed_at else None,
                "scope": parsed["scope"],
                "description": parsed["description"],
                "html_url": commit.html_url
            })
            
        # Filter out empty groups for display
        active_groups = {k: v for k, v in groups.items() if len(v) > 0}
        
        # Calculate stats
        total_commits = len(commits)
        stats = {
            "total_commits": total_commits,
            "breakdown": {COMMIT_TYPES[k]: len(v) for k, v in active_groups.items()}
        }
        
        # Generate Markdown output
        tag_title = f" {version_tag}" if version_tag else ""
        date_str = datetime.now().strftime("%Y-%m-%d")
        
        md_lines = []
        md_lines.append(f"# Release Notes{tag_title} ({date_str})")
        md_lines.append("")
        
        if from_date or to_date:
            range_str = []
            if from_date:
                range_str.append(f"từ {from_date_dt.strftime('%Y-%m-%d')}")
            if to_date:
                range_str.append(f"đến {to_date_dt.strftime('%Y-%m-%d')}")
            md_lines.append(f"> 📅 Khoảng thời gian: {' '.join(range_str)}")
        if branch and branch != "all":
            md_lines.append(f"> 🌿 Nhánh: `{branch}`")
        md_lines.append("")
        
        if total_commits == 0:
            md_lines.append("*Không có thay đổi nào trong khoảng thời gian này.*")
        else:
            # Order sections logically: breaking first, then feat, fix, etc.
            ordered_keys = ["breaking", "feat", "fix", "refactor", "perf", "docs", "style", "test", "ci", "chore", "other"]
            for key in ordered_keys:
                if key in active_groups:
                    md_lines.append(f"## {COMMIT_TYPES[key]}")
                    md_lines.append("")
                    for c in active_groups[key]:
                        scope_str = f"**{c['scope']}**: " if c["scope"] else ""
                        author_str = f" by @{c['author']}" if c["author"] else ""
                        sha_link = f"([`{c['short_sha']}`]({c['html_url']}))" if c["html_url"] else f"(`{c['short_sha']}`)"
                        md_lines.append(f"- {scope_str}{c['description']}{author_str} {sha_link}")
                    md_lines.append("")
                    
            # Add summary stats in MD
            md_lines.append("---")
            md_lines.append("### 📊 Thống kê")
            md_lines.append(f"- **Tổng số commits**: {total_commits}")
            for name, count in stats["breakdown"].items():
                md_lines.append(f"- **{name}**: {count}")
                
        markdown_output = "\n".join(md_lines)
        
        # Display name mapping for active groups
        grouped_data = {COMMIT_TYPES[k]: v for k, v in active_groups.items()}
        
        return {
            "version": version_tag,
            "date_range": f"{from_date or ''} - {to_date or ''}",
            "groups": grouped_data,
            "markdown_output": markdown_output,
            "stats": stats
        }
