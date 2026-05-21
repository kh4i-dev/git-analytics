from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any
import unicodedata
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile


def remove_vietnamese_accents(text: str) -> str:
    char_map = {
        'đ': 'd', 'Đ': 'D',
        '—': '-', '–': '-',
        '“': '"', '”': '"',
        '‘': "'", '’': "'",
        '•': '*', '·': '*',
        '…': '...',
    }
    for k, v in char_map.items():
        text = text.replace(k, v)
    normalized = unicodedata.normalize('NFKD', text)
    cleaned = "".join(c for c in normalized if not unicodedata.combining(c))
    
    final_chars = []
    for c in cleaned:
        try:
            c.encode('latin-1')
            final_chars.append(c)
        except UnicodeEncodeError:
            final_chars.append('?')
    return "".join(final_chars)


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

    def to_pdf(self, rows: list[list[str]]) -> bytes:
        lines = ["Git Analytics Report"]
        for row in rows[2:]:
            if not row:
                lines.append("")
            else:
                lines.append("  ".join(row))
        stripped_lines = [remove_vietnamese_accents(line) for line in lines]
        return _simple_pdf(stripped_lines)


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


def _simple_pdf(lines: list[str]) -> bytes:
    escaped_lines = [_pdf_escape(line[:110]) for line in lines[:52]]
    text_ops = ["BT", "/F1 11 Tf", "50 780 Td"]
    first = True
    for line in escaped_lines:
        if first:
            first = False
        else:
            text_ops.append("0 -15 Td")
        text_ops.append(f"({line}) Tj")
    text_ops.append("ET")
    stream = "\n".join(text_ops).encode("latin-1", "replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref_offset = sum(len(chunk) for chunk in chunks)
    chunks.append(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        chunks.append(f"{offset:010d} 00000 n \n".encode())
    chunks.append(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode()
    )
    return b"".join(chunks)


def _pdf_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
