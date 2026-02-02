def get_cumulative_result_data(student, academic_session):
    """
    Returns (results_data, cumulative_stats) for a student's cumulative session result.
    results_data: {subject: {First, Second, Third, total, avg, grade}}
    cumulative_stats: {average, position, total_score, subject_count, ...}
    """
    from academics.models import StudentResult, Subject
    results = StudentResult.objects.filter(
        student=student,
        academic_session=academic_session
    )
    subjects = Subject.objects.filter(
        id__in=results.values_list('subject', flat=True).distinct()
    )
    results_data = {}
    total_score = 0
    subject_count = 0
    for subject in subjects:
        subj_results = results.filter(subject=subject)
        term_scores = {term: None for term in ['First', 'Second', 'Third']}
        for r in subj_results:
            term_scores[r.term] = r.total
        # Calculate total and average for this subject
        term_vals = [v for v in term_scores.values() if v is not None]
        subj_total = sum(term_vals)
        subj_avg = subj_total / len(term_vals) if term_vals else 0
        grade = 'F'
        if subj_avg >= 80: grade = 'A'
        elif subj_avg >= 70: grade = 'B'
        elif subj_avg >= 60: grade = 'C'
        elif subj_avg >= 50: grade = 'D'
        elif subj_avg >= 40: grade = 'E'
        results_data[subject.name] = {
            'First': term_scores['First'] or '-',
            'Second': term_scores['Second'] or '-',
            'Third': term_scores['Third'] or '-',
            'total': subj_total,
            'avg': subj_avg,
            'grade': grade
        }
        total_score += subj_total
        subject_count += 1
    cumulative_avg = total_score / subject_count if subject_count else 0
    # Position logic (optional, can be improved for class-wide)
    cumulative_stats = {
        'average': cumulative_avg,
        'position': '-',  # Position calculation can be added
        'total_score': total_score,
        'subject_count': subject_count
    }
    return results_data, cumulative_stats
from django.db import transaction
from django.db.models import Sum
from .models import StudentResult, TermResultSummary


@transaction.atomic
def compute_term_results(school_class, academic_session, term):
    """
    Computes:
    - Subject-wise positions and highest scores
    - Total score per student
    - Average score
    - Class position
    """

    # 1. Update subject-wise positions and highest scores
    subjects = school_class.class_subjects.all().values_list('subject', flat=True)
    
    for subject_id in subjects:
        subject_results = StudentResult.objects.filter(
            school_class=school_class,
            subject_id=subject_id,
            academic_session=academic_session,
            term=term
        ).order_by('-total')
        
        if not subject_results:
            continue
            
        highest_score = subject_results[0].total
        
        # Assign positions for this subject
        current_pos = 1
        last_score = None
        for index, res in enumerate(subject_results):
            if last_score is not None and res.total < last_score:
                current_pos = index + 1
            
            res.subject_position = current_pos
            res.subject_highest = highest_score
            res.save(update_fields=['subject_position', 'subject_highest'])
            last_score = res.total

    # 2. Update overall term summaries
    results = (
        StudentResult.objects
        .filter(
            school_class=school_class,
            academic_session=academic_session,
            term=term,
        )
        .select_related("student")
    )

    student_map = {}
    for result in results:
        student_map.setdefault(result.student_id, []).append(result)

    summaries = []
    for student_id, records in student_map.items():
        total_score = sum(r.total for r in records)
        average = total_score / len(records) if records else 0

        summary, _ = TermResultSummary.objects.update_or_create(
            student_id=student_id,
            school_class=school_class,
            academic_session=academic_session,
            term=term,
            defaults={
                "total_score": total_score,
                "average": average,
            },
        )
        summaries.append(summary)

    # Sort by average (descending)
    summaries.sort(key=lambda s: s.average, reverse=True)

    # Assign positions (handles ties correctly)
    current_position = 1
    last_average = None

    for index, summary in enumerate(summaries):
        if last_average is not None and summary.average < last_average:
            current_position = index + 1

        summary.position = current_position
        summary.save(update_fields=["position"])
        last_average = summary.average
