from __future__ import annotations

from app.pdf_export.layout import (
    PDFLayout,
    PRIMARY,
    PRIMARY_DARK,
    SECONDARY,
    SUCCESS,
    WARNING,
    DANGER,
    BG_CARD,
    TEXT_DARK,
    TEXT_MUTED,
    BORDER,
)
from app.pdf_export.serializer import ReportData


class PDFRenderer:
    def __init__(self, layout: PDFLayout, data: ReportData) -> None:
        self.layout = layout
        self.data = data

    def render(self) -> bytes:
        p = self.layout
        self._render_title()
        self._render_metadata()
        self._render_kpi_cards()
        self._render_section_health()
        self._render_section_kpi_rankings()
        self._render_section_team()
        if self.data.insights:
            self._render_section_insights()
        return bytes(p.pdf.output())

    def _render_title(self) -> None:
        self.layout.title_block(
            self.data.title,
            subtitle="Production-Grade Engineering Analytics Snapshot",
        )

    def _render_metadata(self) -> None:
        p = self.layout
        for item in [
            ("Generated", self.data.generated_at),
            ("User", self.data.username),
            ("Scope", self.data.repository_scope),
            ("Format", self.data.export_type),
        ]:
            p.metadata_row(*item)
        p.pdf.ln(4)

    def _render_kpi_cards(self) -> None:
        p = self.layout
        p.section_heading("Key Performance Indicators")
        cards = [
            ("Repositories", str(self.data.summary.total_repositories), PRIMARY),
            ("Commits", str(self.data.summary.total_commits), SUCCESS),
            ("Pull Requests", str(self.data.summary.total_prs), WARNING),
            ("Issues", str(self.data.summary.total_issues), DANGER),
            ("Health Score", str(self.data.health.score), PRIMARY_DARK),
        ]
        x_start = p.MARGIN
        y = p.pdf.get_y()
        card_w = (p.CONTENT_W - 12) / 5
        card_h = 22
        for i, (label, value, color) in enumerate(cards):
            x = x_start + i * (card_w + 3)
            p.kpi_card(x, y, card_w, card_h, label, value, color)
        p.pdf.set_y(y + card_h + 6)

    def _render_section_health(self) -> None:
        p = self.layout
        p.section_heading("Repository Health")
        h = self.data.health
        pdf = p.pdf
        pdf.set_font("DejaVu", "B", p.SUBHEADING_SIZE)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(0, 7, f"Score: {h.score}/100  —  {h.status}", new_x="LMARGIN", new_y="NEXT")
        if h.recommendation:
            pdf.set_font("DejaVu", "", p.BODY_SIZE)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.multi_cell(0, 5, h.recommendation)
        if h.breakdown:
            pdf.ln(2)
            cols = ["Metric", "Score"]
            col_ws = [80, 30]
            p.table_header(cols, col_ws)
            for i, item in enumerate(h.breakdown):
                p.table_row([item.get("label", ""), str(item.get("value", 0))], col_ws, i)
        pdf.ln(4)

    def _render_section_kpi_rankings(self) -> None:
        p = self.layout
        p.check_page_overflow(50)
        p.section_heading("KPI Rankings")
        pdf = p.pdf
        cols = ["Category", "Top Performer", "Detail"]
        col_ws = [40, 55, 55]
        p.table_header(cols, col_ws)
        for i, item in enumerate(self.data.kpi_rankings):
            p.table_row([item.label, item.value, item.detail], col_ws, i)
        pdf.ln(4)

    def _render_section_team(self) -> None:
        p = self.layout
        needed = 20 + len(self.data.team.rows) * 8
        p.check_page_overflow(needed)
        p.section_heading("Team Activity")
        pdf = p.pdf
        team = self.data.team
        if team.rows:
            p.table_header(team.columns, team.col_widths)
            for i, row in enumerate(team.rows):
                fmts: list[str] | None = ["B"] if i == 0 else None
                p.table_row(row, team.col_widths, i, formats=fmts)
        else:
            pdf.set_font("DejaVu", "", p.BODY_SIZE)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(0, 7, "No team data available yet.", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    def _render_section_insights(self) -> None:
        p = self.layout
        p.check_page_overflow(30)
        p.section_heading("Key Insights")
        pdf = p.pdf
        for insight in self.data.insights:
            pdf.set_font("DejaVu", "", p.BODY_SIZE)
            pdf.set_text_color(*TEXT_DARK)
            pdf.cell(3, 6, chr(8226) + " ", align="C")
            pdf.cell(0, 6, insight, new_x="LMARGIN", new_y="NEXT")
