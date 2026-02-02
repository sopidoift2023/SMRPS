from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from django.conf import settings
from .models import StudentResult, TermResultSummary, SchoolClass
from students.models import Student
import os


GRADE_DESCRIPTIONS = {
    "A": "Excellent",
    "B": "Very Good",
    "C": "Good",
    "D": "Pass",
    "E": "Fair",
    "F": "Fail",
}


def generate_student_result_pdf(student: Student, school_class: SchoolClass, academic_session, term: str):
    """
    Generate a high-school style result PDF for a single student.
    Includes:
    - Subject scores, test/exam breakdown
    - Total, average, grade
    - Class position
    - Affective & psychomotor traits
    - Teacher & principal comments
    - Promotion info
    """
    # -------------------------------
    # Setup
    # -------------------------------
    filename = f"{student.admission_number}_{term}_result.pdf"
    filepath = os.path.join(settings.MEDIA_ROOT, "results", filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)

    doc = SimpleDocTemplate(filepath, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    normal = styles["Normal"]
    title_style = ParagraphStyle(
        name="Title",
        fontSize=16,
        alignment=1,  # Center
        spaceAfter=10,
        bold=True,
    )

    # -------------------------------
    # School Header
    # -------------------------------
    school_name = student.school.name
    school_address = student.school.address if hasattr(student.school, "address") else ""
    school_motto = getattr(student.school, "motto", "")

    elements.append(Paragraph(f"<b>{school_name}</b>", title_style))
    elements.append(Paragraph(f"{school_address}", normal))
    if school_motto:
        elements.append(Paragraph(f"<i>{school_motto}</i>", normal))
    elements.append(Spacer(1, 12))

    # Optional logo
    if getattr(student.school, "logo", None):
        logo_path = student.school.logo.path
        if os.path.exists(logo_path):
            elements.append(Image(logo_path, width=80, height=80))
            elements.append(Spacer(1, 12))

    # -------------------------------
    # Student Info
    # -------------------------------
    elements.append(Paragraph(f"<b>Student Name:</b> {student.first_name} {student.last_name}", normal))
    elements.append(Paragraph(f"<b>Admission No:</b> {student.admission_number}", normal))
    elements.append(Paragraph(f"<b>Class:</b> {school_class.name}", normal))
    elements.append(Paragraph(f"<b>Term:</b> {term} | <b>Session:</b> {academic_session}", normal))
    elements.append(Spacer(1, 12))

    # -------------------------------
    # Subject Results Table
    # -------------------------------
    results = StudentResult.objects.filter(
        student=student,
        school_class=school_class,
        academic_session=academic_session,
        term=term,
    )

    data = [
        ["Subject", "Test 1", "Test 2", "Exam", "Total", "Grade"]
    ]

    for r in results:
        data.append([
            r.subject.name,
            r.test1,
            r.test2,
            r.exam,
            r.total,
            r.grade
        ])

    table = Table(data, repeatRows=1)
    table.setStyle(
        TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#d3d3d3")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
            ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ])
    )
    elements.append(table)
    elements.append(Spacer(1, 12))

    # -------------------------------
    # Term Summary
    # -------------------------------
    try:
        summary = TermResultSummary.objects.get(
            student=student,
            school_class=school_class,
            academic_session=academic_session,
            term=term,
        )
        elements.append(Paragraph(f"<b>Total Score:</b> {summary.total_score}", normal))
        elements.append(Paragraph(f"<b>Average:</b> {summary.average:.2f}", normal))
        elements.append(Paragraph(f"<b>Class Position:</b> {summary.position}", normal))

        promotion_text = "Promoted" if summary.average >= 50 else "Repeat"
        elements.append(Paragraph(f"<b>Promotion Status:</b> {promotion_text}", normal))
    except TermResultSummary.DoesNotExist:
        pass

    elements.append(Spacer(1, 12))

    # -------------------------------
    # Affective Traits
    # -------------------------------
    affective_traits = [
        "Punctuality", "Mental Alertness", "Respect", "Neatness",
        "Honesty", "Politeness", "Relationship with peers",
        "Willingness to learn", "Spirit of teamwork"
    ]
    elements.append(Paragraph("<b>Affective Traits</b>", normal))
    elements.append(Spacer(1, 6))
    for trait in affective_traits:
        elements.append(Paragraph(f"{trait}: _______", normal))
    elements.append(Spacer(1, 12))

    # -------------------------------
    # Psychomotor Traits
    # -------------------------------
    psychomotor_traits = ["Games & Sports", "Verbal Skills", "Artistic Creativity", "Musical Skills", "Dance Skills"]
    elements.append(Paragraph("<b>Psychomotor Traits</b>", normal))
    elements.append(Spacer(1, 6))
    for trait in psychomotor_traits:
        elements.append(Paragraph(f"{trait}: _______", normal))
    elements.append(Spacer(1, 12))

    # -------------------------------
    # Comments & Signatures
    # -------------------------------
    elements.append(Paragraph("Class Teacher's Comment: _______________________________", normal))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Class Teacher Signature & Stamp: _______________________", normal))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Principal's Comment: _________________________________", normal))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Principal Signature & Stamp: _________________________", normal))
    elements.append(Spacer(1, 12))

    # -------------------------------
    # Next Term Info
    # -------------------------------
    elements.append(Paragraph("Next Term Begins: ____________________", normal))

    # -------------------------------
    # Build PDF
    # -------------------------------
    doc.build(elements)

    return filepath
