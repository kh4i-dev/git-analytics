from __future__ import annotations

import os
from fpdf import FPDF

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

PRIMARY = (37, 99, 235)
PRIMARY_DARK = (30, 64, 175)
SECONDARY = (100, 116, 139)
SUCCESS = (22, 163, 74)
WARNING = (234, 179, 8)
DANGER = (220, 38, 38)
BG_LIGHT = (248, 250, 252)
BG_CARD = (255, 255, 255)
BG_TABLE_HEADER = PRIMARY_DARK
BG_ROW_ODD = (241, 245, 249)
BG_ROW_EVEN = (255, 255, 255)
BORDER = (203, 213, 225)
TEXT_DARK = (15, 23, 42)
TEXT_MUTED = (100, 116, 139)
TEXT_WHITE = (255, 255, 255)
DIVIDER = (226, 232, 240)


class PDFLayout:
    FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
    FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")

    PAGE_W = 210
    PAGE_H = 297
    MARGIN = 20
    CONTENT_W = PAGE_W - 2 * MARGIN

    TITLE_SIZE = 22
    HEADING_SIZE = 14
    SUBHEADING_SIZE = 11
    BODY_SIZE = 10
    SMALL_SIZE = 8
    CARD_TITLE_SIZE = 9
    CARD_VALUE_SIZE = 18

    def __init__(self) -> None:
        self.pdf = FPDF(orientation="P", unit="mm", format="A4")
        self.pdf.add_font("Tahoma", "", self.FONT_REGULAR)
        self.pdf.add_font("Tahoma", "B", self.FONT_BOLD)
        self.page_count = 0

    def add_page(self) -> None:
        self.pdf.add_page()
        self.page_count += 1
        self._draw_header_bar()
        self._draw_footer()

    def _draw_header_bar(self) -> None:
        pdf = self.pdf
        pdf.set_fill_color(*PRIMARY)
        pdf.rect(0, 0, self.PAGE_W, 6, "F")
        pdf.set_fill_color(*PRIMARY_DARK)
        pdf.rect(0, 6, self.PAGE_W, 1, "F")

    def _draw_footer(self) -> None:
        pdf = self.pdf
        pdf.set_y(-12)
        pdf.set_font("Tahoma", "", self.SMALL_SIZE)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(0, 4, "Git Analytics Engineering Report", align="L")
        pdf.cell(0, 4, f"Page {self.page_count}", align="R", new_x="LMARGIN", new_y="NEXT")

    def title_block(self, title: str, subtitle: str | None = None) -> None:
        pdf = self.pdf
        pdf.set_font("Tahoma", "B", self.TITLE_SIZE)
        pdf.set_text_color(*PRIMARY_DARK)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            pdf.set_font("Tahoma", "", self.BODY_SIZE)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(0, 6, subtitle, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(3)

    def section_heading(self, text: str) -> None:
        pdf = self.pdf
        pdf.ln(2)
        pdf.set_font("Tahoma", "B", self.HEADING_SIZE)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")
        self.divider()

    def divider(self) -> None:
        pdf = self.pdf
        pdf.set_draw_color(*DIVIDER)
        pdf.set_line_width(0.3)
        y = pdf.get_y()
        pdf.line(self.MARGIN, y, self.PAGE_W - self.MARGIN, y)
        pdf.ln(3)

    def kpi_card(
        self, x: float, y: float, w: float, h: float,
        label: str, value: str, color: tuple[int, int, int],
    ) -> None:
        pdf = self.pdf
        pdf.set_fill_color(*BG_CARD)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.3)
        pdf.rect(x, y, w, h, "DF")
        left_stripe_w = 3
        pdf.set_fill_color(*color)
        pdf.rect(x, y, left_stripe_w, h, "F")
        pdf.set_font("Tahoma", "B", self.CARD_VALUE_SIZE)
        pdf.set_text_color(*TEXT_DARK)
        val_w = pdf.get_string_width(str(value)) + 2
        vx = x + (w - val_w) / 2
        vy = y + (h - self.CARD_VALUE_SIZE - self.CARD_TITLE_SIZE - 4) / 2 + 2
        pdf.set_xy(vx, vy)
        pdf.cell(val_w, self.CARD_VALUE_SIZE + 2, str(value), align="C")
        pdf.set_font("Tahoma", "", self.CARD_TITLE_SIZE)
        pdf.set_text_color(*TEXT_MUTED)
        label_w = pdf.get_string_width(str(label)) + 2
        lx = x + (w - label_w) / 2
        ly = vy + self.CARD_VALUE_SIZE + 3
        pdf.set_xy(lx, ly)
        pdf.cell(label_w, self.CARD_TITLE_SIZE + 1, str(label), align="C")

    def metadata_row(self, label: str, value: str) -> None:
        pdf = self.pdf
        pdf.set_font("Tahoma", "", self.BODY_SIZE)
        pdf.set_text_color(*TEXT_MUTED)
        label_w = pdf.get_string_width(label + ":  ") + 2
        pdf.cell(label_w, 6, label + ":  ")
        pdf.set_font("Tahoma", "B", self.BODY_SIZE)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(0, 6, value, new_x="LMARGIN", new_y="NEXT")

    def table_header(self, cols: list[str], col_widths: list[float]) -> None:
        pdf = self.pdf
        pdf.set_fill_color(*BG_TABLE_HEADER)
        pdf.set_text_color(*TEXT_WHITE)
        pdf.set_draw_color(*PRIMARY_DARK)
        pdf.set_font("Tahoma", "B", self.BODY_SIZE)
        for i, col in enumerate(cols):
            w = col_widths[i]
            align = "L" if i == 0 else "C"
            pdf.cell(w, 8, col, border=1, align=align, fill=True)
        pdf.ln()

    def table_row(
        self, cells: list[str], col_widths: list[float],
        row_index: int, formats: list[str] | None = None,
    ) -> None:
        pdf = self.pdf
        bg = BG_ROW_ODD if row_index % 2 == 0 else BG_ROW_EVEN
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("Tahoma", "", self.BODY_SIZE)
        for i, cell in enumerate(cells):
            w = col_widths[i]
            align = "L" if i == 0 else "C"
            is_bold = formats and i < len(formats) and formats[i] == "B"
            if is_bold:
                pdf.set_font("Tahoma", "B", self.BODY_SIZE)
            pdf.cell(w, 7, cell, border=1, align=align, fill=True)
            if is_bold:
                pdf.set_font("Tahoma", "", self.BODY_SIZE)
        pdf.ln()

    def check_page_overflow(self, needed: float = 30) -> None:
        if self.pdf.get_y() + needed > self.PAGE_H - 20:
            self.add_page()
