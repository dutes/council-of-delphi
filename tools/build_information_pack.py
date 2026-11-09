from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics
from reportlab.platypus import (
    Flowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "jev-crowd-council-experiment-information-pack.pdf"

NAVY = colors.HexColor("#14213D")
BLUE = colors.HexColor("#2D6CDF")
CYAN = colors.HexColor("#48CAE4")
TEAL = colors.HexColor("#159A9C")
GREEN = colors.HexColor("#2A9D5B")
AMBER = colors.HexColor("#E9A23B")
RED = colors.HexColor("#D95D5D")
INK = colors.HexColor("#243044")
MUTED = colors.HexColor("#637083")
PALE = colors.HexColor("#F3F6FA")
LINE = colors.HexColor("#D9E1EA")
WHITE = colors.white


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/aptos.ttf")
    bold = Path("C:/Windows/Fonts/aptos-bold.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("PackSans", str(regular)))
        pdfmetrics.registerFont(TTFont("PackSans-Bold", str(bold)))
        return "PackSans", "PackSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


class AccuracyBars(Flowable):
    def __init__(self, data: list[tuple[str, float, colors.Color]], width=170 * mm, height=96 * mm):
        super().__init__()
        self.data = data
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        label_w = 59 * mm
        chart_w = self.width - label_w - 18 * mm
        top = self.height - 9 * mm
        row_h = 13 * mm
        c.setFont(FONT, 7.5)
        c.setFillColor(MUTED)
        for tick in (0, 20, 40, 60, 80, 100):
            x = label_w + chart_w * tick / 100
            c.setStrokeColor(LINE)
            c.setLineWidth(0.4)
            c.line(x, 5 * mm, x, top + 4 * mm)
            c.drawCentredString(x, 1 * mm, str(tick))
        for i, (label, value, color) in enumerate(self.data):
            y = top - i * row_h
            c.setFillColor(INK)
            c.setFont(FONT, 8.3)
            c.drawRightString(label_w - 3 * mm, y + 2.2 * mm, label)
            c.setFillColor(colors.HexColor("#E8EDF3"))
            c.roundRect(label_w, y, chart_w, 6 * mm, 2 * mm, fill=1, stroke=0)
            c.setFillColor(color)
            c.roundRect(label_w, y, chart_w * value / 100, 6 * mm, 2 * mm, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont(FONT_BOLD, 8.5)
            c.drawString(label_w + chart_w + 3 * mm, y + 2.0 * mm, f"{value:.2f}%")


class PipelineDiagram(Flowable):
    def __init__(self, width=170 * mm, height=80 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw_box(self, c, x, y, w, h, title, sub, color):
        c.setFillColor(color)
        c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(x + w / 2, y + h - 6 * mm, title)
        c.setFont(FONT, 6.6)
        lines = sub.split("|")
        for i, line in enumerate(lines):
            c.drawCentredString(x + w / 2, y + h - (11 + i * 4) * mm, line)

    def arrow(self, c, x1, y, x2):
        c.setStrokeColor(MUTED)
        c.setFillColor(MUTED)
        c.setLineWidth(1.2)
        c.line(x1, y, x2, y)
        c.line(x2, y, x2 - 2.2 * mm, y + 1.5 * mm)
        c.line(x2, y, x2 - 2.2 * mm, y - 1.5 * mm)

    def draw(self):
        c = self.canv
        w = 35 * mm
        h = 27 * mm
        gap = 9 * mm
        y = 41 * mm
        xs = [2 * mm + i * (w + gap) for i in range(4)]
        boxes = [
            ("FIRST ANSWERS", "1 answer|per provider", BLUE),
            ("OWN CROWDS", "3 samples|per provider", TEAL),
            ("COUNCIL VOTE", "1 position|per provider", AMBER),
            ("JEV ARBITER", "select or request|one reconsideration", NAVY),
        ]
        for i, ((title, sub, color), x) in enumerate(zip(boxes, xs)):
            self.draw_box(c, x, y, w, h, title, sub, color)
            if i < 3:
                self.arrow(c, x + w + 1 * mm, y + h / 2, xs[i + 1] - 1 * mm)
        c.setFillColor(PALE)
        c.roundRect(22 * mm, 5 * mm, 126 * mm, 23 * mm, 3 * mm, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(FONT_BOLD, 8)
        c.drawCentredString(85 * mm, 20 * mm, "CONTROL CONDITION")
        c.setFont(FONT, 7.3)
        c.drawCentredString(85 * mm, 14 * mm, "JEV answered each question alone, without council input")
        c.setFillColor(MUTED)
        c.setFont(FONT, 6.7)
        c.drawCentredString(85 * mm, 8.8 * mm, "This separates arbitration benefit from JEV's direct solving ability")


class IntervalGraphic(Flowable):
    def __init__(self, width=170 * mm, height=45 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        left = 18 * mm
        right = self.width - 18 * mm
        y = 21 * mm
        minimum, maximum = -5, 20

        def sx(v):
            return left + (v - minimum) / (maximum - minimum) * (right - left)

        c.setStrokeColor(LINE)
        c.setLineWidth(1)
        c.line(left, y, right, y)
        for v in (-5, 0, 5, 10, 15, 20):
            x = sx(v)
            c.setStrokeColor(RED if v == 0 else LINE)
            c.line(x, y - 4 * mm, x, y + 4 * mm)
            c.setFillColor(MUTED)
            c.setFont(FONT, 7)
            c.drawCentredString(x, y - 9 * mm, f"{v:+d}")
        c.setStrokeColor(BLUE)
        c.setLineWidth(5)
        c.line(sx(9.72), y, sx(16.80), y)
        c.setFillColor(NAVY)
        c.circle(sx(13.16), y, 2.3 * mm, fill=1, stroke=0)
        c.setFont(FONT_BOLD, 9)
        c.drawCentredString(sx(13.16), y + 7 * mm, "+13.16 pp")
        c.setFont(FONT, 7.3)
        c.setFillColor(MUTED)
        c.drawCentredString((sx(9.72) + sx(16.80)) / 2, y + 12 * mm, "95% bootstrap interval: +9.72 to +16.80 pp")
        c.setFillColor(RED)
        c.setFont(FONT, 6.8)
        c.drawCentredString(sx(0), y + 7 * mm, "no difference")


class ProviderBars(Flowable):
    def __init__(self, width=170 * mm, height=65 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        data = [
            ("OpenAI", 62.55, 63.56),
            ("Anthropic", 65.59, 65.99),
            ("Mistral", 60.12, 60.53),
        ]
        left = 37 * mm
        chart_w = self.width - 54 * mm
        row_h = 18 * mm
        top = self.height - 12 * mm
        for i, (name, first, crowd) in enumerate(data):
            y = top - i * row_h
            c.setFillColor(INK)
            c.setFont(FONT_BOLD, 8.5)
            c.drawRightString(left - 4 * mm, y + 1 * mm, name)
            c.setFillColor(colors.HexColor("#CDD6E1"))
            c.roundRect(left, y + 4 * mm, chart_w * first / 100, 4 * mm, 1.5 * mm, fill=1, stroke=0)
            c.setFillColor(TEAL)
            c.roundRect(left, y - 2 * mm, chart_w * crowd / 100, 4 * mm, 1.5 * mm, fill=1, stroke=0)
            c.setFillColor(INK)
            c.setFont(FONT, 7.2)
            c.drawString(left + chart_w * first / 100 + 2 * mm, y + 4.7 * mm, f"{first:.2f}%")
            c.drawString(left + chart_w * crowd / 100 + 2 * mm, y - 1.3 * mm, f"{crowd:.2f}%")
        c.setFillColor(colors.HexColor("#CDD6E1"))
        c.rect(left, 1 * mm, 5 * mm, 2.5 * mm, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.setFont(FONT, 6.8)
        c.drawString(left + 7 * mm, 1 * mm, "first sample")
        c.setFillColor(TEAL)
        c.rect(left + 34 * mm, 1 * mm, 5 * mm, 2.5 * mm, fill=1, stroke=0)
        c.setFillColor(MUTED)
        c.drawString(left + 41 * mm, 1 * mm, "own-crowd plurality")


def styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "Title", parent=base["Title"], fontName=FONT_BOLD, fontSize=28,
            leading=31, textColor=NAVY, alignment=TA_LEFT, spaceAfter=5 * mm,
        ),
        "subtitle": ParagraphStyle(
            "Subtitle", parent=base["Normal"], fontName=FONT, fontSize=13,
            leading=18, textColor=MUTED, spaceAfter=7 * mm,
        ),
        "h1": ParagraphStyle(
            "H1", parent=base["Heading1"], fontName=FONT_BOLD, fontSize=20,
            leading=24, textColor=NAVY, spaceAfter=5 * mm,
        ),
        "h2": ParagraphStyle(
            "H2", parent=base["Heading2"], fontName=FONT_BOLD, fontSize=12,
            leading=15, textColor=BLUE, spaceBefore=2 * mm, spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "Body", parent=base["BodyText"], fontName=FONT, fontSize=9.2,
            leading=13.2, textColor=INK, spaceAfter=3 * mm,
        ),
        "small": ParagraphStyle(
            "Small", parent=base["BodyText"], fontName=FONT, fontSize=7.6,
            leading=10.5, textColor=MUTED, spaceAfter=2 * mm,
        ),
        "callout": ParagraphStyle(
            "Callout", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=12,
            leading=16, textColor=NAVY, alignment=TA_CENTER,
        ),
        "number": ParagraphStyle(
            "Number", parent=base["BodyText"], fontName=FONT_BOLD, fontSize=22,
            leading=24, textColor=BLUE, alignment=TA_CENTER,
        ),
        "label": ParagraphStyle(
            "Label", parent=base["BodyText"], fontName=FONT, fontSize=7.5,
            leading=9.5, textColor=MUTED, alignment=TA_CENTER,
        ),
        "bullet": ParagraphStyle(
            "Bullet", parent=base["BodyText"], fontName=FONT, fontSize=9,
            leading=13, textColor=INK, leftIndent=5 * mm, firstLineIndent=-3 * mm,
            bulletIndent=1 * mm, spaceAfter=2 * mm,
        ),
    }


S = styles()


def P(text: str, style="body") -> Paragraph:
    return Paragraph(text, S[style])


def page_decor(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 14 * mm, A4[0] - 20 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7)
    canvas.drawString(20 * mm, 9 * mm, "JEV Crowd-to-Council Experiment | Brian Doutey")
    canvas.drawRightString(A4[0] - 20 * mm, 9 * mm, f"Page {page}")
    canvas.restoreState()


def metric_cards(items):
    cells = []
    for number, label, color in items:
        cells.append([
            Paragraph(f'<font color="{color.hexval()}">{number}</font>', S["number"]),
            Paragraph(label, S["label"]),
        ])
    table = Table([cells], colWidths=[170 * mm / len(items)])
    table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.7, LINE),
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    return table


def bullet(text):
    return P(f"- {text}", "bullet")


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(OUTPUT), pagesize=A4, rightMargin=20 * mm, leftMargin=20 * mm,
        topMargin=19 * mm, bottomMargin=19 * mm,
        title="JEV Crowd-to-Council Experiment Information Pack",
        author="Brian Doutey",
        subject="Results of a 500-question LLM crowd and JEV arbitration experiment",
    )
    story = []

    # Cover
    story += [Spacer(1, 21 * mm), P("JEV Crowd-to-Council Experiment", "title")]
    story += [P("Can a classifier-style arbiter turn multiple non-reasoning LLM outputs into a more accurate final answer?", "subtitle")]
    story += [Spacer(1, 8 * mm)]
    story += [metric_cards([
        ("500", "frozen multiple-choice questions", BLUE),
        ("3 x 3", "providers x initial samples", TEAL),
        ("494", "terminally complete questions", NAVY),
    ])]
    story += [Spacer(1, 12 * mm)]
    headline = Table([[P("Full JEV-controlled Delphi reached <font color='#2D6CDF'>80.77%</font> accuracy, improving on the provider-crowd majority by <font color='#2D6CDF'>13.16 percentage points</font>.", "callout")]], colWidths=[160 * mm])
    headline.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EAF1FF")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#B9CCF5")),
        ("LEFTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 8 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8 * mm),
    ]))
    story += [headline, Spacer(1, 13 * mm)]
    story += [P("Prepared for Brian Doutey", "h2")]
    story += [P("Independent personal research project | No institutional affiliation | No external funding or influence", "body")]
    story += [Spacer(1, 7 * mm), P("Frozen study: jev-crowd-council-delphi-2026-09-24-v5", "small")]
    story += [P("Locked analysis: 494 evaluable questions; six terminally incomplete; recorded API spend $5.6511", "small")]
    story += [PageBreak()]

    # Executive summary
    story += [P("Executive summary", "h1")]
    story += [metric_cards([
        ("+13.16 pp", "full Delphi vs provider-crowd majority", BLUE),
        ("+9.72 to +16.80", "95% bootstrap interval, percentage points", GREEN),
        ("76 / 11", "helpful / harmful answer transitions", AMBER),
    ]), Spacer(1, 7 * mm)]
    story += [P("What the experiment found", "h2")]
    story += [bullet("Repeated sampling helped modestly: the cross-model vote rose from 64.78% using first answers to 67.61% using each provider's three-sample crowd."),
              bullet("JEV selection among the initial council positions reached 73.48%, a further 5.87-point improvement over simple provider-crowd voting."),
              bullet("Allowing JEV to request one reconsideration round, then arbitrate the revised positions, reached 80.77%."),
              bullet("The primary paired improvement was positive and its frozen bootstrap interval excluded zero."),
              bullet("JEV answering alone reached 87.25%, higher than the full council pipeline. Arbitration helped the crowd, but direct JEV solving was descriptively strongest.")]
    story += [Spacer(1, 5 * mm)]
    caveat = Table([[P("Bottom line", "h2"), P("The evidence supports the narrow claim that JEV materially improved the output of this three-model council. It does not support the stronger claim that the council was the best way to use JEV, because JEV-alone performed better.", "body")]], colWidths=[31 * mm, 129 * mm])
    caveat.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF6E6")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#F1C978")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    story += [caveat, Spacer(1, 7 * mm)]
    story += [P("Scope", "h2")]
    story += [P("These results apply to this model slate, prompt, temperature, question mix, crowd size, and one-round Delphi policy. They do not establish that all LLM crowds or arbiters improve accuracy.", "body")]
    story += [PageBreak()]

    # Design
    story += [P("How the experiment worked", "h1")]
    story += [P("Each question moved through a controlled sequence designed to separate homogeneous crowds, heterogeneous voting, JEV selection, and JEV-controlled reconsideration.", "body")]
    story += [PipelineDiagram(), Spacer(1, 4 * mm)]
    design_table = Table([
        [P("Council models", "h2"), P("OpenAI gpt-4.1-mini-2025-04-14<br/>Anthropic claude-haiku-4-5-20251001<br/>Mistral ministral-14b-2512", "body")],
        [P("Initial sampling", "h2"), P("Three independent answers per provider at temperature 0.7; each provider's plurality became one council position.", "body")],
        [P("Simple comparator", "h2"), P("One equal vote per provider position. Deterministic hash ordering resolved a 1-1-1 tie.", "body")],
        [P("JEV role", "h2"), P("JEV saw anonymized candidates, rationales, evidence, and vote counts. It either stopped or requested exactly one reconsideration round.", "body")],
        [P("Blinding", "h2"), P("Models and JEV never received ground truth. JEV did not see provider identities. Interim accuracy was not displayed.", "body")],
    ], colWidths=[39 * mm, 121 * mm])
    design_table.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PALE]),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2 * mm),
    ]))
    story += [design_table, PageBreak()]

    # Condition accuracy
    story += [P("Accuracy by experimental condition", "h1")]
    story += [P("Accuracy increased at each aggregation and arbitration stage. JEV-alone is shown separately because it is a control, not a stage in the council pipeline.", "body")]
    story += [AccuracyBars([
        ("First-answer vote", 64.78, colors.HexColor("#A9B7C8")),
        ("Provider-crowd vote", 67.61, TEAL),
        ("JEV selection-only", 73.48, AMBER),
        ("Post-controller vote", 76.72, CYAN),
        ("Full JEV Delphi", 80.77, BLUE),
        ("JEV alone", 87.25, NAVY),
    ]), Spacer(1, 3 * mm)]
    story += [P("Reading the ladder", "h2")]
    story += [bullet("The provider-crowd vote is the primary non-JEV comparator."),
              bullet("Selection-only measures JEV choosing among existing initial positions without requesting revision."),
              bullet("Post-controller vote measures the revised provider positions without final JEV selection."),
              bullet("Full Delphi includes both the bounded reconsideration policy and final JEV selection.")]
    story += [PageBreak()]

    # Primary result
    story += [P("Primary result: JEV improved the council", "h1")]
    story += [P("The preregistered primary estimand was full JEV-controlled Delphi accuracy minus the cross-model majority of provider crowds, evaluated question by question.", "body")]
    story += [IntervalGraphic(), Spacer(1, 5 * mm)]
    story += [metric_cards([
        ("76", "questions changed from wrong crowd vote to correct Delphi answer", GREEN),
        ("11", "questions changed from correct crowd vote to wrong Delphi answer", RED),
        ("407", "questions unchanged by the primary comparison", NAVY),
    ]), Spacer(1, 8 * mm)]
    story += [P("Interpretation", "h2")]
    story += [P("The net gain was 65 additional correct answers among the 494 completed questions. The paired bootstrap interval stayed entirely above zero, supporting a positive effect for this frozen study configuration.", "body")]
    story += [P("This is a paired comparison: both methods answered the same questions. It therefore measures how often the JEV-controlled process repaired or damaged the council's answer, rather than comparing unrelated test sets.", "body")]
    story += [PageBreak()]

    # Decomposition
    story += [P("Where the improvement came from", "h1")]
    decomposition = Table([
        [P("Component", "h2"), P("Accuracy change", "h2"), P("Frozen 95% interval", "h2"), P("Meaning", "h2")],
        [P("Own crowds + cross-model vote", "body"), P("+2.83 pp", "body"), P("+1.21 to +4.66 pp", "body"), P("Three samples per provider modestly improved the heterogeneous vote.", "body")],
        [P("JEV selection-only", "body"), P("+5.87 pp", "body"), P("+3.04 to +8.91 pp", "body"), P("JEV extracted value by choosing among available council positions.", "body")],
        [P("Full Delphi vs crowd vote", "body"), P("+13.16 pp", "body"), P("+9.72 to +16.80 pp", "body"), P("Bounded reconsideration plus final arbitration produced the largest preregistered gain.", "body")],
    ], colWidths=[43 * mm, 28 * mm, 38 * mm, 51 * mm])
    decomposition.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story += [decomposition, Spacer(1, 8 * mm)]
    story += [metric_cards([
        ("220 / 494", "questions where JEV requested reconsideration", BLUE),
        ("222", "questions with initial provider disagreement", AMBER),
        ("382 / 494", "questions with a correct provider position available", GREEN),
    ]), Spacer(1, 7 * mm)]
    story += [P("Selection ceiling", "h2")]
    story += [P("JEV selection-only was correct on 95.03% of questions where a correct provider position existed. When every provider position was wrong, selection alone could not recover; reconsideration or JEV's own knowledge was needed.", "body")]
    story += [PageBreak()]

    # Provider results
    story += [P("What wisdom-of-crowds added within each model", "h1")]
    story += [P("Each provider produced three independent initial samples. The provider-level crowd position was the plurality label across those samples.", "body")]
    story += [ProviderBars(), Spacer(1, 6 * mm)]
    provider_table = Table([
        [P("Provider", "h2"), P("First sample", "h2"), P("Own crowd", "h2"), P("Change", "h2")],
        [P("OpenAI", "body"), P("62.55%", "body"), P("63.56%", "body"), P("+1.01 pp", "body")],
        [P("Anthropic", "body"), P("65.59%", "body"), P("65.99%", "body"), P("+0.40 pp", "body")],
        [P("Mistral", "body"), P("60.12%", "body"), P("60.53%", "body"), P("+0.40 pp", "body")],
    ], colWidths=[55 * mm, 35 * mm, 35 * mm, 35 * mm])
    provider_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
        ("ALIGN", (1, 1), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story += [provider_table, Spacer(1, 7 * mm)]
    story += [P("The within-model gains were small. The larger improvement appeared when evidence from different model families was evaluated by JEV, especially after bounded reconsideration.", "body")]
    story += [PageBreak()]

    # Caveat
    story += [P("The essential caveat: JEV alone was strongest", "h1")]
    story += [metric_cards([
        ("87.25%", "JEV answering directly", NAVY),
        ("80.77%", "full JEV-controlled Delphi", BLUE),
        ("-6.48 pp", "Delphi minus JEV-alone, descriptive", RED),
    ]), Spacer(1, 8 * mm)]
    story += [P("Why this matters", "h2")]
    story += [P("The experiment included JEV-alone precisely to avoid mistaking a strong fourth solver for a uniquely effective arbiter. JEV did improve the council's output, but direct JEV answering produced the highest observed accuracy.", "body")]
    story += [bullet("Supported: JEV added substantial value relative to simple three-provider crowd voting."),
              bullet("Not supported: the full council was more accurate than asking JEV directly."),
              bullet("Still open: whether arbitration provides benefits on domains where JEV has weaker direct knowledge, where auditability matters, or where diverse evidence is more valuable than benchmark accuracy alone.")]
    story += [Spacer(1, 6 * mm)]
    nuance = Table([[P("Do not overclaim", "h2"), P("The 6.48-point JEV-alone advantage is descriptive in the frozen report; no additional paired confidence interval was preregistered for this contrast. It is nevertheless large enough to shape the practical interpretation.", "body")]], colWidths=[35 * mm, 125 * mm])
    nuance.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FDEEEE")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#E8A1A1")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 5 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
    ]))
    story += [nuance, PageBreak()]

    # Integrity and amendments
    story += [P("Integrity, amendments, and limitations", "h1")]
    story += [P("Model replacement", "h2")]
    story += [P("The original clean-slate plan named Google gemini-2.5-flash. During synthetic, unscored preflight the API reported that the model was unavailable to new users. Mistral Large 3 was then considered but blocked by the free subscription tier. The account metadata marked ministral-14b-2512 as reasoning=false; it passed structured-output preflight and became the third provider before the scored v5 run.", "body")]
    story += [P("Aborted output-cap pilot", "h2")]
    story += [P("A v4 start was stopped after six questions because a 512-token output ceiling caused widespread structured-JSON truncation. No accuracy or aggregate outcome was inspected. That database was quarantined and excluded. The ceiling was raised uniformly to 2,048 tokens and the study restarted under freeze v5.", "body")]
    story += [P("Terminal run quality", "h2")]
    quality = Table([
        [P("Planned questions", "h2"), P("500", "body")],
        [P("Complete questions", "h2"), P("494", "body")],
        [P("Terminally incomplete", "h2"), P("6 (1.2%)", "body")],
        [P("Preregistered maximum missingness", "h2"), P("2.0%", "body")],
        [P("Failed calls including retries", "h2"), P("41", "body")],
        [P("Recorded API spend", "h2"), P("$5.6511", "body")],
    ], colWidths=[95 * mm, 65 * mm])
    quality.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story += [quality, Spacer(1, 6 * mm)]
    story += [P("Limitations", "h2")]
    story += [bullet("Provider samples are correlated model outputs, not independent human participants."),
              bullet("Public benchmark items may have appeared in model training data."),
              bullet("Results depend on one model slate, prompt, temperature, dataset mix, and one-round reconsideration policy."),
              bullet("Ministral 14B was the strongest available non-reasoning Mistral model on the accessible tier, but model capabilities were not identical."),
              bullet("Six terminally incomplete questions were excluded under the prespecified missingness rule.")]
    story += [PageBreak()]

    # Methods and sources
    story += [P("Methods and reproducibility record", "h1")]
    methods = Table([
        [P("Dataset", "h2"), P("500 public multiple-choice questions: 400 MMLU-Pro and 100 ARC-Challenge. Health and law categories excluded.", "body")],
        [P("Primary estimand", "h2"), P("Full JEV-controlled Delphi accuracy minus cross-model majority of provider crowds.", "body")],
        [P("Inference", "h2"), P("Paired question bootstrap, 10,000 draws, frozen analysis seed 20260926.", "body")],
        [P("Reasoning control", "h2"), P("No enabled hidden reasoning mode. OpenAI reasoning tokens and Anthropic thinking blocks caused call failure. Mistral metadata reported reasoning=false and no reasoning-mode parameter was sent.", "body")],
        [P("Ground-truth handling", "h2"), P("Correct labels remained local and were replaced with a dummy label in every model-facing object.", "body")],
        [P("Retry rule", "h2"), P("At most two recorded attempts for each missing stage. Successful calls were never rerun.", "body")],
    ], colWidths=[42 * mm, 118 * mm])
    methods.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PALE]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    story += [methods, Spacer(1, 7 * mm)]
    story += [P("Source artifacts", "h2")]
    story += [P("Locked analysis: results/final-analysis-v5.txt<br/>Terminal database: results/arbiter-study-v5.sqlite3<br/>Protocol and amendment history: docs/PROTOCOL.md<br/>Frozen configuration: config/study_v1.json", "body")]
    story += [P("Artifact integrity", "h2")]
    story += [P("Database SHA-256: EDC8469C9CBA1A8EDB095CA258BF721A42C7E433F308B105DF088DEAE528867E<br/>Locked analysis SHA-256: B39E476E3F03CC6BC91689B5C86B086B06B1B51F3BDEE65662EB5A2519392F05", "small")]
    story += [Spacer(1, 6 * mm)]
    story += [P("Disclosure", "h2")]
    story += [P("This was Brian Doutey's independent personal project. No person or organization paid for, commissioned, or influenced the work. The author reports no affiliation or relationship with TypeSafe and no external funding.", "body")]

    doc.build(story, onFirstPage=page_decor, onLaterPages=page_decor)
    print(OUTPUT)


if __name__ == "__main__":
    build()
