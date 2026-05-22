from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from app.pdf_export import PDFLayout, PDFRenderer, ReportSerializer


class AnalyticsExportService:
    def build_rows(self, stats: dict[str, Any]) -> list[list[str]]:
        team = stats.get("team", {})
        kpi = stats.get("kpi", {})
        rows: list[list[str]] = [
            ["Git Analytics Report", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")],
            [],
            ["Summary"],
            ["Repositories", str(stats["summary"]["total_repositories"])],
            ["Commits", str(stats["summary"]["total_commits"])],
            ["Pull Requests", str(stats["summary"]["total_prs"])],
            ["Issues", str(stats["summary"]["total_issues"])],
            ["Health Score", str(stats["health"]["score"])],
            ["Health Status", stats["health"]["status"]["label"]],
            [],
            ["KPI Ranking"],
            ["Top Contributor", kpi["top_contributor"]["name"], str(kpi["top_contributor"]["value"])],
            ["Top Issue Resolver", kpi["top_issue_resolver"]["name"], str(kpi["top_issue_resolver"]["value"])],
            ["Fastest Reviewer", kpi["fastest_reviewer"]["name"], str(kpi["fastest_reviewer"]["value"])],
            ["Most Active Repo", kpi["most_active_repo"]["full_name"], str(kpi["most_active_repo"]["score"])],
            [],
            ["Team Members"],
            ["GitHub Username", "Commits", "PR Merged", "Issues Resolved", "Active Days", "Activity Score"],
        ]
        for member in team.get("members", []):
            rows.append(
                [
                    str(member.get("login") or member.get("name") or "Unknown"),
                    str(member.get("commits", 0)),
                    str(member.get("prs_merged", 0)),
                    str(member.get("issues_closed", 0)),
                    str(member.get("active_days", 0)),
                    str(member.get("score", 0)),
                ]
            )
        return rows

    def to_xlsx(self, rows: list[list[str]]) -> bytes:
        buffer = BytesIO()
        with ZipFile(buffer, "w", ZIP_DEFLATED) as xlsx:
            xlsx.writestr("[Content_Types].xml", _content_types_xml())
            xlsx.writestr("_rels/.rels", _root_rels_xml())
            xlsx.writestr("xl/workbook.xml", _workbook_xml())
            xlsx.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml())
            xlsx.writestr("xl/worksheets/sheet1.xml", _worksheet_xml(rows))
        return buffer.getvalue()

    def to_pdf(self, stats: dict[str, Any], username: str | None = None) -> bytes:
        layout = PDFLayout()
        data = ReportSerializer().serialize(stats, username=username)
        renderer = PDFRenderer(layout, data)
        return renderer.render()


def _worksheet_xml(rows: list[list[str]]) -> str:
    row_xml = []
    for row_index, row in enumerate(rows, start=1):
        cells = []
        for col_index, value in enumerate(row, start=1):
            ref = f"{_col_name(col_index)}{row_index}"
            cells.append(f'<c r="{ref}" t="inlineStr"><is><t>{escape(value)}</t></is></c>')
        row_xml.append(f'<row r="{row_index}">{"".join(cells)}</row>')
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f'<sheetData>{"".join(row_xml)}</sheetData>'
        "</worksheet>"
    )


def _col_name(index: int) -> str:
    name = ""
    while index:
        index, remainder = divmod(index - 1, 26)
        name = chr(65 + remainder) + name
    return name


def _content_types_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<sheets><sheet name="Analytics KPI" sheetId="1" r:id="rId1"/></sheets>'
        "</workbook>"
    )


def _workbook_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
        "</Relationships>"
    )
