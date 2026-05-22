from __future__ import annotations

import os
from fpdf import FPDF

FONT_DIR = os.path.join(os.path.dirname(__file__), "fonts")

# Premium Slate & Sapphire Visual Theme
PRIMARY = (37, 99, 235)       # Elegant Sapphire Blue
PRIMARY_DARK = (15, 23, 42)    # Sophisticated Charcoal Dark
SECONDARY = (71, 85, 105)      # Slate Slate-600 Muted
SUCCESS = (16, 185, 129)      # Emerald Green
WARNING = (245, 158, 11)      # Amber Orange
DANGER = (239, 68, 68)        # Coral Red
BG_LIGHT = (248, 250, 252)    # Slate-50 Light Background
BG_CARD = (255, 255, 255)     # Solid White Card
BG_TABLE_HEADER = PRIMARY_DARK # Sophisticated Dark Header
BG_ROW_ODD = (248, 250, 252)  # Soft Alternate Slate-50
BG_ROW_EVEN = (255, 255, 255) # Pure White Row
BORDER = (226, 232, 240)      # Slate-200 Border Line
TEXT_DARK = (15, 23, 42)      # Deep Obsidian Text
TEXT_MUTED = (100, 116, 139)  # Slate-500 Caption Text
TEXT_WHITE = (255, 255, 255)  # Crisp White
DIVIDER = (241, 245, 249)     # Soft slate-100 Divider Line


class _PDFDoc(FPDF):
    FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")
    FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")

    def __init__(self) -> None:
        super().__init__(orientation="P", unit="mm", format="A4")
        self.add_font("DejaVu", "", self.FONT_REGULAR)
        self.add_font("DejaVu", "B", self.FONT_BOLD)
        self.set_auto_page_break(auto=True, margin=15)

    def header(self) -> None:
        # Ultra-premium header top accent strip
        self.set_fill_color(*PRIMARY)
        self.rect(0, 0, 210, 4, "F")
        self.set_fill_color(*PRIMARY_DARK)
        self.rect(0, 4, 210, 1.2, "F")
        
        # Subtle running head (only on page > 1)
        if self.page_no() > 1:
            self.set_y(8)
            self.set_font("DejaVu", "", 8)
            self.set_text_color(*SECONDARY)
            self.cell(0, 5, "Git Analytics — Engineering Executive Summary", align="L")
            self.set_draw_color(*DIVIDER)
            self.set_line_width(0.2)
            self.line(20, 13.5, 190, 13.5)
        self.set_y(15)

    def footer(self) -> None:
        self.set_y(-15)
        # Elegant thin bottom divider
        self.set_draw_color(*DIVIDER)
        self.set_line_width(0.2)
        self.line(20, 282, 190, 282)
        
        self.set_y(-12)
        self.set_font("DejaVu", "", 8)
        self.set_text_color(*TEXT_MUTED)
        self.cell(100, 5, "Git Analytics Platform — Engineering Intelligence", align="L")
        self.set_x(-40)
        self.cell(20, 5, f"Page {self.page_no()}", align="R")


class PDFLayout:
    PAGE_W = 210
    PAGE_H = 297
    MARGIN = 20
    CONTENT_W = PAGE_W - 2 * MARGIN

    TITLE_SIZE = 20
    HEADING_SIZE = 13
    SUBHEADING_SIZE = 10
    BODY_SIZE = 9
    SMALL_SIZE = 7.5
    CARD_TITLE_SIZE = 8
    CARD_VALUE_SIZE = 15

    def __init__(self) -> None:
        self.pdf = _PDFDoc()
        self.pdf.add_page()

    def add_page(self) -> None:
        self.pdf.add_page()

    def title_block(self, title: str, subtitle: str | None = None) -> None:
        pdf = self.pdf
        pdf.set_font("DejaVu", "B", self.TITLE_SIZE)
        pdf.set_text_color(*PRIMARY_DARK)
        pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
        if subtitle:
            pdf.set_font("DejaVu", "", self.BODY_SIZE)
            pdf.set_text_color(*TEXT_MUTED)
            pdf.cell(0, 5, subtitle, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    def section_heading(self, text: str) -> None:
        pdf = self.pdf
        pdf.ln(3)
        y = pdf.get_y()
        
        # Left accent vertical colored tag (Stripe-style)
        pdf.set_fill_color(*PRIMARY)
        pdf.rect(self.MARGIN, y + 1.2, 3, 5.5, "F")
        
        pdf.set_xy(self.MARGIN + 5, y)
        pdf.set_font("DejaVu", "B", self.HEADING_SIZE)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(0, 8, text, new_x="LMARGIN", new_y="NEXT")
        self.divider()

    def divider(self) -> None:
        pdf = self.pdf
        pdf.set_draw_color(*DIVIDER)
        pdf.set_line_width(0.2)
        y = pdf.get_y()
        pdf.line(self.MARGIN, y, self.PAGE_W - self.MARGIN, y)
        pdf.ln(3)

    def kpi_card(
        self, x: float, y: float, w: float, h: float,
        label: str, value: str, color: tuple[int, int, int],
    ) -> None:
        pdf = self.pdf
        # Card body with standard professional light slate shadow outline
        pdf.set_fill_color(*BG_CARD)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.25)
        pdf.rect(x, y, w, h, "DF")
        
        # Sleek vertical color tag stripe on the left edge
        left_stripe_w = 2.5
        pdf.set_fill_color(*color)
        pdf.rect(x, y, left_stripe_w, h, "F")
        
        # Left-aligned bold metric value
        pdf.set_xy(x + left_stripe_w + 3, y + 2)
        pdf.set_font("DejaVu", "B", self.CARD_VALUE_SIZE)
        pdf.set_text_color(*TEXT_DARK)
        pdf.cell(w - left_stripe_w - 5, 8, str(value), align="L")
        
        # Upper-cased small label description underneath
        pdf.set_xy(x + left_stripe_w + 3, y + 11)
        pdf.set_font("DejaVu", "", self.CARD_TITLE_SIZE)
        pdf.set_text_color(*TEXT_MUTED)
        pdf.cell(w - left_stripe_w - 5, 5, str(label).upper(), align="L")

    def metadata_block(self, items: list[tuple[str, str]]) -> None:
        pdf = self.pdf
        pdf.set_fill_color(*BG_LIGHT)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.25)
        
        y_start = pdf.get_y()
        box_h = 9
        pdf.rect(self.MARGIN, y_start, self.CONTENT_W, box_h, "DF")
        
        col_w = self.CONTENT_W / len(items)
        for i, (label, val) in enumerate(items):
            x = self.MARGIN + i * col_w
            pdf.set_xy(x + 3, y_start + 1.5)
            pdf.set_font("DejaVu", "", 8)
            pdf.set_text_color(*TEXT_MUTED)
            lbl = f"{label}: "
            pdf.cell(pdf.get_string_width(lbl), 6, lbl)
            
            pdf.set_font("DejaVu", "B", 8)
            pdf.set_text_color(*TEXT_DARK)
            pdf.cell(0, 6, val)
            
        pdf.set_xy(self.MARGIN, y_start + box_h + 3)

    def table_header(self, cols: list[str], col_widths: list[float]) -> None:
        pdf = self.pdf
        pdf.set_fill_color(*BG_TABLE_HEADER)
        pdf.set_text_color(*TEXT_WHITE)
        pdf.set_font("DejaVu", "B", self.BODY_SIZE)
        for i, col in enumerate(cols):
            w = col_widths[i]
            align = "L" if i == 0 else "C"
            pdf.cell(w, 8.5, "  " + col if i == 0 else col, border=0, align=align, fill=True)
        pdf.ln()

    def table_row(
        self, cells: list[str], col_widths: list[float],
        row_index: int, formats: list[str] | None = None,
    ) -> None:
        pdf = self.pdf
        bg = BG_ROW_ODD if row_index % 2 == 0 else BG_ROW_EVEN
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*TEXT_DARK)
        pdf.set_font("DejaVu", "", self.BODY_SIZE)
        pdf.set_draw_color(*BORDER)
        pdf.set_line_width(0.2)
        for i, cell in enumerate(cells):
            w = col_widths[i]
            align = "L" if i == 0 else "C"
            is_bold = formats and i < len(formats) and formats[i] == "B"
            if is_bold:
                pdf.set_font("DejaVu", "B", self.BODY_SIZE)
            # Modern horizontal border only: border="B"
            pdf.cell(w, 7.5, "  " + cell if i == 0 else cell, border="B", align=align, fill=True)
            if is_bold:
                pdf.set_font("DejaVu", "", self.BODY_SIZE)
        pdf.ln()

    def insight_callout(self, insights: list[str]) -> None:
        pdf = self.pdf
        pdf.ln(1)
        
        # Soft premium blue container block
        pdf.set_fill_color(240, 246, 255)
        pdf.set_draw_color(*PRIMARY)
        pdf.set_line_width(0.25)
        
        y_start = pdf.get_y()
        h_needed = 4 + len(insights) * 7.5
        
        # Draw soft filled rectangle
        pdf.rect(self.MARGIN, y_start, self.CONTENT_W, h_needed, "F")
        # Draw thick primary blue stripe on the left edge
        pdf.set_fill_color(*PRIMARY)
        pdf.rect(self.MARGIN, y_start, 3.5, h_needed, "F")
        
        for i, insight in enumerate(insights):
            pdf.set_xy(self.MARGIN + 7, y_start + 2.5 + i * 7.5)
            pdf.set_font("DejaVu", "", self.BODY_SIZE)
            pdf.set_text_color(*PRIMARY_DARK)
            pdf.cell(3, 5, chr(8226) + " ", align="C")
            pdf.set_text_color(*TEXT_DARK)
            pdf.cell(0, 5, insight)
            
        pdf.set_xy(self.MARGIN, y_start + h_needed + 3)

    def check_page_overflow(self, needed: float = 30) -> None:
        if self.pdf.get_y() + needed > self.PAGE_H - 15:
            self.add_page()

