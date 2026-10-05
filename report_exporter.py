"""
WhisperSense AI • Meeting Intelligence Report Exporter (Milestone 4 - Task 6)
Supports professional PDF dossier generation and structured CSV export.
"""

import io
import csv
import os
import html
from datetime import datetime
from typing import Dict, Any, Optional, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether
)

def _safe_str(val: Any, default: str = "") -> str:
    if val is None:
        return default
    return str(val).strip()

def _safe_pdf_text(val: Any, default: str = "") -> str:
    """
    Sanitizes arbitrary text for ReportLab Paragraphs to prevent XML/HTML injection crashes.
    """
    raw = _safe_str(val, default)
    return html.escape(raw, quote=False)

def generate_meeting_pdf(meeting: Dict[str, Any], output_path: Optional[str] = None) -> bytes:
    """
    Generates an executive, professional PDF meeting intelligence dossier.
    Includes:
    - Meeting details (ID, Title, Date, Duration, Word Count, Language)
    - Executive Summary
    - Key Discussion Points
    - Strategic Decisions Ledger
    - Action Items & Deliverables Table
    - Participants & Attendees
    - Deadlines & Milestones
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    # Custom Color Palette
    primary_color = colors.HexColor("#1E1B4B")     # Deep indigo
    accent_color = colors.HexColor("#4F46E5")      # Vibrant purple-blue
    secondary_color = colors.HexColor("#475569")   # Slate neutral
    light_bg = colors.HexColor("#F8FAFC")          # Off-white table row
    border_color = colors.HexColor("#E2E8F0")

    # Typography Styles
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.white
    )

    subtitle_style = ParagraphStyle(
        "DocSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#C7D2FE")
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=primary_color,
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        "BodyDark",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1E293B")
    )

    bullet_style = ParagraphStyle(
        "BulletItem",
        parent=body_style,
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=3
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=12,
        textColor=colors.white
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1E293B")
    )

    story = []

    # 1. Header Banner
    title_text = _safe_pdf_text(meeting.get("title"), "Executive Meeting Intelligence")
    meeting_id = _safe_pdf_text(meeting.get("meeting_id"), "MEET-UNKNOWN")
    created_at = _safe_pdf_text(meeting.get("created_at"), datetime.now().strftime("%Y-%m-%d %H:%M"))

    header_data = [
        [
            Paragraph(f"<b>🎙️ WhisperSense AI</b> &bull; Meeting Intelligence Dossier", subtitle_style),
            Paragraph(f"<b>Date:</b> {created_at[:10]}", subtitle_style)
        ],
        [
            Paragraph(f"<b>{title_text}</b>", title_style),
            Paragraph(f"<b>ID:</b> {meeting_id}", subtitle_style)
        ]
    ]

    header_table = Table(header_data, colWidths=[380, 150])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), primary_color),
        ("TOPPADDING", (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
        ("LEFTPADDING", (0, 0), (-1, -1), 14),
        ("RIGHTPADDING", (0, 0), (-1, -1), 14),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    # 2. Meeting Details & Metadata Grid
    duration_sec = float(meeting.get("duration_seconds") or 0.0)
    dur_str = f"{int(duration_sec // 60)}m {int(duration_sec % 60)}s" if duration_sec else "N/A"
    word_count = meeting.get("word_count") or (len(str(meeting.get("transcript") or "").split()))
    audio_fn = _safe_pdf_text(meeting.get("audio_filename"), "audio_recording")
    format_str = _safe_pdf_text(meeting.get("format"), "MP3")
    lang_str = _safe_pdf_text(meeting.get("language"), "EN")

    meta_data = [
        [
            Paragraph("<b>Meeting ID:</b>", body_style), Paragraph(meeting_id, body_style),
            Paragraph("<b>Audio File:</b>", body_style), Paragraph(audio_fn, body_style)
        ],
        [
            Paragraph("<b>Created Date:</b>", body_style), Paragraph(created_at, body_style),
            Paragraph("<b>Audio Duration:</b>", body_style), Paragraph(dur_str, body_style)
        ],
        [
            Paragraph("<b>Language:</b>", body_style), Paragraph(lang_str, body_style),
            Paragraph("<b>Spoken Words:</b>", body_style), Paragraph(f"{word_count:,} words", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[90, 175, 90, 175])
    meta_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), light_bg),
        ("BOX", (0, 0), (-1, -1), 1, border_color),
        ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # 3. Executive Summary
    story.append(Paragraph("📌 Executive Summary", h1_style))
    summary_text = _safe_pdf_text(meeting.get("summary"), "No executive summary available.")
    summary_table = Table([[Paragraph(summary_text, body_style)]], colWidths=[530])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
        ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#C7D2FE")),
        ("LINELEFT", (0, 0), (0, -1), 4, accent_color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("RIGHTPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 12))

    # 4. Key Discussion Points
    key_points = meeting.get("key_points") or []
    if key_points:
        story.append(Paragraph("💡 Key Discussion Points", h1_style))
        for kp in key_points:
            story.append(Paragraph(f"• {_safe_pdf_text(kp)}", bullet_style))
        story.append(Spacer(1, 10))

    # 5. Strategic Decisions Ledger
    decisions = meeting.get("decisions") or []
    if decisions:
        story.append(Paragraph("⚖️ Strategic Decisions & Consensus", h1_style))
        for d in decisions:
            story.append(Paragraph(f"• <b>Decision:</b> {_safe_pdf_text(d)}", bullet_style))
        story.append(Spacer(1, 10))

    # 6. Action Items & Deliverables Table
    action_items = meeting.get("action_items") or []
    story.append(Paragraph("📋 Action Items & Deliverables", h1_style))
    if action_items:
        act_rows = [[
            Paragraph("Task Description", table_header_style),
            Paragraph("Assignee", table_header_style),
            Paragraph("Priority", table_header_style),
            Paragraph("Deadline", table_header_style),
            Paragraph("Status", table_header_style)
        ]]

        for act in action_items:
            task_t = _safe_pdf_text(act.get("task"), "Unspecified task")
            assignee = _safe_pdf_text(act.get("assignee"), "Unassigned")
            priority = _safe_pdf_text(act.get("priority"), "Medium")
            deadline = _safe_pdf_text(act.get("deadline"), "Not specified")
            status_t = _safe_pdf_text(act.get("status"), "Pending")

            act_rows.append([
                Paragraph(task_t, table_cell_style),
                Paragraph(assignee, table_cell_style),
                Paragraph(priority, table_cell_style),
                Paragraph(deadline, table_cell_style),
                Paragraph(status_t, table_cell_style)
            ])

        act_table = Table(act_rows, colWidths=[200, 90, 60, 100, 80])
        act_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), accent_color),
            ("BOX", (0, 0), (-1, -1), 1, border_color),
            ("INNERGRID", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, light_bg])
        ]))
        story.append(act_table)
    else:
        story.append(Paragraph("<i>No explicit action items recorded for this session.</i>", body_style))
    story.append(Spacer(1, 12))

    # 7. Participants & Deadlines
    participants = meeting.get("participants") or []
    deadlines = meeting.get("deadlines") or []

    summary_part_rows = []
    if participants:
        part_str = _safe_pdf_text(", ".join([str(p) for p in participants]))
        summary_part_rows.append([
            Paragraph("<b>👥 Attendees:</b>", body_style),
            Paragraph(part_str, body_style)
        ])
    if deadlines:
        dl_str = _safe_pdf_text(", ".join([str(dl) for dl in deadlines]))
        summary_part_rows.append([
            Paragraph("<b>⏰ Deadlines Mentioned:</b>", body_style),
            Paragraph(dl_str, body_style)
        ])

    if summary_part_rows:
        part_table = Table(summary_part_rows, colWidths=[130, 400])
        part_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), light_bg),
            ("BOX", (0, 0), (-1, -1), 0.5, border_color),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        story.append(part_table)

    story.append(Spacer(1, 16))
    story.append(HRFlowable(width="100%", thickness=0.5, color=border_color, spaceBefore=4, spaceAfter=8))
    story.append(Paragraph(
        "Generated automatically by <b>WhisperSense AI</b> • Meeting Intelligence Platform & Knowledge Repository",
        ParagraphStyle("Footer", parent=styles["Normal"], fontName="Helvetica", fontSize=7.5, leading=10, textColor=secondary_color, alignment=1)
    ))

    # Build PDF document
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if output_path:
        with open(output_path, "wb") as f:
            f.write(pdf_bytes)

    return pdf_bytes


def generate_meeting_csv(meeting: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generates a structured multi-section CSV report containing complete meeting intelligence:
    - Meeting metadata
    - Executive summary
    - Key points
    - Strategic decisions
    - Action items
    - Participants & Deadlines
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # 1. Header Information
    writer.writerow(["SECTION", "FIELD / ITEM", "ASSIGNEE", "PRIORITY", "DEADLINE", "STATUS", "DETAILS"])
    
    # Metadata
    mid = _safe_str(meeting.get("meeting_id"))
    title = _safe_str(meeting.get("title"))
    created_at = _safe_str(meeting.get("created_at"))
    duration = _safe_str(meeting.get("duration_seconds"))
    word_count = _safe_str(meeting.get("word_count"))
    language = _safe_str(meeting.get("language"))

    writer.writerow(["METADATA", "Meeting ID", "", "", "", "", mid])
    writer.writerow(["METADATA", "Meeting Title", "", "", "", "", title])
    writer.writerow(["METADATA", "Created Date", "", "", "", "", created_at])
    writer.writerow(["METADATA", "Duration (seconds)", "", "", "", "", duration])
    writer.writerow(["METADATA", "Word Count", "", "", "", "", word_count])
    writer.writerow(["METADATA", "Language", "", "", "", "", language])

    # Summary
    summary = _safe_str(meeting.get("summary"))
    writer.writerow(["SUMMARY", "Executive Summary", "", "", "", "", summary])

    # Key Points
    for idx, kp in enumerate(meeting.get("key_points") or [], 1):
        writer.writerow(["KEY_POINT", f"Point {idx}", "", "", "", "", _safe_str(kp)])

    # Decisions
    for idx, dec in enumerate(meeting.get("decisions") or [], 1):
        writer.writerow(["DECISION", f"Decision {idx}", "", "", "", "", _safe_str(dec)])

    # Action Items
    for act in meeting.get("action_items") or []:
        task = _safe_str(act.get("task"))
        assignee = _safe_str(act.get("assignee"), "Unassigned")
        priority = _safe_str(act.get("priority"), "Medium")
        deadline = _safe_str(act.get("deadline"), "Not specified")
        status = _safe_str(act.get("status"), "Pending")
        writer.writerow(["ACTION_ITEM", task, assignee, priority, deadline, status, ""])

    # Participants
    for p in meeting.get("participants") or []:
        writer.writerow(["PARTICIPANT", _safe_str(p), "", "", "", "", ""])

    # Deadlines
    for dl in meeting.get("deadlines") or []:
        writer.writerow(["DEADLINE", _safe_str(dl), "", "", "", "", ""])

    csv_content = output.getvalue()
    output.close()

    if output_path:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)

    return csv_content


def generate_action_items_csv(meeting: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """
    Generates a dedicated action-items table CSV formatted for easy import into
    Excel, Jira, Notion, or project management tools.
    """
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["Meeting ID", "Meeting Title", "Task Description", "Assignee", "Priority", "Deadline", "Status"])

    mid = _safe_str(meeting.get("meeting_id"))
    title = _safe_str(meeting.get("title"))

    for act in meeting.get("action_items") or []:
        writer.writerow([
            mid,
            title,
            _safe_str(act.get("task")),
            _safe_str(act.get("assignee"), "Unassigned"),
            _safe_str(act.get("priority"), "Medium"),
            _safe_str(act.get("deadline"), "Not specified"),
            _safe_str(act.get("status"), "Pending")
        ])

    csv_content = output.getvalue()
    output.close()

    if output_path:
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_content)

    return csv_content
