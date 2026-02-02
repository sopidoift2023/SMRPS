"""
PDF Generation for Class Results
"""
from reportlab.lib.pagesizes import A4, landscape, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
from io import BytesIO


def generate_class_results_pdf(school, school_class, academic_session, term, results, subjects):
    """
    Generate a PDF report of class results
    
    Args:
        school: School instance
        school_class: SchoolClass instance
        academic_session: AcademicSession instance
        term: Term name (e.g., 'First')
        results: List of student results with scores
        subjects: List of Subject instances
    
    Returns:
        BytesIO object containing PDF
    """
    
    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=landscape(A4), topMargin=0.5*inch)
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=3,
        alignment=TA_CENTER
    )
    
    # Build document content
    story = []
    
    # Header
    story.append(Paragraph(f"{school.name}", title_style))
    story.append(Paragraph(f"Class: {school_class.name} - {term} Term Results", subtitle_style))
    story.append(Paragraph(f"Academic Session: {academic_session.name}", subtitle_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y, %H:%M')}", subtitle_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Build table data
    table_data = []
    
    # Header row - Position, Student, Admission #, then each subject with sub-headers
    header_row = ['Pos', 'Student Name', 'Admission #']
    subject_subheaders = []
    
    for subject in subjects:
        header_row.extend([subject.name, '', '', ''])
        subject_subheaders.append(subject.name)
    
    header_row.extend(['Avg', 'Pos'])
    table_data.append(header_row)
    
    # Sub-header row (T1, T2, Ex, Tot for each subject)
    subheader_row = ['', '', '']
    for _ in subjects:
        subheader_row.extend(['T1', 'T2', 'Ex', 'Tot'])
    subheader_row.extend(['', ''])
    table_data.append(subheader_row)
    
    # Data rows
    for result in results:
        row = [
            str(result['position']),
            result['student'],
            result['admission']
        ]
        
        # Add scores for each subject
        for subject in subjects:
            scores = result['subjects'].get(subject.name, {
                'test1': 0, 'test2': 0, 'exam': 0, 'total': 0
            })
            row.extend([
                str(scores.get('test1', 0)),
                str(scores.get('test2', 0)),
                str(scores.get('exam', 0)),
                str(scores.get('total', 0))
            ])
        
        row.extend([
            f"{result['average']:.2f}",
            str(result['position'])
        ])
        
        table_data.append(row)
    
    # Create table
    col_widths = [0.5*inch, 1.5*inch, 1.0*inch]  # Pos, Name, Admission
    for _ in subjects:
        col_widths.extend([0.6*inch, 0.6*inch, 0.6*inch, 0.7*inch])  # T1, T2, Ex, Tot
    col_widths.extend([0.6*inch, 0.5*inch])  # Average, Position
    
    table = Table(table_data, colWidths=col_widths)
    
    # Style table
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        
        # Sub-header styling
        ('BACKGROUND', (0, 1), (-1, 1), colors.HexColor('#e8eef5')),
        ('TEXTCOLOR', (0, 1), (-1, 1), colors.HexColor('#333333')),
        ('ALIGN', (0, 1), (-1, 1), 'CENTER'),
        ('FONTNAME', (0, 1), (-1, 1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 1), (-1, 1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, 1), 6),
        
        # Data rows
        ('ALIGN', (0, 2), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 2), (-1, -1), 8),
        ('ROWBACKGROUNDS', (0, 2), (-1, -1), [colors.white, colors.HexColor('#f5f5f5')]),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        
        # Subject total columns highlighting
    ]))
    
    # Highlight total columns for each subject
    col_idx = 3
    for _ in subjects:
        table.setStyle(TableStyle([
            ('BACKGROUND', (col_idx + 3, 2), (col_idx + 3, -1), colors.HexColor('#ffffcc')),
            ('FONTNAME', (col_idx + 3, 2), (col_idx + 3, -1), 'Helvetica-Bold'),
        ]))
        col_idx += 4
    
    # Highlight average column
    table.setStyle(TableStyle([
        ('BACKGROUND', (col_idx, 2), (col_idx, -1), colors.HexColor('#ccffcc')),
        ('FONTNAME', (col_idx, 2), (col_idx, -1), 'Helvetica-Bold'),
    ]))
    
    story.append(table)
    
    # Footer
    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        f"<i>Total Students: {len(results)} | Total Subjects: {len(subjects)}</i>",
        subtitle_style
    ))
    
    # Build PDF
    doc.build(story)
    
    # Reset buffer position
    pdf_buffer.seek(0)
    
    return pdf_buffer


def generate_individual_student_pdf(school, school_class, academic_session, term, student_data, subjects):
    """
    Generate an individual PDF report for a single student
    
    Args:
        school: School instance
        school_class: SchoolClass instance
        academic_session: AcademicSession instance
        term: Term name (e.g., 'First')
        student_data: Dictionary with student results {
            'student': student_name,
            'admission': admission_number,
            'subjects': {subject_name: {test1, test2, exam, total, grade}},
            'average': average_score,
            'position': class_position
        }
        subjects: List of Subject instances
    
    Returns:
        BytesIO object containing PDF
    """
    
    # Create PDF in memory
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(pdf_buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    
    # Define styles
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=6,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1a3a52'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    info_style = ParagraphStyle(
        'Info',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#333333'),
        spaceAfter=4,
        alignment=TA_LEFT
    )
    
    label_style = ParagraphStyle(
        'Label',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#666666'),
        spaceAfter=2,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    # Build document content
    story = []
    
    # Header
    story.append(Paragraph(f"{school.name}", title_style))
    story.append(Paragraph(f"Student Result Report - {term} Term", heading_style))
    story.append(Spacer(1, 0.15*inch))
    
    # Student Information Section
    info_data = [
        ['Student Name:', student_data['student']],
        ['Admission Number:', student_data['admission']],
        ['Class:', school_class.name],
        ['Academic Session:', academic_session.name],
    ]
    
    info_table = Table(info_data, colWidths=[2.0*inch, 3.5*inch])
    info_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#333333')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Grades Table
    story.append(Paragraph("Subject Performance", heading_style))
    story.append(Spacer(1, 0.1*inch))
    
    # Build table data
    table_data = [['Subject', 'Test 1', 'Test 2', 'Exam', 'Total', 'Grade']]
    
    for subject in subjects:
        subject_scores = student_data['subjects'].get(subject.name, {
            'test1': 0, 'test2': 0, 'exam': 0, 'total': 0, 'grade': '-'
        })
        
        table_data.append([
            subject.name,
            str(subject_scores.get('test1', 0)),
            str(subject_scores.get('test2', 0)),
            str(subject_scores.get('exam', 0)),
            str(subject_scores.get('total', 0)),
            str(subject_scores.get('grade', '-'))
        ])
    
    # Add summary row
    table_data.append(['', '', '', 'AVERAGE:', f"{student_data['average']:.2f}", ''])
    
    table = Table(table_data, colWidths=[2.5*inch, 1.0*inch, 1.0*inch, 1.0*inch, 1.0*inch, 0.8*inch])
    
    table.setStyle(TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a3a52')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, 0), 8),
        
        # Data rows
        ('ALIGN', (0, 1), (-1, -2), 'CENTER'),
        ('FONTSIZE', (0, 1), (-1, -2), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9f9f9')]),
        ('GRID', (0, 0), (-1, -2), 1, colors.HexColor('#cccccc')),
        ('VALIGN', (0, 0), (-1, -2), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -2), 6),
        ('RIGHTPADDING', (0, 0), (-1, -2), 6),
        ('TOPPADDING', (0, 0), (-1, -2), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -2), 5),
        
        # Summary row styling
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ccffcc')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 11),
        ('ALIGN', (0, -1), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, -1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 6),
        ('GRID', (0, -1), (-1, -1), 1, colors.HexColor('#cccccc')),
        
        # Grade column highlighting
        ('BACKGROUND', (5, 1), (5, -2), colors.HexColor('#ffffcc')),
        ('FONTNAME', (5, 1), (5, -2), 'Helvetica-Bold'),
    ]))
    
    story.append(table)
    story.append(Spacer(1, 0.3*inch))
    
    # Position info
    position_data = [
        ['Class Position:', str(student_data['position'])],
        ['Average Score:', f"{student_data['average']:.2f}%"],
    ]
    
    position_table = Table(position_data, colWidths=[2.0*inch, 3.5*inch])
    position_table.setStyle(TableStyle([
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 11),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#1a3a52')),
        ('TEXTCOLOR', (1, 0), (1, -1), colors.HexColor('#228B22')),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#f0f8f0')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(position_table)
    
    story.append(Spacer(1, 0.4*inch))
    
    # Footer
    story.append(Paragraph(
        f"<i>Generated: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}</i>",
        ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#999999'),
            alignment=TA_CENTER
        )
    ))
    
    # Build PDF
    doc.build(story)
    
    # Reset buffer position
    pdf_buffer.seek(0)
    
    return pdf_buffer
