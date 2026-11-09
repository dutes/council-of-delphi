from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Flowable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "output" / "pdf" / "jev-delphi-research-results-and-hypothesis-status.pdf"

NAVY = colors.HexColor("#132238")
BLUE = colors.HexColor("#2F6FED")
TEAL = colors.HexColor("#159A9C")
GREEN = colors.HexColor("#268A55")
AMBER = colors.HexColor("#D99124")
RED = colors.HexColor("#C84C4C")
PURPLE = colors.HexColor("#6957C2")
INK = colors.HexColor("#263445")
MUTED = colors.HexColor("#647184")
PALE = colors.HexColor("#F3F6FA")
PALE_BLUE = colors.HexColor("#EAF1FF")
LINE = colors.HexColor("#D8E0EA")
WHITE = colors.white


def register_fonts() -> tuple[str, str]:
    regular = Path("C:/Windows/Fonts/aptos.ttf")
    bold = Path("C:/Windows/Fonts/aptos-bold.ttf")
    if regular.exists() and bold.exists():
        pdfmetrics.registerFont(TTFont("ResultSans", str(regular)))
        pdfmetrics.registerFont(TTFont("ResultSans-Bold", str(bold)))
        return "ResultSans", "ResultSans-Bold"
    return "Helvetica", "Helvetica-Bold"


FONT, FONT_BOLD = register_fonts()


def make_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle("title", parent=base["Title"], fontName=FONT_BOLD,
                                fontSize=28, leading=32, textColor=NAVY, alignment=TA_LEFT,
                                spaceAfter=5 * mm),
        "subtitle": ParagraphStyle("subtitle", parent=base["Normal"], fontName=FONT,
                                   fontSize=13, leading=18, textColor=MUTED, spaceAfter=5 * mm),
        "h1": ParagraphStyle("h1", parent=base["Heading1"], fontName=FONT_BOLD,
                             fontSize=19, leading=23, textColor=NAVY, spaceAfter=4 * mm),
        "h2": ParagraphStyle("h2", parent=base["Heading2"], fontName=FONT_BOLD,
                             fontSize=11.5, leading=14, textColor=BLUE,
                             spaceBefore=2 * mm, spaceAfter=2 * mm),
        "body": ParagraphStyle("body", parent=base["BodyText"], fontName=FONT,
                               fontSize=9.1, leading=12.7, textColor=INK, spaceAfter=2.5 * mm),
        "small": ParagraphStyle("small", parent=base["BodyText"], fontName=FONT,
                                fontSize=7.4, leading=9.8, textColor=MUTED, spaceAfter=1.5 * mm),
        "callout": ParagraphStyle("callout", parent=base["BodyText"], fontName=FONT_BOLD,
                                  fontSize=12, leading=16, textColor=NAVY, alignment=TA_CENTER),
        "metric": ParagraphStyle("metric", parent=base["BodyText"], fontName=FONT_BOLD,
                                 fontSize=20, leading=22, textColor=BLUE, alignment=TA_CENTER),
        "label": ParagraphStyle("label", parent=base["BodyText"], fontName=FONT,
                                fontSize=7.3, leading=9.2, textColor=MUTED, alignment=TA_CENTER),
        "bullet": ParagraphStyle("bullet", parent=base["BodyText"], fontName=FONT,
                                 fontSize=8.9, leading=12.6, textColor=INK,
                                 leftIndent=5 * mm, firstLineIndent=0,
                                 bulletIndent=1 * mm, spaceAfter=1.8 * mm),
        "status": ParagraphStyle("status", parent=base["BodyText"], fontName=FONT_BOLD,
                                 fontSize=8.4, leading=10.5, alignment=TA_CENTER),
    }


S = make_styles()


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def bullet(text: str) -> Paragraph:
    return Paragraph(text, S["bullet"], bulletText="-")


def page_decor(canvas, doc):
    canvas.saveState()
    page = canvas.getPageNumber()
    canvas.setFillColor(NAVY)
    canvas.rect(0, A4[1] - 8 * mm, A4[0], 8 * mm, fill=1, stroke=0)
    canvas.setStrokeColor(LINE)
    canvas.line(20 * mm, 14 * mm, A4[0] - 20 * mm, 14 * mm)
    canvas.setFillColor(MUTED)
    canvas.setFont(FONT, 7)
    canvas.drawString(20 * mm, 9 * mm, "JEV Delphi research programme | Brian Doutey")
    canvas.drawRightString(A4[0] - 20 * mm, 9 * mm, f"Page {page}")
    canvas.restoreState()


def metric_cards(items):
    cells = [[P(number, "metric"), P(label, "label")] for number, label in items]
    table = Table([cells], colWidths=[170 * mm / len(items)])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), PALE),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.7, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4 * mm),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    return table


def callout(title: str, text: str, background=PALE_BLUE, border=colors.HexColor("#B9CCF5")):
    table = Table([[P(title, "h2"), P(text, "body")]], colWidths=[37 * mm, 123 * mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), background),
        ("BOX", (0, 0), (-1, -1), 0.8, border),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 4 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]))
    return table


def data_table(rows, widths, header=True):
    table = Table(rows, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3 * mm),
        ("TOPPADDING", (0, 0), (-1, -1), 3 * mm),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3 * mm),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), NAVY),
                     ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                     ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE])]
    else:
        commands += [("ROWBACKGROUNDS", (0, 0), (-1, -1), [WHITE, PALE])]
    table.setStyle(TableStyle(commands))
    return table


class HorizontalBars(Flowable):
    def __init__(self, data, width=170 * mm, height=88 * mm, min_value=0, max_value=100):
        super().__init__(); self.data=data; self.width=width; self.height=height
        self.min_value=min_value; self.max_value=max_value

    def draw(self):
        c=self.canv; label_w=62*mm; chart_w=self.width-label_w-20*mm
        top=self.height-9*mm; row_h=(self.height-14*mm)/max(len(self.data),1)
        for tick in range(0,101,20):
            x=label_w+chart_w*tick/100
            c.setStrokeColor(LINE);c.setLineWidth(.4);c.line(x,4*mm,x,top+3*mm)
            c.setFillColor(MUTED);c.setFont(FONT,6.8);c.drawCentredString(x,0,str(tick))
        for i,(label,value,color) in enumerate(self.data):
            y=top-i*row_h
            c.setFillColor(INK);c.setFont(FONT,8);c.drawRightString(label_w-3*mm,y+1.5*mm,label)
            c.setFillColor(colors.HexColor("#E6EBF1"));c.roundRect(label_w,y,chart_w,5.5*mm,2*mm,fill=1,stroke=0)
            c.setFillColor(color);c.roundRect(label_w,y,chart_w*value/100,5.5*mm,2*mm,fill=1,stroke=0)
            c.setFillColor(INK);c.setFont(FONT_BOLD,7.8);c.drawString(label_w+chart_w+3*mm,y+1.4*mm,f"{value:.2f}%")


class JourneyDiagram(Flowable):
    def __init__(self, width=170*mm, height=92*mm): super().__init__();self.width=width;self.height=height
    def draw(self):
        c=self.canv; xs=[4,45,86,127]; colors_=[TEAL,AMBER,BLUE,PURPLE]
        titles=["1. CROWD", "2. REPORTS", "3. ACTIVE", "4. ABLATION"]
        subs=["Does repetition help?", "Can JEV combine\ndistributed summaries?",
              "Can classification\nroute retrieval?", "Is JEV uniquely\nnecessary?"]
        for i,xmm in enumerate(xs):
            x=xmm*mm; y=43*mm; w=35*mm; h=33*mm
            c.setFillColor(colors_[i]);c.roundRect(x,y,w,h,3*mm,fill=1,stroke=0)
            c.setFillColor(WHITE);c.setFont(FONT_BOLD,8);c.drawCentredString(x+w/2,y+h-7*mm,titles[i])
            c.setFont(FONT,6.7)
            for j,line in enumerate(subs[i].split("\n")):c.drawCentredString(x+w/2,y+h-(14+j*5)*mm,line)
            if i<3:
                c.setStrokeColor(MUTED);c.setFillColor(MUTED);c.line(x+w+1*mm,y+h/2,(xs[i+1]-1)*mm,y+h/2)
                c.line((xs[i+1]-1)*mm,y+h/2,(xs[i+1]-3)*mm,y+h/2+1.5*mm)
                c.line((xs[i+1]-1)*mm,y+h/2,(xs[i+1]-3)*mm,y+h/2-1.5*mm)
        c.setFillColor(PALE);c.roundRect(10*mm,7*mm,150*mm,23*mm,3*mm,fill=1,stroke=0)
        c.setFillColor(NAVY);c.setFont(FONT_BOLD,8.5);c.drawCentredString(85*mm,21*mm,"EVIDENCE ACCUMULATED ACROSS FOUR SEPARATE CONFIRMATORY STUDIES")
        c.setFillColor(MUTED);c.setFont(FONT,7);c.drawCentredString(85*mm,14*mm,"Each later experiment addressed a limitation revealed by the previous one")


class ActiveFlow(Flowable):
    def __init__(self,width=170*mm,height=72*mm):super().__init__();self.width=width;self.height=height
    def draw(self):
        c=self.canv; box_w=31*mm; gap=10*mm; y=37*mm; h=24*mm
        boxes=[("TARGET", "artifact" ,TEAL),("RETRIEVE", "matching fact",BLUE),("JEV", "classify action",PURPLE),("CONTROLLER", "advance or stop",NAVY)]
        for i,(title,sub,color) in enumerate(boxes):
            x=4*mm+i*(box_w+gap);c.setFillColor(color);c.roundRect(x,y,box_w,h,3*mm,fill=1,stroke=0)
            c.setFillColor(WHITE);c.setFont(FONT_BOLD,7.8);c.drawCentredString(x+box_w/2,y+16*mm,title)
            c.setFont(FONT,6.8);c.drawCentredString(x+box_w/2,y+9*mm,sub)
            if i<3:
                c.setStrokeColor(MUTED);c.line(x+box_w+1*mm,y+h/2,x+box_w+gap-1*mm,y+h/2)
        c.setFillColor(PALE_BLUE);c.roundRect(16*mm,4*mm,138*mm,23*mm,3*mm,fill=1,stroke=0)
        c.setFillColor(INK);c.setFont(FONT_BOLD,8);c.drawCentredString(85*mm,18*mm,"JEV never wrote a question or generated the final answer")
        c.setFont(FONT,7);c.drawCentredString(85*mm,11*mm,"It chose a closed-set action; deterministic code issued the next fixed retrieval request")


def build():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc=SimpleDocTemplate(str(OUTPUT),pagesize=A4,leftMargin=20*mm,rightMargin=20*mm,
                          topMargin=19*mm,bottomMargin=19*mm,
                          title="JEV Delphi Research: Results and Hypothesis Status",
                          author="Brian Doutey",
                          subject="Results from four studies of LLM crowds, JEV arbitration, and active evidence retrieval")
    story=[]

    # 1 Cover
    story += [Spacer(1,18*mm),P("JEV Delphi Research", "title"),
              P("What we expected, what the experiments found, and the current status of the hypothesis", "subtitle"),
              Spacer(1,7*mm),metric_cards([
                  ("4", "confirmatory studies"),("1,394", "evaluable question cases"),("$8.64", "recorded confirmatory API spend")]),
              Spacer(1,12*mm)]
    headline=Table([[P("The central idea survived, but in a narrower form: active semantic arbitration can recover distributed evidence; JEV performed perfectly in that role, but was not uniquely better than another capable classifier.","callout")]],colWidths=[160*mm])
    headline.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),PALE_BLUE),("BOX",(0,0),(-1,-1),1,colors.HexColor("#B9CCF5")),("LEFTPADDING",(0,0),(-1,-1),8*mm),("RIGHTPADDING",(0,0),(-1,-1),8*mm),("TOPPADDING",(0,0),(-1,-1),8*mm),("BOTTOMPADDING",(0,0),(-1,-1),8*mm)]))
    story += [headline,Spacer(1,13*mm),P("Prepared for Brian Doutey","h2"),
              P("Independent personal research project | No institutional affiliation | No external funding or influence","body"),
              Spacer(1,6*mm),P("Report date: 25 September 2026","small"),
              P("This report distinguishes confirmatory results from engineering pilots and preserves the limitations of each design.","small"),PageBreak()]

    # 2 Executive status
    story += [P("Executive conclusion", "h1"),metric_cards([
        ("+13.16 pp","JEV Delphi improvement over council vote"),("300 / 300","active evidence paths correct"),("0.00 pp","JEV advantage over OpenAI classifier")]),Spacer(1,6*mm),
        callout("Current status","Partly supported. The architecture works under the tested conditions, but neither a large automatic wisdom-of-crowds effect nor a unique accuracy advantage for JEV has been demonstrated."),Spacer(1,6*mm),
        P("What is supported", "h2"),
        bullet("Repeated sampling and voting produced a small positive improvement on conventional benchmark questions."),
        bullet("JEV materially improved a heterogeneous three-model council and used reconsideration to repair more answers than it damaged."),
        bullet("One-round summaries can destroy indispensable distributed evidence before an arbiter sees it."),
        bullet("An iterative, classifier-led retrieval process can recover a complete evidence chain and match the full-information ceiling on the synthetic task."),
        bullet("Semantic classification handled scope-aware conflicting evidence far better than tied voting or the tested keyword rule."),
        P("What is not supported", "h2"),
        bullet("The council did not beat JEV answering conventional benchmark questions directly."),
        bullet("JEV was not more accurate than a capable non-reasoning OpenAI model used as the same closed-set classifier."),
        bullet("The studies do not yet establish performance on uncontrolled real documents, adversarial provenance, or open-ended evidence collection."),PageBreak()]

    # 3 Journey
    story += [P("How the research question evolved", "h1"),
              P("The original idea was that LLMs might obtain a wisdom-of-crowds benefit from repeated independent answers, then gain more from a heterogeneous council, with JEV acting as a Delphi arbiter. Each study tested a progressively narrower failure point.","body"),
              JourneyDiagram(),Spacer(1,5*mm)]
    journey_rows=[
        [P("Stage","h2"),P("Expectation","h2"),P("Observed result","h2")],
        [P("Crowd and council","body"),P("Repeated and diverse answers should raise accuracy; JEV should select and coordinate the best answer.","body"),P("Crowds helped slightly. JEV helped substantially, but JEV alone was strongest.","body")],
        [P("One-round distributed evidence","body"),P("JEV should synthesize facts distributed across specialist reports.","body"),P("Failed: specialists omitted indispensable facts, so no complete proof reached JEV.","body")],
        [P("Active classifier-led retrieval","body"),P("Targeted rounds should preserve and assemble the missing evidence without making JEV a reasoning agent.","body"),P("Succeeded: 300/300 correct paths, equal to all raw evidence.","body")],
        [P("Conflicting-evidence ablation","body"),P("JEV should outperform voting and rules; possibly another classifier too.","body"),P("JEV beat voting and the keyword rule, but tied the OpenAI classifier at 100%.","body")],
    ]
    story += [data_table(journey_rows,[38*mm,59*mm,63*mm]),PageBreak()]

    # 4 Study 1
    story += [P("Study 1: crowds, councils, and JEV arbitration", "h1"),
              P("A frozen 500-question public benchmark compared first answers, within-provider crowds, a cross-provider vote, JEV selection, one bounded reconsideration round, and JEV answering alone. Six questions were terminally incomplete, leaving 494 evaluable.","body"),
              HorizontalBars([
                  ("First-answer vote",64.78,colors.HexColor("#A9B7C8")),("Provider-crowd vote",67.61,TEAL),
                  ("JEV selection-only",73.48,AMBER),("Full JEV Delphi",80.77,BLUE),("JEV alone",87.25,NAVY)
              ],height=70*mm),Spacer(1,3*mm),
              metric_cards([("+2.83 pp","crowd vote vs first answers"),("+13.16 pp","full Delphi vs crowd vote"),("76 / 11","helpful / harmful transitions")]),Spacer(1,6*mm),
              callout("Interpretation","The first hypothesis received limited support: ordinary crowd effects were small. JEV clearly improved the council, with a frozen 95% interval of +9.72 to +16.80 points, but direct JEV answering remained 6.48 points higher than the full pipeline.",colors.HexColor("#FFF6E6"),colors.HexColor("#EBCB8A")),Spacer(1,5*mm),
              P("Provider-level first-answer to own-crowd gains were +1.01 points for OpenAI and +0.40 points each for Anthropic and Mistral. The larger gain came from arbitration and reconsideration, not repeated sampling alone.","body"),PageBreak()]

    # 5 Study 2
    story += [P("Study 2: why one-round specialist reports failed", "h1"),
              P("Each of three providers received one indispensable link in a novel artifact-to-vault-to-sector-to-clearance chain, plus distractors. JEV could not know the invented relationships from training data.","body"),
              HorizontalBars([
                  ("JEV question-only",26.00,colors.HexColor("#A9B7C8")),("Specialist vote",25.67,AMBER),
                  ("JEV report synthesis",12.67,RED),("JEV all raw evidence",100.00,NAVY)
              ],height=68*mm),Spacer(1,5*mm),
              metric_cards([("0 / 300","reports containing all three links"),("44.11%","specialist own-support recall"),("100%","raw-evidence answer accuracy")]),Spacer(1,6*mm),
              callout("What failed","JEV did not fail to combine evidence that it received. The information pipeline failed earlier: specialists discarded facts they could not recognize as globally relevant. An arbiter cannot reconstruct evidence that never reaches it.",colors.HexColor("#FDEEEE"),colors.HexColor("#E5A4A4")),Spacer(1,5*mm),
              P("Design cautions discovered after the locked analysis: proof-link position was confounded with provider identity, so provider-specific recall cannot be interpreted as model ability. The three citation choices were also independent, making complete-proof citation a limited audit metric. These issues motivated rotated ownership and joint, staged selections in the next study.","small"),PageBreak()]

    # 6 Active
    story += [P("Study 3: active classifier-led Delphi retrieval", "h1"),
              P("JEV remained a classifier. A deterministic controller issued fixed targeted requests, while JEV selected one action from a closed menu: accept a named evidence item, retry, or halt unresolved.","body"),
              ActiveFlow(),Spacer(1,4*mm),
              HorizontalBars([
                  ("Question-only JEV",26.33,colors.HexColor("#A9B7C8")),("Specialist vote",20.67,AMBER),
                  ("One-round synthesis",17.33,RED),("Active classified retrieval",100.00,BLUE),
                  ("All raw evidence",100.00,NAVY)
              ],height=78*mm),Spacer(1,4*mm),
              callout("Result","Active retrieval improved by 82.67 points over one-round synthesis, with a frozen 95% interval of +78.33 to +86.67 points. Every accepted three-link path exactly matched the true support path."),Spacer(1,4*mm),
              P("This established that an iterative architecture can solve the information-loss problem on the synthetic task. It did not yet establish that JEV caused the success, because conflict-free targeted retrieval made classification easy.","body"),PageBreak()]

    # 7 Ablation
    story += [P("Study 4: is the benefit specific to JEV?", "h1"),
              P("All arbiters saw the same 900 scope-aware conflict decisions. Correct selection required interpreting chronology, negation, authority, directness, corroboration, or final correction status. Specialist retrieval variability was removed to isolate arbitration.","body"),
              HorizontalBars([
                  ("Tied-vote hash",32.56,colors.HexColor("#A9B7C8")),("Keyword rule",20.00,RED),
                  ("OpenAI classifier",100.00,TEAL),("JEV classifier",100.00,PURPLE)
              ],height=68*mm),Spacer(1,4*mm),
              data_table([
                  [P("Arbiter","h2"),P("Stage choices","h2"),P("Complete paths","h2")],
                  [P("Tied-vote hash","body"),P("293 / 900","body"),P("6 / 300","body")],
                  [P("Keyword rule","body"),P("180 / 900","body"),P("0 / 300","body")],
                  [P("OpenAI classifier","body"),P("900 / 900","body"),P("300 / 300","body")],
                  [P("JEV classifier","body"),P("900 / 900","body"),P("300 / 300","body")],
              ],[60*mm,50*mm,50*mm]),Spacer(1,6*mm),
              callout("Attribution result","JEV outperformed the tested vote and keyword baselines, but its paired difference from the OpenAI classifier was 0.00 points with a 0.00 to 0.00 interval. The preregistered descriptive 3-point equivalence criterion was met.",colors.HexColor("#F0EDFF"),colors.HexColor("#C8BFF0")),Spacer(1,4*mm),
              P("This supports semantic classification, not JEV exclusivity. It does not prove that every deterministic system would fail; only the frozen keyword and tied-vote baselines were tested.","small"),PageBreak()]

    # 8 Status matrix
    story += [P("Status of the hypothesis", "h1"),
              P("The original hypothesis contained several separable claims. Treating it as one yes-or-no proposition would hide what succeeded and what did not.","body")]
    status_rows=[
        [P("Claim","h2"),P("Status","h2"),P("Evidence","h2")],
        [P("Repeated LLM answers create a useful wisdom-of-crowds gain.","body"),P("LIMITED SUPPORT","status"),P("The heterogeneous vote improved by 2.83 points; within-model gains were only 0.40 to 1.01 points.","body")],
        [P("JEV can improve a heterogeneous council as arbiter.","body"),P("SUPPORTED","status"),P("Full Delphi improved 13.16 points over provider-crowd voting.","body")],
        [P("The JEV-controlled council is better than JEV alone.","body"),P("NOT SUPPORTED","status"),P("JEV alone scored 87.25%; full Delphi scored 80.77%.","body")],
        [P("One-round reports preserve enough distributed evidence.","body"),P("REJECTED HERE","status"),P("No report set preserved all three links; synthesis fell to 12.67%.","body")],
        [P("Active classifier-led retrieval can recover distributed evidence.","body"),P("SUPPORTED SYNTHETICALLY","status"),P("300/300 complete correct paths, matching the all-evidence ceiling.","body")],
        [P("JEV is uniquely more accurate than another capable classifier.","body"),P("NOT SUPPORTED","status"),P("JEV and OpenAI both selected 900/900 conflict packets.","body")],
        [P("The method generalizes to real uncontrolled evidence.","body"),P("OPEN","status"),P("All distributed-evidence studies used synthetic, structured facts and explicit policies.","body")],
    ]
    table=data_table(status_rows,[64*mm,38*mm,58*mm]);table.setStyle(TableStyle([
        ("TEXTCOLOR",(1,1),(1,1),AMBER),("TEXTCOLOR",(1,2),(1,2),GREEN),
        ("TEXTCOLOR",(1,3),(1,4),RED),("TEXTCOLOR",(1,5),(1,5),GREEN),
        ("TEXTCOLOR",(1,6),(1,6),RED),("TEXTCOLOR",(1,7),(1,7),BLUE)]))
    story += [table,Spacer(1,6*mm),
              callout("Best current formulation","JEV is a strong and operationally suitable closed-set arbiter, but the evidence supports classifier-led Delphi architecture more strongly than it supports a unique JEV accuracy advantage."),PageBreak()]

    # 9 Expectations vs outcomes and remaining
    story += [P("What we expected versus what we learned", "h1")]
    comparison=[
        [P("Expected before testing","h2"),P("What the evidence now says","h2")],
        [P("More samples should create a substantial crowd advantage.","body"),P("The advantage was real but small. Model-output correlation limits the classic independence assumption behind wisdom of crowds.","body")],
        [P("A heterogeneous council should provide diverse useful knowledge.","body"),P("Diversity created opportunities for JEV selection, but it did not outperform JEV's own benchmark knowledge.","body")],
        [P("JEV should identify good answers and determine consensus.","body"),P("JEV selected well and controlled reconsideration effectively. Under explicit conflict, another capable classifier was equally accurate.","body")],
        [P("Independent summaries should allow later synthesis.","body"),P("False in the partitioned task: local summarization removed globally necessary evidence.","body")],
        [P("An active Delphi process might repair missing information.","body"),P("Strongly supported on the synthetic chain task when a controller asked targeted questions and JEV classified actions.","body")],
    ]
    story += [data_table(comparison,[80*mm,80*mm]),Spacer(1,7*mm),P("What remains genuinely open","h2"),
              bullet("Whether JEV has cost, latency, calibration, consistency, or auditability advantages over general-purpose classifiers."),
              bullet("Whether active arbitration survives ambiguous, incomplete, adversarial, or forged real-world evidence."),
              bullet("Whether multiple specialists contribute value once the controller, retrieval method, and arbiter are compared with a single-model retrieval system."),
              bullet("Whether iterative retrieval improves real decisions where there is no clean answer key or explicit provenance policy."),
              Spacer(1,4*mm),callout("Next phase","Move from synthetic accuracy to external validity and operational metrics. The next useful comparison is not another easy accuracy benchmark; it is a blinded real-document study measuring answer quality, evidence coverage, cost, latency, calibration, and audit trail quality.",colors.HexColor("#FFF6E6"),colors.HexColor("#EBCB8A")),PageBreak()]

    # 10 integrity
    story += [P("Methods, integrity, and disclosure", "h1"),
              P("Confirmatory record","h2")]
    record=[
        [P("Study","h2"),P("Evaluable","h2"),P("Recorded spend","h2"),P("Primary role","h2")],
        [P("Crowd-to-council v5","body"),P("494 / 500","body"),P("$5.6511","body"),P("Benchmark crowd and arbitration accuracy","body")],
        [P("Partitioned evidence v1","body"),P("300 / 300","body"),P("$0.6352","body"),P("One-round information preservation","body")],
        [P("Active Delphi v1","body"),P("300 / 300","body"),P("$2.0328","body"),P("Iterative evidence recovery","body")],
        [P("Conflict ablation v1","body"),P("300 / 300","body"),P("$0.3207","body"),P("Arbiter attribution under conflict","body")],
    ]
    story += [data_table(record,[51*mm,31*mm,31*mm,47*mm]),Spacer(1,6*mm),
              P("Research safeguards","h2"),
              bullet("Protocols, datasets, prompts, analysis code, and implementation hashes were frozen before confirmatory calls."),
              bullet("Ground truth and support flags stayed local and were removed from model-facing objects."),
              bullet("Interim accuracy was not displayed. Successful calls were reused rather than rerun."),
              bullet("Engineering pilots were excluded from confirmatory inference. A pilot ceiling caused redesign before confirmation."),
              bullet("The active-pilot ownership gate contained an impossible threshold; the unchanged failure and a dated correction note were preserved transparently."),
              P("Source artifacts","h2"),
              P("Study 1: results/final-analysis-v5.txt<br/>Study 2: results/evidence-final-analysis-v1.txt<br/>Study 3: results/active-delphi-confirmatory-analysis-v1.txt<br/>Study 4: results/conflict-ablation-confirmatory-analysis-v1.txt<br/>Protocols: docs/PROTOCOL.md, docs/EVIDENCE_PROTOCOL.md, docs/ACTIVE_DELPHI_CONFIRMATORY_PROTOCOL.md, docs/CONFLICT_ABLATION_CONFIRMATORY_PROTOCOL.md","small"),
              PageBreak(),P("Disclosure and final assessment","h1"),P("Disclosure","h2"),
              P("This is Brian Doutey's independent personal project. No person or organization paid for, commissioned, or influenced the work. The author reports no institutional affiliation, no relationship with TypeSafe, and no external funding.","body"),
              Spacer(1,5*mm),P("Final conclusion","h2"),
              callout("Hypothesis verdict","PARTLY SUPPORTED. Active, semantically classified evidence collection can be extremely effective when knowledge is distributed. Ordinary crowds and one-shot summaries were insufficient, and JEV's accuracy advantage over another capable classifier was not demonstrated."),
              Spacer(1,7*mm),P("The most defensible claim","h2"),
              P("The programme did not validate the strongest original claim. It produced a more precise one: an iterative controller can use closed-set semantic classification to preserve, route, and assemble distributed evidence. JEV is a successful implementation of that arbiter role, but uniqueness remains unproven.","body"),
              P("Practical interpretation","h2"),
              bullet("Use JEV arbitration when a closed-set, auditable classifier interface is operationally valuable."),
              bullet("Do not assume multiple LLM answers automatically create a large wisdom-of-crowds benefit."),
              bullet("Do not compress distributed evidence into one-shot summaries before the arbiter knows what will matter."),
              bullet("Evaluate JEV against other classifiers on cost, latency, calibration, consistency, and real-document evidence quality, not only synthetic accuracy."),
              Spacer(1,8*mm),P("End of report","small")]

    doc.build(story,onFirstPage=page_decor,onLaterPages=page_decor)
    print(OUTPUT)


if __name__ == "__main__":
    build()
