"""
Generate Official Academic Progress Report & Project Documentation PDF
Deliverable: CPE100L A6 Group 1 - Sept 23 Progress Report
"""

import os
import sys
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """Canvas with two-pass page numbering and professional running headers/footers."""
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            super(NumberedCanvas, self).showPage()
        super(NumberedCanvas, self).save()

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (Pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "CPE100L (Section A6) | Group 1 - Progress Report & Project Documentation")
            self.drawRightString(612 - 54, 750, "SiteSafety Tracker (Sept 23 Deliverable)")
            self.setStrokeColor(colors.HexColor("#cbd5e1"))
            self.setLineWidth(0.75)
            self.line(54, 744, 612 - 54, 744)

        # Footer (All Pages)
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.75)
        self.line(54, 45, 612 - 54, 45)
        self.drawString(54, 32, "SiteSafety Tracker - Academic Progress Report (Sept 23, 2026)")
        page_text = f"Page {self._pageNumber} of {page_count}"
        self.drawRightString(612 - 54, 32, page_text)
        self.restoreState()


def build_pdf(output_filename):
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()

    # Custom typography & styles
    c_primary = colors.HexColor("#0f172a")     # Slate 900
    c_accent = colors.HexColor("#1e40af")      # Blue 800
    c_amber = colors.HexColor("#b45309")       # Amber 700
    c_text = colors.HexColor("#1e293b")        # Slate 800
    c_muted = colors.HexColor("#475569")       # Slate 600
    c_border = colors.HexColor("#cbd5e1")      # Slate 300
    c_bg_table = colors.HexColor("#f8fafc")    # Slate 50
    c_header_bg = colors.HexColor("#1e293b")   # Slate 800

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=c_primary,
        alignment=0,
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=c_accent,
        alignment=0,
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=c_accent,
        spaceBefore=12,
        spaceAfter=6,
        keepWithNext=True
    )

    h2_style = ParagraphStyle(
        'H2',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=c_primary,
        spaceBefore=8,
        spaceAfter=4,
        keepWithNext=True
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_text,
        spaceAfter=6
    )

    body_bold = ParagraphStyle(
        'BodyBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=c_text
    )

    bullet_style = ParagraphStyle(
        'Bullet',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=c_text,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    code_style = ParagraphStyle(
        'CodeSnippet',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10.5,
        textColor=colors.HexColor("#0f172a"),
        backColor=colors.HexColor("#f1f5f9"),
        borderColor=colors.HexColor("#cbd5e1"),
        borderWidth=0.5,
        borderPadding=5,
        spaceAfter=6
    )

    table_text = ParagraphStyle(
        'TableText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=11,
        textColor=c_text
    )

    table_header = ParagraphStyle(
        'TableHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.white
    )

    story = []

    # ── HEADER & TITLE ──────────────────────────────────────────
    story.append(Paragraph("SiteSafety Tracker: Workplace Incident & Safety Management Platform", title_style))
    story.append(Paragraph("Progress Report & Draft Technical Documentation — Deliverable Milestone (Sept 23, 2026)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_accent, spaceBefore=0, spaceAfter=10))

    # Meta Info Card Table
    meta_data = [
        [Paragraph("<b>Course & Section:</b>", body_style), Paragraph("CPE100L — Section A6", body_style),
         Paragraph("<b>Submission Date:</b>", body_style), Paragraph("September 23, 2026", body_style)],
        [Paragraph("<b>Group Number:</b>", body_style), Paragraph("Group 1", body_style),
         Paragraph("<b>Application Type:</b>", body_style), Paragraph("Web UI & Python RESTful API", body_style)],
        [Paragraph("<b>Project Lead:</b>", body_style), Paragraph("Andrei Santos (Lead Full-Stack)", body_style),
         Paragraph("<b>Repository:</b>", body_style), Paragraph("GitHub (SiteSafety-Tracker)", body_style)]
    ]
    meta_table = Table(meta_data, colWidths=[100, 150, 100, 154])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 0.75, c_border),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # ── SECTION 1: PROJECT OVERVIEW ─────────────────────────────
    story.append(Paragraph("1. Project Overview", h1_style))
    story.append(Paragraph(
        "<b>1.1 Problem Statement:</b> Construction jobsites and industrial workspaces operate under high-risk conditions where physical safety hazards, scaffolding defects, equipment failure, and environmental dangers present severe risks to human life. Traditional safety reporting relies heavily on manual paper inspection sheets or disconnected verbal notifications, resulting in delayed corrective actions, lack of accountability, and zero real-time visibility for safety administrators.",
        body_style
    ))
    story.append(Paragraph(
        "<b>1.2 Project Solution:</b> <i>SiteSafety Tracker</i> is a full-stack Python and Web-based safety incident management system. It provides on-site field staff with an intuitive hazard ticket reporting interface (complete with image attachments, priority categorization, and location tagging) while empowering managers with live incident investigation boards, inspection scheduling engines, and automated audit logging.",
        body_style
    ))
    story.append(Paragraph(
        "<b>1.3 Target Users:</b><br/>"
        "• <b>Field Personnel / Safety Officers (Staff Role):</b> Submit real-time hazard reports, monitor personal report histories, and review active safety bulletins.<br/>"
        "• <b>Safety Directors / Project Managers (Manager Role):</b> Review pending incident tickets, conduct root cause assessments, resolve tickets, schedule safety audits, and export incident compliance CSV datasets.",
        body_style
    ))

    # Role Distribution Table
    story.append(Paragraph("<b>1.4 Team Member Role Distribution (Group 1):</b>", h2_style))
    roles_data = [
        [Paragraph("Team Member", table_header), Paragraph("Assigned Role", table_header), Paragraph("Deliverable Responsibilities", table_header)],
        [Paragraph("Andrei Santos", table_text), Paragraph("Project Lead & Backend Architecture", table_text), Paragraph("Flask REST API, SQLite database integration, session management, and domain models.", table_text)],
        [Paragraph("Group 1 Member 2", table_text), Paragraph("Frontend UI & Interaction Developer", table_text), Paragraph("HTML5 layout hierarchy, Vanilla CSS design tokens, responsive views, modal dialogs.", table_text)],
        [Paragraph("Group 1 Member 3", table_text), Paragraph("Database & Business Logic Engineer", table_text), Paragraph("Schema normalization, SQL triggers, seed data scripts, and CSV export functionality.", table_text)],
        [Paragraph("Group 1 Member 4", table_text), Paragraph("QA, Security & Documentation Specialist", table_text), Paragraph("Input validation, bcrypt password hashing, session audit logging, and documentation.", table_text)]
    ]
    roles_table = Table(roles_data, colWidths=[110, 150, 244])
    roles_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_header_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_table]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(roles_table)
    story.append(Spacer(1, 10))

    # ── SECTION 2: SYLLABUS TOPIC CHECKLIST & IMPLEMENTATION ────
    story.append(Paragraph("2. Syllabus Topic Checklist & Implementation Strategy", h1_style))
    story.append(Paragraph(
        "The project has been engineered to strictly address all required computational concepts outlined in the CPE100L curriculum:",
        body_style
    ))

    checklist_data = [
        [Paragraph("Syllabus Requirement", table_header), Paragraph("Status", table_header), Paragraph("Concrete Code Implementation Strategy", table_header)],
        [
            Paragraph("<b>Classes & Objects</b><br/>(Required)", table_text),
            Paragraph("<font color='#15803d'><b>IMPLEMENTED</b></font>", table_text),
            Paragraph("Defined core domain classes (<code>User</code>, <code>HazardReport</code>, <code>Inspection</code>, <code>NotificationAlert</code>) in <code>server/models.py</code> featuring parameterized <code>__init__</code> constructors, instance methods, and dictionary serialization.", table_text)
        ],
        [
            Paragraph("<b>Data Structures</b><br/>(Required)", table_text),
            Paragraph("<font color='#15803d'><b>IMPLEMENTED</b></font>", table_text),
            Paragraph("Utilizes standard Python structures: <b>Lists</b> for queued records and batch iterations; <b>Dictionaries</b> for JSON payloads and user sessions; <b>Tuples</b> for SQLite parameterized queries; <b>Sets</b> for distinct category filtering.", table_text)
        ],
        [
            Paragraph("<b>Data Storage Strategy</b><br/>(Required)", table_text),
            Paragraph("<font color='#15803d'><b>IMPLEMENTED</b></font>", table_text),
            Paragraph("Relational <b>SQLite database</b> (<code>sitesafety.db</code>) with 7 relational tables, persistent file writes, transaction safety, and dynamic <b>CSV data export</b> (<code>SiteSafety_Resolved_Hazards.csv</code>).", table_text)
        ],
        [
            Paragraph("<b>Error & Exception Handling</b><br/>(Required)", table_text),
            Paragraph("<font color='#15803d'><b>IMPLEMENTED</b></font>", table_text),
            Paragraph("Robust <code>try-except</code> blocks wrapped around all database queries, authentication validations, file I/O operations, and HTTP endpoints returning structured JSON error codes (400, 401, 404, 500).", table_text)
        ],
        [
            Paragraph("<b>User Interface Framework</b><br/>(Required)", table_text),
            Paragraph("<font color='#15803d'><b>IMPLEMENTED</b></font>", table_text),
            Paragraph("Full-featured Web UI powered by HTML5, Vanilla CSS Design System, and asynchronous JavaScript (Fetch API) interacting seamlessly with Python's Flask backend server.", table_text)
        ],
        [
            Paragraph("<b>Inheritance & Abstraction</b><br/>(Deferred / Optional)", table_text),
            Paragraph("<font color='#b45309'><b>DEFERRED</b></font>", table_text),
            Paragraph("Flat domain model architecture with public attributes and encapsulated serialization methods in accordance with milestone guidelines.", table_text)
        ]
    ]
    check_table = Table(checklist_data, colWidths=[120, 80, 304])
    check_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_header_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_table]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(check_table)
    story.append(Spacer(1, 10))

    # ── SECTION 3: SYSTEM ARCHITECTURE & DATA DESIGN ─────────────
    story.append(Paragraph("3. System Architecture & Data File Design", h1_style))
    story.append(Paragraph("<b>3.1 Object-Oriented Domain Model (UML Architecture):</b>", h2_style))
    story.append(Paragraph(
        "Below is the UML Class representation of the core Python domain models defined in <code>server/models.py</code>:",
        body_style
    ))

    uml_snippet = """+-----------------------------------------------------------------------------------+
|                                      User                                         |
+-----------------------------------------------------------------------------------+
| - id: Optional[int]                                                               |
| - username: str                                                                   |
| - email: str                                                                      |
| - role: str  ('staff' | 'manager')                                                |
| - company: str                                                                    |
| - signup_time: str                                                                |
+-----------------------------------------------------------------------------------+
| + __init__(username, email, role, company, user_id, ...)                          |
| + is_manager() -> bool                                                            |
| + is_staff() -> bool                                                              |
| + to_dict() -> Dict[str, Any]                                                     |
| + hash_password(plain_password: str) -> str  [static]                              |
| + verify_password(plain_password: str, hashed_pw: str) -> bool  [static]          |
+-----------------------------------------------------------------------------------+

+-----------------------------------------------------------------------------------+
|                                  HazardReport                                     |
+-----------------------------------------------------------------------------------+
| - ticket: str  (e.g., 'ABC-2026-0923-42')                                         |
| - location: str                                                                   |
| - category: str                                                                   |
| - urgency: str ('Low' | 'Medium' | 'High' | 'Critical')                            |
| - status: str  ('Pending' | 'Resolved')                                           |
| - cause: str                                                                      |
| - photo: str  (Base64 data URL)                                                   |
| - reporter: Dict[str, str]                                                        |
| - resolved_date: Optional[str]                                                    |
+-----------------------------------------------------------------------------------+
| + __init__(ticket, location, category, date, time, urgency, status, ...)          |
| + mark_resolved(resolution_date: Optional[str]) -> None                           |
| + is_resolved() -> bool                                                           |
| + to_dict() -> Dict[str, Any]                                                     |
+-----------------------------------------------------------------------------------+"""
    story.append(Paragraph(f"<pre>{uml_snippet}</pre>", code_style))

    story.append(Paragraph("<b>3.2 Database Schema Layout (SQLite - sitesafety.db):</b>", h2_style))
    schema_data = [
        [Paragraph("Table Name", table_header), Paragraph("Primary Columns & Data Types", table_header), Paragraph("Purpose & Constraints", table_header)],
        [
            Paragraph("<b>users</b>", table_text),
            Paragraph("id (INT PK), username (TEXT), email (TEXT UNIQUE), password (TEXT), role (TEXT), company (TEXT), signup_time (TEXT)", table_text),
            Paragraph("Stores user profiles with bcrypt hashed passwords and role constraints ('staff' / 'manager').", table_text)
        ],
        [
            Paragraph("<b>hazards</b>", table_text),
            Paragraph("id (INT PK), ticket (TEXT UNIQUE), location (TEXT), category (TEXT), urgency (TEXT), status (TEXT), cause (TEXT), photo (TEXT), reporter_name (TEXT), resolved_date (TEXT)", table_text),
            Paragraph("Stores workplace hazard incident reports, photographic evidence, and lifecycle resolution status.", table_text)
        ],
        [
            Paragraph("<b>inspections</b>", table_text),
            Paragraph("id (INT PK), title (TEXT), location (TEXT), inspector (TEXT), date (TEXT), time (TEXT), status (TEXT)", table_text),
            Paragraph("Tracks site audit schedules and certified inspector assignments.", table_text)
        ],
        [
            Paragraph("<b>login_logs</b>", table_text),
            Paragraph("id (INT PK), user_id (INT FK), username (TEXT), action (TEXT), status (TEXT), timestamp (TEXT), ip_address (TEXT)", table_text),
            Paragraph("Maintains security audit trails for logins, signups, and logouts.", table_text)
        ],
        [
            Paragraph("<b>notifications</b>", table_text),
            Paragraph("id (INT PK), title (TEXT), time_label (TEXT), unread (INT), user_id (INT)", table_text),
            Paragraph("Delivers dynamic system alerts and ticket status change notices.", table_text)
        ]
    ]
    schema_table = Table(schema_data, colWidths=[90, 240, 174])
    schema_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), c_header_bg),
        ('GRID', (0, 0), (-1, -1), 0.5, c_border),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, c_bg_table]),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(schema_table)
    story.append(Spacer(1, 10))

    # ── SECTION 4: FINAL PROJECT FEATURES LIST ───────────────────
    story.append(Paragraph("4. Final Project Features List", h1_style))
    story.append(Paragraph(
        "The following complete set of core features are implemented and will be demonstrated during the final course presentation:",
        body_style
    ))

    features = [
        "<b>1. Role-Based Authentication & Session Access Control:</b> Multi-role login supporting Staff and Manager personas with bcrypt cryptographic password protection and secure Flask server session cookies.",
        "<b>2. Hazard Incident Reporting Engine:</b> Comprehensive hazard filing interface with auto-generated tickets (e.g. <code>ABC-2026-0923-XX</code>), multi-tier urgency classification, location tags, and live photo attachment previews.",
        "<b>3. Interactive Manager Resolution & Investigation Board:</b> Tabular and card views allowing safety managers to inspect pending tickets, view photo evidence, and mark incidents as 'Resolved' with automated audit timestamps.",
        "<b>4. Scheduled Safety Inspection Calendar:</b> Dynamic scheduling workflow to assign certified inspectors to specific jobsite sectors with automatic synchronization into the pending hazards queue.",
        "<b>5. Live System Notification Feed:</b> Real-time notification dropdown and alerts informing personnel of new hazard reports, resolved incidents, and scheduled inspections.",
        "<b>6. Safety Contacts Directory:</b> Searchable emergency contact roster of site safety coordinators, medical teams, and compliance officers.",
        "<b>7. CSV Compliance Data Export:</b> One-click export enabling managers to download resolved hazard logs (<code>SiteSafety_Resolved_Hazards.csv</code>) for regulatory compliance.",
        "<b>8. Dual Execution Mode (Local & Cloud):</b> Seamless local execution via <code>python main.py</code> and cloud deployment capability via PythonAnywhere WSGI."
    ]
    for feat in features:
        story.append(Paragraph(f"• {feat}", bullet_style))

    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>End of Deliverable Documentation</b> — Prepared by CPE100L Section A6 Group 1.", subtitle_style))

    # Build PDF with page numbers
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"[OK] Official Progress Report PDF generated: {output_filename}")


if __name__ == '__main__':
    output_pdf = "CPE100L_A6_Group1_SiteSafetyTracker_ProgressReport_Sept23.pdf"
    build_pdf(output_pdf)
