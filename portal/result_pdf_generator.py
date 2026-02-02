"""
PDF Generation for Student Result Report Cards
Matches the sample secondary school result format with:
- School header and logo
- Student information
- Subject results table with CA scores
- Affective and Psychomotor traits
- Class teacher and Principal comments
- Promotion status and next term date
"""
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.platypus.flowables import HRFlowable
from datetime import datetime
from io import BytesIO
import os


def get_ordinal_suffix(n):
    """Return ordinal suffix for a number (1st, 2nd, 3rd, etc.)"""
    if 11 <= n % 100 <= 13:
        return 'th'
    return {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')


def format_position(position):
    """Format position with ordinal suffix"""
    if position is None:
        return '-'
    return f"{position}{get_ordinal_suffix(position)}"


def draw_watermark(canvas, doc):
    """Draw a light watermark on the PDF page"""
    canvas.saveState()
    canvas.setFont('Helvetica-Bold', 40)
    canvas.setFillColor(colors.lightgrey)
    canvas.setFillAlpha(0.15)  # Very light and subtle
    
    # Positioning in the center of A4
    canvas.translate(A4[0]/2, A4[1]/2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "HaDerech Software Solution")
    canvas.restoreState()


def generate_student_result_pdf(
    school,
    school_class,
    academic_session,
    term,
    student_data,
    subjects,
    attendance_data=None,
    affective_traits=None,
    psychomotor_traits=None,
    term_report=None,
    class_info=None,
    all_term_results=None
):
    """
    Generate a comprehensive PDF result report for a single student.
    
    Args:
        school: School instance
        school_class: SchoolClass instance
        academic_session: AcademicSession instance
        term: Term name (e.g., 'First', 'Second', 'Third')
        student_data: Dictionary with student results
        subjects: List of Subject instances
        attendance_data: StudentAttendance instance
        affective_traits: StudentAffectiveTraits instance
        psychomotor_traits: StudentPsychomotorTraits instance
        term_report: StudentTermReport instance
        class_info: ClassTermInfo instance
        all_term_results: Dictionary of results from previous terms for this session
    
    Returns:
        BytesIO object containing PDF
    """
    
    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch,
        leftMargin=0.4*inch,
        rightMargin=0.4*inch
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    
    school_name_style = ParagraphStyle(
        'SchoolName',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#000080'),
        spaceAfter=2,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    school_address_style = ParagraphStyle(
        'SchoolAddress',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#333333'),
        spaceAfter=1,
        alignment=TA_CENTER
    )
    
    motto_style = ParagraphStyle(
        'Motto',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#800000'),
        spaceAfter=3,
        alignment=TA_CENTER,
        fontName='Helvetica-BoldOblique'
    )
    
    report_title_style = ParagraphStyle(
        'ReportTitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=colors.HexColor('#000000'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#000080'),
        spaceBefore=4,
        spaceAfter=2,
        fontName='Helvetica-Bold'
    )
    
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#333333'),
        spaceAfter=2
    )
    
    # Build document content
    story = []
    
    # ========== HEADER SECTION ==========
    # School logo (left), School info (center), Student photo (right)
    header_data = []
    
    # School logo placeholder (if available)
    school_logo = None
    if school.logo and os.path.exists(school.logo.path):
        try:
            school_logo = Image(school.logo.path, width=0.8*inch, height=0.8*inch)
        except:
            school_logo = Paragraph("🏫", school_name_style)
    else:
        school_logo = Paragraph("🏫", school_name_style)
    
    # School info
    motto_text = school.motto if school.motto else "MOTTO: EXCELLENCE IN EDUCATION"
    if not motto_text.upper().startswith("MOTTO:"):
        motto_text = f"MOTTO: {motto_text}"
        
    school_info = [
        Paragraph(f"<b>{school.name.upper()}</b>", school_name_style),
        Paragraph(school.address if school.address else "", school_address_style),
        Paragraph(f"<b>{motto_text.upper()}</b>", motto_style),
    ]
    
    # Student photo placeholder
    student_photo = Paragraph("👤", ParagraphStyle('Photo', fontSize=24, alignment=TA_CENTER))
    
    header_table_data = [[school_logo, school_info, student_photo]]
    header_table = Table(header_table_data, colWidths=[1*inch, 5*inch, 1*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('ALIGN', (2, 0), (2, 0), 'RIGHT'),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 0.1*inch))
    
    # Report title
    term_display = f"{term.upper()} TERM" if term else "TERM"
    story.append(Paragraph(
        f"<b>REPORT SHEET FOR {term_display}, {academic_session.name} ACADEMIC SESSION</b>",
        report_title_style
    ))
    story.append(Spacer(1, 0.1*inch))
    
    # ========== STUDENT INFO SECTION ==========
    student = student_data.get('student_obj') or student_data
    student_name = student_data.get('student', str(student) if hasattr(student, '__str__') else 'N/A')
    
    # Get attendance info
    times_present = attendance_data.times_present if attendance_data else 0
    times_opened = attendance_data.times_school_opened if attendance_data else (class_info.times_school_opened if class_info else 0)
    attendance_str = f"{times_present} out of {times_opened}" if times_opened else "N/A"
    
    # Get class position
    class_position = student_data.get('position', '-')
    position_str = format_position(class_position) if class_position else '-'
    
    # Get class population
    class_population = class_info.class_population if class_info else school_class.students.filter(is_active=True).count()
    
    # Student info in two columns
    # Fetch Gender and Age using new model fields
    gender = getattr(student, 'get_gender_display', lambda: 'N/A')() if hasattr(student, 'get_gender_display') else 'N/A'
    if gender == 'N/A' and hasattr(student, 'gender'):
        gender = 'Male' if student.gender == 'M' else 'Female'
    
    age = getattr(student, 'age', 'N/A')
    if age is None: age = 'N/A'
        
    info_data = [
        [
            Paragraph(f"<b>NAME:</b> {student_name}", info_style),
            Paragraph(f"<b>GENDER:</b> {gender}", info_style),
        ],
        [
            Paragraph(f"<b>CLASS:</b> {school_class.name}", info_style),
            Paragraph(f"<b>AGE:</b> {age}", info_style),
        ],
        [
            Paragraph(f"<b>ADMISSION NUMBER:</b> {student_data.get('admission', getattr(student, 'admission_number', 'N/A'))}", info_style),
            Paragraph(f"<b>ATTENDANCE:</b> {attendance_str}   <b>Class Position:</b> {position_str}", info_style),
        ],
        [
            Paragraph(f"<b>SESSION:</b> {academic_session.name}", info_style),
            Paragraph(f"<b>CLASS POPULATION:</b> {class_population}", info_style),
        ],
    ]
    
    info_table = Table(info_data, colWidths=[3.5*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.1*inch))
    
    # ========== HORIZONTAL LINE ==========
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#800000')))
    story.append(Spacer(1, 0.05*inch))
    
    # ========== MAIN CONTENT - RESULTS TABLE AND TRAITS SIDE BY SIDE ==========
    # Create the results table
    results_table_data = []
    
    # Header row
    header_row = [
        'SUBJECT', 'TEST 1', 'TEST 2', 'EXAM', 'TOTAL',
        'Letter\nGrade', 'Position', 'Subject\nHigh',
        '1st\nTerm', '2nd\nTerm', '3rd\nTerm', 'Remark'
    ]
    results_table_data.append(header_row)
    
    # Subject rows
    cumulative_total = 0
    max_obtainable = 0
    subject_count = 0
    
    for subject in subjects:
        subject_scores = student_data.get('subjects', {}).get(subject.name, {})
        
        test1 = subject_scores.get('test1', 0)
        test2 = subject_scores.get('test2', 0)
        exam = subject_scores.get('exam', 0)
        total = subject_scores.get('total', test1 + test2 + exam)
        grade = subject_scores.get('grade', '-')
        position = format_position(subject_scores.get('subject_position')) if subject_scores.get('subject_position') else '-'
        subject_high = subject_scores.get('subject_highest', '-')
        remark = subject_scores.get('remark', '-')
        
        # Get previous term scores
        first_term = '-'
        second_term = '-'
        third_term = '-'
        
        if all_term_results:
            first_term = all_term_results.get('First', {}).get(subject.name, {}).get('total', '-')
            second_term = all_term_results.get('Second', {}).get(subject.name, {}).get('total', '-')
            third_term = all_term_results.get('Third', {}).get(subject.name, {}).get('total', '-')
        
        # Set current term
        if term == 'First':
            first_term = total
        elif term == 'Second':
            second_term = total
        elif term == 'Third':
            third_term = total
        
        row = [
            subject.name,
            str(test1), str(test2), str(exam), str(total),
            grade, position, str(subject_high) if subject_high else '-',
            str(first_term), str(second_term), str(third_term), remark
        ]
        results_table_data.append(row)
        
        cumulative_total += total
        max_obtainable += 100
        subject_count += 1
    
    # Calculate averages
    average_score = round(cumulative_total / subject_count, 2) if subject_count > 0 else 0
    
    # Create results table
    col_widths = [1.3*inch, 0.4*inch, 0.4*inch, 0.4*inch, 0.4*inch,
                  0.4*inch, 0.4*inch, 0.5*inch, 0.4*inch, 0.4*inch, 0.4*inch, 0.6*inch]
    
    results_table = Table(results_table_data, colWidths=col_widths)
    
    results_table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000080')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
        ('TOPPADDING', (0, 0), (-1, 0), 4),
        
        # Data rows
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        
        # Highlight total column
        ('BACKGROUND', (4, 1), (4, -1), colors.HexColor('#ffffcc')),
        ('FONTNAME', (4, 1), (4, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(results_table)
    story.append(Spacer(1, 0.1*inch))
    
    # ========== SUMMARY ROW ==========
    summary_style = ParagraphStyle(
        'Summary',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#333333')
    )
    
    # Calculate grade from average
    if average_score >= 80:
        avg_grade = "A"
    elif average_score >= 70:
        avg_grade = "B"
    elif average_score >= 60:
        avg_grade = "C"
    elif average_score >= 50:
        avg_grade = "D"
    elif average_score >= 40:
        avg_grade = "E"
    else:
        avg_grade = "F"
    
    summary_data = [[
        Paragraph(f"<b>TERM AVERAGE</b>", summary_style),
        Paragraph(f"Subjects: {subject_count}", summary_style),
        Paragraph(f"<b>CUMULATIVE:</b> {cumulative_total:.2f}", summary_style),
        Paragraph(f"<b>MAXIMUM OBTAINABLE:</b> {max_obtainable}", summary_style),
        Paragraph(f"<b>AVERAGE SCORE:</b> {average_score:.2f}", summary_style),
        Paragraph(f"<b>{avg_grade}</b>", summary_style),
    ]]
    
    summary_table = Table(summary_data, colWidths=[1.2*inch, 0.9*inch, 1.3*inch, 1.5*inch, 1.3*inch, 0.8*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e8e8e8')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ========== TRAITS AND KEY SECTION SIDE BY SIDE ==========
    # Create traits tables
    
    # Affective Traits
    affective_header = [['AFFECTIVE TRAITS', 'RATING']]
    affective_data = []
    
    if affective_traits:
        affective_items = [
            ('1. Punctuality', affective_traits.punctuality),
            ('2. Mental Alertness', affective_traits.mental_alertness),
            ('3. Respect', affective_traits.respect),
            ('4. Neatness', affective_traits.neatness),
            ('5. Honesty', affective_traits.honesty),
            ('6. Politeness', affective_traits.politeness),
            ('7. Relationship with peers', affective_traits.relationship_with_peers),
            ('8. Willingness to learn', affective_traits.willingness_to_learn),
            ('9. Spirit of Teamwork', affective_traits.spirit_of_teamwork),
        ]
    else:
        affective_items = [
            ('1. Punctuality', 'C'),
            ('2. Mental Alertness', 'C'),
            ('3. Respect', 'C'),
            ('4. Neatness', 'C'),
            ('5. Honesty', 'C'),
            ('6. Politeness', 'C'),
            ('7. Relationship with peers', 'C'),
            ('8. Willingness to learn', 'C'),
            ('9. Spirit of Teamwork', 'C'),
        ]
    
    affective_data = affective_header + [[item[0], item[1]] for item in affective_items]
    affective_table = Table(affective_data, colWidths=[1.5*inch, 0.5*inch])
    affective_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000080')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    
    # Psychomotor Traits
    psychomotor_header = [['PSYCHOMOTOR TRAITS', 'RATING']]
    
    if psychomotor_traits:
        psychomotor_items = [
            ('1. Games & Sports', psychomotor_traits.games_and_sports),
            ('2. Verbal Skills', psychomotor_traits.verbal_skills),
            ('3. Artistic Creativity', psychomotor_traits.artistic_creativity),
            ('4. Musical Skills', psychomotor_traits.musical_skills),
            ('5. Dance Skills', psychomotor_traits.dance_skills),
        ]
    else:
        psychomotor_items = [
            ('1. Games & Sports', 'C'),
            ('2. Verbal Skills', 'C'),
            ('3. Artistic Creativity', 'C'),
            ('4. Musical Skills', 'C'),
            ('5. Dance Skills', 'C'),
        ]
    
    psychomotor_data = psychomotor_header + [[item[0], item[1]] for item in psychomotor_items]
    psychomotor_table = Table(psychomotor_data, colWidths=[1.5*inch, 0.5*inch])
    psychomotor_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000080')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
    ]))
    
    # Key to Grading
    grading_key_data = [
        ['KEY TO GRADING'],
        ['A (Excellent) = 80 - 100%'],
        ['B (Very Good) = 70 - 79%'],
        ['C (Good) = 60 - 69%'],
        ['D (Pass) = 50 - 59%'],
        ['E (Fair) = 40 - 49%'],
        ['F (Fail) = 0 - 39%'],
    ]
    
    grading_table = Table(grading_key_data, colWidths=[2*inch])
    grading_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#800000')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#fff5f5')]),
    ]))
    
    # Combine traits and key in a row
    traits_row = [[affective_table, psychomotor_table, grading_table]]
    traits_container = Table(traits_row, colWidths=[2.2*inch, 2.2*inch, 2.2*inch])
    traits_container.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
    ]))
    story.append(traits_container)
    story.append(Spacer(1, 0.15*inch))
    
    # ========== NEXT Term Info ==========
    next_term_date = term_report.next_term_begins.strftime('%d/%m/%Y') if term_report and term_report.next_term_begins else 'TBD'
    promotion_status = term_report.promotion_status if term_report else 'PENDING'
    
    next_term_data = [[
        Paragraph(f"<b>Next Begins:</b> {next_term_date}", info_style),
        Paragraph(f"<b>{promotion_status}</b>", ParagraphStyle('Promo', fontSize=10, fontName='Helvetica-Bold', alignment=TA_CENTER)),
    ]]
    
    next_term_table = Table(next_term_data, colWidths=[3.5*inch, 3.5*inch])
    next_term_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('ALIGN', (1, 0), (1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BACKGROUND', (1, 0), (1, 0), colors.HexColor('#ccffcc') if promotion_status == 'PROMOTED' else colors.HexColor('#ffcccc')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(next_term_table)
    story.append(Spacer(1, 0.15*inch))
    
    # ========== COMMENTS SECTION ==========
    comment_style = ParagraphStyle(
        'Comment',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#333333'),
        leading=12
    )
    
    # Helper for auto comments based on average
    def get_auto_comment(avg):
        if avg >= 80: return "An excellent result. Keep it up."
        if avg >= 70: return "A very good result. Keep it up."
        if avg >= 60: return "A good result. You can do better."
        if avg >= 50: return "A credit pass. Work harder next time."
        if avg >= 40: return "A fair result. You need to sit up."
        return "A poor result. Please study harder."

    def get_principal_comment(avg):
        if avg >= 80: return "Excellent performance."
        if avg >= 70: return "Very Good performance."
        if avg >= 60: return "Good performance."
        if avg >= 50: return "Fair performance."
        if avg >= 40: return "Poor performance."
        return "Fail. Needs to repeat."

    
    # Class Teacher Comment
    if term_report and term_report.class_teacher_comment:
        teacher_comment = term_report.class_teacher_comment
    else:
        teacher_comment = get_auto_comment(average_score)

    teacher_name = term_report.class_teacher_name if term_report else (
        str(school_class.form_teacher) if school_class.form_teacher else "Class Teacher"
    )
    
    story.append(Paragraph(f"<b>CLASS TEACHER'S COMMENT:</b> {teacher_comment}", comment_style))
    story.append(Paragraph(f"Keep it up.", comment_style) if not teacher_comment else Spacer(1, 0.05*inch))
    story.append(Spacer(1, 0.05*inch))
    
    # Prepare Teacher section (Comment only, no signature)
    teacher_sig_data = [[
        Paragraph(f"<b>Class Teacher:</b> {teacher_name}", info_style),
        "",
        "",
    ]]
    teacher_sig_table = Table(teacher_sig_data, colWidths=[3*inch, 1.5*inch, 1.5*inch])
    teacher_sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 0), 'LEFT'),
        ('LINEBELOW', (2, 0), (2, 0), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
    ]))
    story.append(teacher_sig_table)
    story.append(Spacer(1, 0.15*inch))
    
    # Principal Comment
    if term_report and term_report.principal_comment:
        principal_comment = term_report.principal_comment
    else:
        principal_comment = get_principal_comment(average_score)
    
    story.append(Paragraph(f"<b>PRINCIPAL'S COMMENT:</b> {principal_comment}", comment_style))
    story.append(Spacer(1, 0.05*inch))
    
    # Prepare Principal Signature and Stamp
    principal_sig_image = Paragraph("", info_style)
    school_stamp_image = Paragraph("Stamp", ParagraphStyle('Stamp', fontSize=8, alignment=TA_RIGHT))
    
    if school.principal_signature:
        try:
            # Try to load principal signature
            principal_sig_image = Image(school.principal_signature.path, width=1.5*inch, height=0.5*inch, preserveAspectRatio=True)
        except Exception:
            # Fallback to empty if file missing or corrupt
            principal_sig_image = Paragraph("", info_style)
        
    if school.stamp:
        try:
            # Try to load school stamp
            school_stamp_image = Image(school.stamp.path, width=0.8*inch, height=0.8*inch, preserveAspectRatio=True)
        except Exception:
            # Fallback to default label if file missing
            school_stamp_image = Paragraph("Stamp", ParagraphStyle('Stamp', fontSize=8, alignment=TA_RIGHT))
    
    principal_sig_data = [
        [
            principal_sig_image,
            "",
            school_stamp_image,
        ],
        [
            Paragraph(f"<b>Principal's Signature</b>", info_style),
            "",
            Paragraph(f"<b>Official Stamp</b>", info_style),
        ]
    ]
    principal_sig_table = Table(principal_sig_data, colWidths=[2.2*inch, 2.3*inch, 2.5*inch])
    principal_sig_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, 1), 'LEFT'),
        ('ALIGN', (2, 0), (2, 1), 'RIGHT'),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'BOTTOM'),
        ('TOPPADDING', (1, 0), (1, 1), 10),
    ]))
    story.append(principal_sig_table)
    
    # Build PDF
    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def generate_class_broadsheet_pdf(
    school,
    school_class,
    academic_session,
    term,
    students_data,
    subjects
):
    """
    Generate a broadsheet PDF showing all students' results for a class.
    
    Args:
        school: School instance
        school_class: SchoolClass instance
        academic_session: AcademicSession instance
        term: Term name
        students_data: List of student result dictionaries
        subjects: List of Subject instances
    
    Returns:
        BytesIO object containing PDF
    """
    from reportlab.lib.pagesizes import landscape, A3
    
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=landscape(A3),
        topMargin=0.3*inch,
        bottomMargin=0.3*inch,
        leftMargin=0.3*inch,
        rightMargin=0.3*inch
    )
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#000080'),
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # Header
    story.append(Paragraph(f"<b>{school.name.upper()}</b>", title_style))
    story.append(Paragraph(
        f"RESULT BROADSHEET - {school_class.name} - {term.upper()} TERM, {academic_session.name}",
        ParagraphStyle('Subtitle', fontSize=11, alignment=TA_CENTER, spaceAfter=10)
    ))
    story.append(Spacer(1, 0.2*inch))
    
    # Build table
    header_row = ['S/N', 'STUDENT NAME', 'ADM. NO.']
    for subject in subjects:
        header_row.append(subject.name[:8])  # Truncate long names
    header_row.extend(['TOTAL', 'AVG', 'POS'])
    
    table_data = [header_row]
    
    # Sort students by position
    sorted_students = sorted(students_data, key=lambda x: x.get('position', 999))
    
    for idx, student in enumerate(sorted_students, 1):

        row = [
            str(idx),
            student.get('student', 'N/A')[:25],  # Truncate long names
            student.get('admission', 'N/A'),
        ]
        
        student_total = 0
        for subject in subjects:
            subject_scores = student.get('subjects', {}).get(subject.name, {})
            total = subject_scores.get('total', 0)
            row.append(str(total))
            student_total += total
        
        row.extend([
            str(student.get('total', student_total)),
            f"{student.get('average', 0):.1f}",
            format_position(student.get('position'))
        ])
        table_data.append(row)
    
    # Create table with dynamic column widths
    col_widths = [0.3*inch, 1.5*inch, 0.8*inch]
    col_widths.extend([0.45*inch] * len(subjects))
    col_widths.extend([0.5*inch, 0.5*inch, 0.4*inch])
    
    table = Table(table_data, colWidths=col_widths)
    
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#000080')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('FONTSIZE', (0, 1), (-1, -1), 7),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('ALIGN', (1, 1), (1, -1), 'LEFT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    
    story.append(table)
    
    # Footer with Signatures
    story.append(Spacer(1, 0.5*inch))
    
    # Try to load images (robustly)
    principal_sig_image = Paragraph("", styles['Normal'])
    if school.principal_signature:
        try:
            principal_sig_image = Image(school.principal_signature.path, width=1.5*inch, height=0.5*inch, preserveAspectRatio=True)
        except Exception:
            pass
            
    school_stamp_image = Paragraph("Stamp", ParagraphStyle('Stamp', fontSize=8, alignment=TA_CENTER))
    if school.stamp:
        try:
            school_stamp_image = Image(school.stamp.path, width=0.8*inch, height=0.8*inch, preserveAspectRatio=True)
        except Exception:
            pass

    sig_data = [
        [principal_sig_image, "", school_stamp_image],
        [
            Paragraph("<b>Principal's Signature</b>", ParagraphStyle('SigLabel', fontSize=9, alignment=TA_LEFT)),
            "",
            Paragraph("<b>Official Stamp</b>", ParagraphStyle('SigLabel', fontSize=9, alignment=TA_RIGHT))
        ]
    ]
    
    sig_table = Table(sig_data, colWidths=[2.5*inch, 5.0*inch, 2.5*inch])
    sig_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,1), 'LEFT'),
        ('ALIGN', (2,0), (2,1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('LINEBELOW', (0, 0), (0, 0), 1, colors.black),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    
    story.append(sig_table)
    
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        f"<i>Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}</i>",
        ParagraphStyle('Footer', fontSize=8, textColor=colors.grey, alignment=TA_CENTER)
    ))
    
    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    pdf_buffer.seek(0)
    
    return pdf_buffer


def generate_cumulative_result_pdf(
    school,
    student,
    academic_session,
    results_data,
    cumulative_stats
):
    """
    Generate a cumulative PDF result for a student across all terms in a session.
    """
    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=A4,
        topMargin=0.3*inch,
        bottomMargin=0.3*inch,
        leftMargin=0.4*inch,
        rightMargin=0.4*inch
    )
    
    # Define styles
    styles = getSampleStyleSheet()
    header_style = ParagraphStyle(
        'Header', parent=styles['Heading1'], fontSize=14, alignment=TA_CENTER, textColor=colors.HexColor('#000080')
    )
    sub_header_style = ParagraphStyle(
        'SubHeader', parent=styles['Normal'], fontSize=10, alignment=TA_CENTER
    )
    
    story = []
    
    # --- Header ---
    logo_img = Paragraph("🏫", header_style)
    if school.logo and os.path.exists(school.logo.path):
        try:
             logo_img = Image(school.logo.path, width=0.8*inch, height=0.8*inch)
        except Exception as e:
            print(f"Error loading logo for PDF: {e}")
            logo_img = Paragraph("🏫", header_style)

    school_name = Paragraph(f"<b>{school.name.upper()}</b>", header_style)
    address = Paragraph(school.address or "", sub_header_style)
    title = Paragraph(f"<b>CUMULATIVE SESSION RESULT - {academic_session.name}</b>", 
                      ParagraphStyle('Title', parent=styles['Heading2'], alignment=TA_CENTER, spaceBefore=6))
    
    # Layout Header Table
    header_table = Table([[logo_img, [school_name, address]]], colWidths=[1*inch, 5*inch])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('ALIGN', (0,0), (0,0), 'CENTER'),
        ('ALIGN', (1,0), (1,0), 'CENTER'),
    ]))
    story.append(header_table)
    story.append(title)
    story.append(Spacer(1, 0.2*inch))
    
    # --- Student Info ---
    info_style = ParagraphStyle('Info', parent=styles['Normal'], fontSize=10)
    student_info = [
        [Paragraph(f"<b>Name:</b> {student.last_name} {student.first_name}", info_style),
         Paragraph(f"<b>Class:</b> {student.school_class.name}", info_style)],
        [Paragraph(f"<b>Admission No:</b> {student.admission_number}", info_style),
         Paragraph(f"<b>Session:</b> {academic_session.name}", info_style)],
    ]
    info_table = Table(student_info, colWidths=[3.5*inch, 3.5*inch])
    story.append(info_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- Results Table ---
    # Columns: Subject | 1st Term | 2nd Term | 3rd Term | Total | Avg | Grade
    headers = ['SUBJECT', '1st TERM', '2nd TERM', '3rd TERM', 'SESSION\nTOTAL', 'SESSION\nAVG', 'GRADE']
    data = [headers]
    
    col_widths = [2.5*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.8*inch, 0.6*inch]
    
    for subject, scores in results_data.items():
        row = [
            Paragraph(subject, ParagraphStyle('Cell', fontSize=9)),
            str(scores.get('First', '-')),
            str(scores.get('Second', '-')),
            str(scores.get('Third', '-')),
            str(scores.get('total', '-')),
            f"{scores.get('avg', 0):.2f}" if scores.get('avg') else '-',
            scores.get('grade', '-')
        ]
        data.append(row)
        
    result_table = Table(data, colWidths=col_widths)
    result_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#000080')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(result_table)
    story.append(Spacer(1, 0.2*inch))
    
    # --- Traits & Attendance ---
    attendance = cumulative_stats.get('attendance')
    affective = cumulative_stats.get('affective')
    psychomotor = cumulative_stats.get('psychomotor')
    
    # 1. Affective Traits Table
    aff_data = [['AFFECTIVE TRAITS', 'RATING']]
    aff_items = [
        ('1. Punctuality', affective.punctuality if affective else '-'),
        ('2. Mental Alertness', affective.mental_alertness if affective else '-'),
        ('3. Respect', affective.respect if affective else '-'),
        ('4. Neatness', affective.neatness if affective else '-'),
        ('5. Honesty', affective.honesty if affective else '-'),
        ('6. Politeness', affective.politeness if affective else '-'),
        ('7. Relationship', affective.relationship_with_peers if affective else '-'),
        ('8. Willingness', affective.willingness_to_learn if affective else '-'),
        ('9. Teamwork', affective.spirit_of_teamwork if affective else '-'),
    ]
    aff_data.extend(aff_items)
    
    # 2. Psychomotor Traits Table
    psy_data = [['PSYCHOMOTOR', 'RATING']]
    psy_items = [
        ('1. Sports', psychomotor.games_and_sports if psychomotor else '-'),
        ('2. Verbal', psychomotor.verbal_skills if psychomotor else '-'),
        ('3. Artistic', psychomotor.artistic_creativity if psychomotor else '-'),
        ('4. Musical', psychomotor.musical_skills if psychomotor else '-'),
        ('5. Dance', psychomotor.dance_skills if psychomotor else '-'),
    ]
    psy_data.extend(psy_items)
    
    # Style for traits tables
    trait_table_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#000080')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (1,0), (1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ])
    
    aff_table = Table(aff_data, colWidths=[1.5*inch, 0.6*inch])
    aff_table.setStyle(trait_table_style)
    
    psy_table = Table(psy_data, colWidths=[1.5*inch, 0.6*inch])
    psy_table.setStyle(trait_table_style)
    
    # Rating Key
    key_data = [
        ['RATING KEY'],
        ['A: Excellent'],
        ['B: Very Good'],
        ['C: Good'],
        ['D: Pass'],
        ['E: Fair'],
        ['F: Fail']
    ]
    key_table = Table(key_data, colWidths=[1.2*inch])
    key_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,0), colors.HexColor('#444444')),
        ('TEXTCOLOR', (0,0), (0,0), colors.whitesmoke),
        ('FONTNAME', (0,0), (0,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 7),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
    ]))
    
    # Combine traits and key side-by-side
    traits_layout = Table([[aff_table, psy_table, key_table]], colWidths=[2.2*inch, 2.2*inch, 1.5*inch])
    traits_layout.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(traits_layout)
    story.append(Spacer(1, 0.1*inch))

    # --- Summary ---
    summary_data = [
        [f"CUMULATIVE AVERAGE: {cumulative_stats.get('average', 0):.2f}%", f"POSITION: {format_position(cumulative_stats.get('position'))}"],
        [f"TOTAL SCORE: {cumulative_stats.get('total_score', 0):.2f}", f"SUBJECTS: {cumulative_stats.get('subject_count', 0)}"],
        [f"ATTENDANCE: {attendance.times_present if attendance else 0} / {attendance.times_school_opened if attendance else 0}", f"SESSION: {academic_session.name}"]
    ]
    summary_table = Table(summary_data, colWidths=[3.5*inch, 3.5*inch])
    summary_table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), 'Helvetica-Bold'),
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#e8e8e8')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 0.15*inch))
    
    # --- Principal Comment ---
    avg = cumulative_stats.get('average', 0)
    if avg >= 90: comment = "A truly exceptional performance! You have shown outstanding academic ability across all terms. Keep maintain this top-tier standard."
    elif avg >= 80: comment = "Excellent result. You have a strong grasp of your subjects. Continue to work hard to reach the very peak."
    elif avg >= 70: comment = "A very good session performance. You are consistently high-performing. Aim for excellence in the next session."
    elif avg >= 60: comment = "Good performance. You have potential to do much better if you stay focused on your studies."
    elif avg >= 50: comment = "A fair performance. You have passed, but more effort is required to improve your grades."
    elif avg >= 40: comment = "Pass. You are just meeting the requirements. I strongly advise you to dedicate more time to your books."
    else: comment = "Poor performance. This result is below standard. You must study much harder and seek help where necessary."
    
    story.append(Paragraph(f"<b>PRINCIPAL'S COMMENT:</b> {comment}", ParagraphStyle('Comment', fontSize=10)))
    story.append(Spacer(1, 0.3*inch))
    
    # Signatures
    sig_data = [
        [Paragraph("", info_style), Paragraph("_______________________", ParagraphStyle('SigLine', alignment=TA_RIGHT))],
        [Paragraph("", info_style), Paragraph("Principal's Signature", ParagraphStyle('SigLabel', alignment=TA_RIGHT, fontSize=8))]
    ]
    sig_table = Table(sig_data, colWidths=[4*inch, 3*inch])
    story.append(sig_table)
    
    doc.build(story, onFirstPage=draw_watermark, onLaterPages=draw_watermark)
    pdf_buffer.seek(0)
    return pdf_buffer
