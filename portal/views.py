from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
@login_required
def download_class_cumulative_zip(request, class_id):
    """Download ZIP of all students' cumulative session results for a class (form teacher or admin)."""
    user = request.user
    # Allow form teacher or admin
    is_admin = user.role == User.Role.SCHOOL_ADMIN
    is_form_teacher = False
    if user.role == User.Role.TEACHER:
        try:
            teacher_profile = TeacherProfile.objects.get(user=user)
            school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
            is_form_teacher = (school_class.form_teacher == teacher_profile)
        except (TeacherProfile.DoesNotExist, SchoolClass.DoesNotExist):
            return JsonResponse({'error': 'Unauthorized'}, status=403)
    elif is_admin:
        school_class = SchoolClass.objects.get(id=class_id, school=user.school)
    else:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    session_id = request.GET.get('session_id')
    if not session_id:
        return JsonResponse({'error': 'Missing session_id'}, status=400)
    session = AcademicSession.objects.get(id=session_id, school=school_class.school)
    from .result_pdf_generator import generate_cumulative_result_pdf
    from academics.services import get_cumulative_result_data
    students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for student in students:
            results_data, cumulative_stats = get_cumulative_result_data(student, session)
            pdf_buffer = generate_cumulative_result_pdf(school_class.school, student, session, results_data, cumulative_stats)
            student_name = f"{student.last_name}_{student.first_name}".replace(' ', '_')
            filename = f"{student_name}_{session.name}_Cumulative.pdf"
            zip_file.writestr(filename, pdf_buffer.getvalue())
    zip_buffer.seek(0)
    zip_filename = f"{school_class.name}_{session.name}_CumulativeResults.zip"
    response = FileResponse(zip_buffer, content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
    return response
@login_required
def download_cumulative_result(request):
    """Download cumulative session result PDF for the logged-in student."""
    user = request.user
    if user.role != User.Role.STUDENT:
        return render(request, "portal/unauthorized.html")
    student = get_object_or_404(Student, user=user)
    # Get latest session (or allow session selection via GET param)
    session_id = request.GET.get('session_id')
    if session_id:
        academic_session = get_object_or_404(AcademicSession, id=session_id, school=student.school)
    else:
        academic_session = AcademicSession.objects.filter(school=student.school).order_by('-name').first()
    if not academic_session:
        return render(request, "portal/unauthorized.html", {"message": "No session found."})
    # Compute cumulative data (reuse logic from result_pdf_generator or services)
    from .result_pdf_generator import generate_cumulative_result_pdf
    from academics.services import get_cumulative_result_data
    results_data, cumulative_stats = get_cumulative_result_data(student, academic_session)
    school = student.school
    pdf_buffer = generate_cumulative_result_pdf(school, student, academic_session, results_data, cumulative_stats)
    filename = f"{student.last_name}_{student.first_name}_{academic_session.name}_Cumulative.pdf"
    response = FileResponse(pdf_buffer, as_attachment=True, filename=filename)
    return response
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, FileResponse
from django.views.decorators.http import require_GET, require_POST
from django.db.models import Count, Q
from django.contrib import messages
from django.db import transaction
from academics.models import (
    SchoolClass, Subject, StudentResult, ClassSubject, TermResultSummary,
    StudentAttendance, StudentAffectiveTraits, StudentPsychomotorTraits,
    StudentTermReport, ClassTermInfo, RATING_CHOICES
)
from academics.services import compute_term_results
from students.models import Student
from teachers.models import TeacherProfile
from schools.models import AcademicSession, School
from accounts.models import User
from .forms import StudentResultForm
from .result_pdf_generator import generate_student_result_pdf, generate_class_broadsheet_pdf
import json
import zipfile
import io
# --- AI Assistant (Chatbot, Question Generator, Lesson Note, Download, CBT Publish) ---
from ai_assistant.services import generate_cbt_questions  # if needed for AI endpoints
from django.views.decorators.csrf import csrf_exempt

def home(request):
    """Home page view"""
    return render(request, "portal/home.html")

def dashboard_redirect(request):
    """Redirect to appropriate dashboard based on user role"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    user = request.user
    
    # Superusers go to admin
    if user.is_superuser:
        return redirect('admin:index')
    
    if user.role == User.Role.TEACHER:
        return redirect('portal:teacher_dashboard')
    elif user.role == User.Role.SCHOOL_ADMIN:
        return redirect('portal:school_admin_dashboard')
    elif user.role == User.Role.STUDENT:
        return redirect('portal:student_dashboard')
    else:
        return redirect('login')

@login_required
def change_password(request):
    """Self-service password change for all users"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif not request.user.check_password(old_password):
            messages.error(request, "Incorrect old password.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            # This is important to keep the user logged in but invalidates other sessions
            update_session_auth_hash(request, request.user)
            messages.success(request, "Password updated successfully! All other sessions have been logged out.")
            return redirect('portal:dashboard')
            
    return render(request, "portal/change_password.html")

@login_required
def teacher_dashboard(request):
    """Teacher dashboard view with stats and class overview"""
    user = request.user

    # Superusers should go to admin
    if user.is_superuser:
        return redirect('admin:index')

    if user.role != User.Role.TEACHER:
        return render(request, "portal/unauthorized.html")

    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
        
        # Get all classes assigned to this teacher (as subject teacher OR form teacher)
        assigned_classes = SchoolClass.objects.filter(
            Q(class_subjects__teacher=teacher_profile) | Q(form_teacher=teacher_profile),
            school=teacher_profile.school
        ).distinct().prefetch_related('students', 'class_subjects', 'class_subjects__subject', 'class_subjects__teacher')
        
        # Get subjects
        assigned_subjects = Subject.objects.filter(
            class_subjects__teacher=teacher_profile
        ).distinct()
        
        # Calculate stats
        total_students = Student.objects.filter(
            school_class__in=assigned_classes
        ).count()
        
        results_count = StudentResult.objects.filter(
            school_class__in=assigned_classes
        ).count()
        
        stats = {
            'total_classes': assigned_classes.count(),
            'total_students': total_students,
            'total_subjects': assigned_subjects.count(),
            'results_entered': results_count,
        }
        
    except TeacherProfile.DoesNotExist:
        teacher_profile = None
        assigned_classes = SchoolClass.objects.none()
        stats = {
            'total_classes': 0,
            'total_students': 0,
            'total_subjects': 0,
            'results_entered': 0,
        }

    class_subjects_data = {}
    if teacher_profile:
        for cls in assigned_classes:
            subjects_list = []
            # Use prefetch_related data
            for subj in cls.class_subjects.all():
                if subj.teacher_id == teacher_profile.id:
                    subjects_list.append({
                        'id': subj.subject.id,
                        'name': subj.subject.name
                    })
            class_subjects_data[str(cls.id)] = subjects_list

    context = {
        'assigned_classes': assigned_classes,
        'stats': stats,
        'teacher_profile': teacher_profile,
        'class_subjects_json': class_subjects_data, # Pass dictionary, template json_script handles it
    }

    return render(request, "portal/dashboard_teacher.html", context)

@login_required
def school_admin_dashboard(request):
    """School admin dashboard view"""
    user = request.user
    
    # Only school admins can access (superusers go to Django admin)
    if user.is_superuser:
        return redirect('admin:index')
    
    if user.role != User.Role.SCHOOL_ADMIN:
        return render(request, "portal/unauthorized.html")
    
    from students.models import Student
    total_students = Student.objects.filter(school=user.school, is_active=True).count()
    
    context = {
        'total_students': total_students,
    }
    
    return render(request, "portal/dashboard_admin.html", context)

@login_required
def student_dashboard(request):
    """Student dashboard view"""
    user = request.user
    if user.role != User.Role.STUDENT:
        return render(request, "portal/unauthorized.html")

    student = get_object_or_404(Student, user=user)
    # Get current/active session (latest by name)
    current_session = AcademicSession.objects.filter(school=student.school).order_by('-name').first()

    # Get all result summaries for this student (most recent first)
    summaries = TermResultSummary.objects.filter(student=student).select_related('academic_session').order_by('-academic_session__name', '-term')
    latest = summaries.first() if summaries else None

    context = {
        'student': student,
        'current_session': current_session,
        'summaries': summaries,
        'latest': latest,
    }
    return render(request, "portal/student_dashboard.html", context)

@login_required
def teacher_result_entry(request):
    """Teacher result entry view"""
    user = request.user

    if user.role != User.Role.TEACHER:
        return render(request, "portal/unauthorized.html")

    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
        
        # Get all classes and subjects assigned to this teacher
        classes = SchoolClass.objects.filter(
            class_subjects__teacher=teacher_profile
        ).distinct()
        
        subjects = Subject.objects.filter(
            class_subjects__teacher=teacher_profile
        ).distinct()
        
        # Get academic sessions for the teacher's school
        sessions = AcademicSession.objects.filter(
            school=teacher_profile.school
        ).order_by('-name')
        
    except TeacherProfile.DoesNotExist:
        classes = SchoolClass.objects.none()
        subjects = Subject.objects.none()
        sessions = AcademicSession.objects.none()

    context = {
        'classes': classes,
        'subjects': subjects,
        'sessions': sessions,
    }

    return render(request, "portal/teacher_result_entry.html", context)

@login_required
@require_GET
def get_students_by_class(request):
    """AJAX endpoint to get students by class"""
    class_id = request.GET.get('class_id')
    if class_id:
        students = Student.objects.filter(school_class_id=class_id).order_by('last_name', 'first_name')
        return render(request, "portal/students_partial.html", {"students": students})
    return render(request, "portal/students_partial.html", {"students": []})

@login_required
@require_GET
def get_class_subjects(request):
    """AJAX endpoint to get subjects for a class"""
    class_id = request.GET.get('class_id')
    user = request.user
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    if not class_id:
        return JsonResponse([], safe=False)
    
    # Verify teacher has access to this class
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get subjects for this class taught by this teacher
    subjects = Subject.objects.filter(
        class_subjects__school_class=school_class,
        class_subjects__teacher=teacher_profile,
        school=teacher_profile.school
    ).values('id', 'name').distinct()
    
    return JsonResponse(list(subjects), safe=False)

@login_required
@require_GET
def get_students_results(request):
    """AJAX endpoint to get students with their current results"""
    user = request.user
    class_id = request.GET.get('class_id')
    subject_id = request.GET.get('subject_id')
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if user.role not in [User.Role.TEACHER, User.Role.SCHOOL_ADMIN]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        if user.role == User.Role.TEACHER:
            profile = TeacherProfile.objects.get(user=user)
        else:
            profile = None
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    if not all([class_id, subject_id, session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    # Verify access to this class
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=user.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    students = Student.objects.filter(
        school_class_id=class_id,
        is_active=True
    ).order_by('last_name', 'first_name')
    
    data = []
    for student in students:
        try:
            result = StudentResult.objects.get(
                student=student,
                school_class_id=class_id,
                subject_id=subject_id,
                academic_session_id=session_id,
                term=term
            )
            result_data = {
                'id': result.id,
                'student_id': student.id,
                'student_name': f"{student.last_name} {student.first_name}",
                'admission_number': student.admission_number,
                'test1': result.test1,
                'test2': result.test2,
                'exam': result.exam,
                'total': result.total,
                'grade': result.grade,
            }
        except StudentResult.DoesNotExist:
            result_data = {
                'id': None,
                'student_id': student.id,
                'student_name': f"{student.last_name} {student.first_name}",
                'admission_number': student.admission_number,
                'test1': 0,
                'test2': 0,
                'exam': 0,
                'total': 0,
                'grade': '-',
            }
        
        data.append(result_data)
    
    return JsonResponse({
        'success': True,
        'count': len(data),
        'students': data
    })


@login_required
@require_GET
def get_term_results(request):
    """AJAX endpoint to get term results summary (averages and positions)"""
    class_id = request.GET.get('class_id')
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    user = request.user
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    if not all([class_id, session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    # Verify teacher has access
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    summaries = TermResultSummary.objects.filter(
        school_class_id=class_id,
        academic_session_id=session_id,
        term=term
    ).order_by('position')
    
    data = [{
        'student_id': s.student.id,
        'student': str(s.student),
        'admission': s.student.admission_number,
        'total': s.total_score,
        'average': round(s.average, 2),
        'position': s.position
    } for s in summaries]
    
    return JsonResponse({
        'success': True,
        'count': len(data),
        'results': data,
        'summaries': data  # Keep summaries for backward compatibility
    })

@login_required
@require_POST
def save_student_result(request):
    """AJAX endpoint to save individual student result"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user = request.user
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    # Get or create the result
    try:
        result = StudentResult.objects.get(
            student_id=data.get('student_id'),
            school_class_id=data.get('class_id'),
            subject_id=data.get('subject_id'),
            academic_session_id=data.get('session_id'),
            term=data.get('term')
        )
        # Verify teacher has permission
        if result.school_class.school != teacher_profile.school:
            return JsonResponse({'error': 'Permission denied'}, status=403)
    except StudentResult.DoesNotExist:
        # Create new result
        try:
            student = Student.objects.get(id=data.get('student_id'))
            school_class = SchoolClass.objects.get(id=data.get('class_id'))
            subject = Subject.objects.get(id=data.get('subject_id'))
            session = AcademicSession.objects.get(id=data.get('session_id'))
            
            # Verify teacher has access
            if school_class.school != teacher_profile.school:
                return JsonResponse({'error': 'Permission denied'}, status=403)
            
            result = StudentResult(
                student=student,
                school_class=school_class,
                subject=subject,
                academic_session=session,
                term=data.get('term')
            )
        except (Student.DoesNotExist, SchoolClass.DoesNotExist, Subject.DoesNotExist, AcademicSession.DoesNotExist) as e:
            return JsonResponse({'error': f'Invalid data: {str(e)}'}, status=400)
    
    # Update scores
    try:
        test1 = int(data.get('test1', 0))
        test2 = int(data.get('test2', 0))
        exam = int(data.get('exam', 0))
        
        if test1 < 0 or test1 > 20:
            return JsonResponse({'error': 'Test 1 must be between 0 and 20'}, status=400)
        if test2 < 0 or test2 > 20:
            return JsonResponse({'error': 'Test 2 must be between 0 and 20'}, status=400)
        if exam < 0 or exam > 60:
            return JsonResponse({'error': 'Exam must be between 0 and 60'}, status=400)
        
        result.test1 = test1
        result.test2 = test2
        result.exam = exam
        
        result.save()
        
        return JsonResponse({
            'success': True,
            'total': result.total,
            'grade': result.grade,
            'result_id': result.id,
            'message': 'Score saved successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def bulk_save_results(request):
    """AJAX endpoint to save multiple student results at once"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user = request.user
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    results_list = data.get('results', [])
    saved_count = 0
    errors = []
    
    try:
        with transaction.atomic():
            for result_data in results_list:
                try:
                    student = Student.objects.get(id=result_data.get('student_id'))
                    school_class = SchoolClass.objects.get(id=result_data.get('class_id'))
                    subject = Subject.objects.get(id=result_data.get('subject_id'))
                    session = AcademicSession.objects.get(id=result_data.get('session_id'))
                    
                    # Verify teacher has access
                    if school_class.school != teacher_profile.school:
                        errors.append(f"Access denied for {student.admission_number}")
                        continue
                    
                    result, created = StudentResult.objects.update_or_create(
                        student=student,
                        school_class=school_class,
                        subject=subject,
                        academic_session=session,
                        term=result_data.get('term'),
                        defaults={
                            'test1': int(result_data.get('test1', 0)),
                            'test2': int(result_data.get('test2', 0)),
                            'exam': int(result_data.get('exam', 0)),
                        }
                    )
                    saved_count += 1
                except Exception as e:
                    errors.append(str(e))
        
        return JsonResponse({
            'success': True,
            'saved_count': saved_count,
            'errors': errors,
            'message': f'Successfully saved {saved_count} results'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def compute_class_results(request):
    """AJAX endpoint to compute term results for a class"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user = request.user
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=data.get('class_id'))
        session = AcademicSession.objects.get(id=data.get('session_id'))
        term = data.get('term')
        
        # Verify teacher has access to this class
        if school_class.school != teacher_profile.school:
            return JsonResponse({'error': 'Permission denied'}, status=403)
        
        # Compute term results (this calculates averages and positions)
        compute_term_results(school_class, session, term)
        
        # Get the computed summaries
        summaries = TermResultSummary.objects.filter(
            school_class=school_class,
            academic_session=session,
            term=term
        ).order_by('position')
        
        summary_data = [{
            'student': str(s.student),
            'admission': s.student.admission_number,
            'total': s.total_score,
            'average': round(s.average, 2),
            'position': s.position
        } for s in summaries]
        
        return JsonResponse({
            'success': True,
            'message': 'Term results computed successfully',
            'count': len(summary_data),
            'summaries': summary_data
        })
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Academic session not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

# ========================================
# Interactive Teacher Dashboard Views
# ========================================

@login_required
def teacher_class_management(request, class_id):
    """
    Interactive teacher dashboard for managing a specific class:
    - View all students in class
    - Add new students
    - Enter scores by subject
    - Generate term results
    """
    user = request.user
    
    if user.role not in [User.Role.TEACHER, User.Role.SCHOOL_ADMIN]:
        return render(request, "portal/unauthorized.html")
    
    try:
        if user.role == User.Role.TEACHER:
            teacher_profile = TeacherProfile.objects.get(user=user)
        else:
            teacher_profile = None
    except TeacherProfile.DoesNotExist:
        return render(request, "portal/unauthorized.html")
    
    try:
        school_class = SchoolClass.objects.get(
            id=class_id,
            school=teacher_profile.school
        )
    except SchoolClass.DoesNotExist:
        return render(request, "portal/unauthorized.html")
    
    # Get all students in the class
    students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
    
    # Get all subjects taught by this teacher in this class
    subjects = Subject.objects.filter(
        class_subjects__school_class=school_class,
        class_subjects__teacher=teacher_profile
    ).distinct()
    
    # Get academic sessions
    sessions = AcademicSession.objects.filter(
        school=teacher_profile.school
    ).order_by('-name')
    
    from .forms import StudentQuickAddForm
    add_student_form = StudentQuickAddForm()
    
    # Check if current teacher is the form teacher for this class
    is_form_teacher = teacher_profile and school_class.form_teacher == teacher_profile or user.role == User.Role.SCHOOL_ADMIN
    
    context = {
        'school_class': school_class,
        'students': students,
        'subjects': subjects,
        'sessions': sessions,
        'add_student_form': add_student_form,
        'terms': [('First', 'First Term'), ('Second', 'Second Term'), ('Third', 'Third Term')],
        'is_form_teacher': is_form_teacher,
    }
    
    return render(request, "portal/teacher_class_dashboard.html", context)


@login_required
@require_POST
def teacher_add_student(request, class_id):
    """AJAX endpoint to add a new student to a class"""
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(
            id=class_id,
            school=teacher_profile.school
        )
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    from .forms import StudentQuickAddForm
    form = StudentQuickAddForm(request.POST)
    
    if form.is_valid():
        try:
            with transaction.atomic():
                student = Student(
                    school=teacher_profile.school,
                    school_class=school_class,
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    admission_number=form.cleaned_data['admission_number'],
                    gender=form.cleaned_data.get('gender', 'M'),
                    date_of_birth=form.cleaned_data.get('date_of_birth')
                )
                student.full_clean()
                student.save()
                
                return JsonResponse({
                    'success': True,
                    'student': {
                        'id': student.id,
                        'name': f"{student.last_name} {student.first_name}",
                        'admission_number': student.admission_number,
                    },
                    'message': f'Student {student.first_name} {student.last_name} added successfully'
                })
        except Exception as e:
            return JsonResponse({
                'error': str(e),
                'message': 'Error adding student'
            }, status=400)
    
    errors = {field: error for field, error in form.errors.items()}
    return JsonResponse({
        'error': 'Form validation failed',
        'errors': errors
    }, status=400)


@login_required
@require_GET
def teacher_enter_subject_scores(request, class_id):
    """
    AJAX endpoint to get students and their scores for entering results by subject
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(
            id=class_id,
            school=teacher_profile.school
        )
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    subject_id = request.GET.get('subject_id')
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if not all([subject_id, session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        subject = Subject.objects.get(id=subject_id, school=teacher_profile.school)
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except (Subject.DoesNotExist, AcademicSession.DoesNotExist):
        return JsonResponse({'error': 'Subject or session not found'}, status=404)
    
    # Verify teacher teaches this subject in this class
    try:
        ClassSubject.objects.get(
            school_class=school_class,
            subject=subject,
            teacher=teacher_profile
        )
    except ClassSubject.DoesNotExist:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    # Get all students
    students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
    
    students_data = []
    for student in students:
        try:
            result = StudentResult.objects.get(
                student=student,
                school_class=school_class,
                subject=subject,
                academic_session=session,
                term=term
            )
            students_data.append({
                'student': {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'admission_number': student.admission_number,
                },
                'result': {
                    'id': result.id,
                    'test1': result.test1,
                    'test2': result.test2,
                    'exam': result.exam,
                }
            })
        except StudentResult.DoesNotExist:
            students_data.append({
                'student': {
                    'id': student.id,
                    'first_name': student.first_name,
                    'last_name': student.last_name,
                    'admission_number': student.admission_number,
                },
                'result': {
                    'test1': 0,
                    'test2': 0,
                    'exam': 0,
                }
            })
    
    return JsonResponse({
        'success': True,
        'subject': subject.name,
        'term': term,
        'students': students_data
    })


@login_required
@require_POST
def teacher_save_subject_scores(request, class_id):
    """AJAX endpoint to save all scores for a subject in bulk"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user = request.user
    
    if user.role not in [User.Role.TEACHER, User.Role.SCHOOL_ADMIN]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    teacher_profile = None
    if user.role == User.Role.TEACHER:
        try:
            teacher_profile = TeacherProfile.objects.get(user=user)
        except TeacherProfile.DoesNotExist:
            return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    subject_id = data.get('subject_id')
    session_id = data.get('session_id')
    term = data.get('term')
    scores = data.get('scores', [])  # List of {student_id, test1, test2, exam}
    
    if not all([subject_id, session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=user.school)
        subject = Subject.objects.get(id=subject_id, school=user.school)
        session = AcademicSession.objects.get(id=session_id, school=user.school)
        
        # Verify teacher teaches this subject in this class (unless admin)
        if user.role == User.Role.TEACHER:
            ClassSubject.objects.get(
                school_class=school_class,
                subject=subject,
                teacher=teacher_profile
            )
    except (SchoolClass.DoesNotExist, Subject.DoesNotExist, AcademicSession.DoesNotExist, ClassSubject.DoesNotExist):
        return JsonResponse({'error': 'Access denied or invalid data'}, status=403)
    
    saved_count = 0
    errors = []
    
    try:
        with transaction.atomic():
            for score_entry in scores:
                try:
                    student_id = score_entry.get('student_id')
                    test1 = int(score_entry.get('test1', 0))
                    test2 = int(score_entry.get('test2', 0))
                    exam = int(score_entry.get('exam', 0))
                    
                    # Validate scores
                    if not (0 <= test1 <= 20):
                        errors.append(f"Student {student_id}: Test 1 must be 0-20")
                        continue
                    if not (0 <= test2 <= 20):
                        errors.append(f"Student {student_id}: Test 2 must be 0-20")
                        continue
                    if not (0 <= exam <= 60):
                        errors.append(f"Student {student_id}: Exam must be 0-60")
                        continue
                    
                    student = Student.objects.get(id=student_id, school_class=school_class)
                    
                    result, created = StudentResult.objects.update_or_create(
                        student=student,
                        school_class=school_class,
                        subject=subject,
                        academic_session=session,
                        term=term,
                        defaults={
                            'test1': test1,
                            'test2': test2,
                            'exam': exam,
                            'ca1': 0, 'ca2': 0, 'ca3': 0, 'ca4': 0 # Reset CAs
                        }
                    )
                    saved_count += 1
                except Student.DoesNotExist:
                    errors.append(f"Student {student_id} not found")
                except Exception as e:
                    errors.append(f"Error saving student {student_id}: {str(e)}")
        
        return JsonResponse({
            'success': True,
            'saved_count': saved_count,
            'errors': errors,
            'message': f'Successfully saved scores for {saved_count} students'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def teacher_generate_results(request, class_id):
    """
    AJAX endpoint to get term results summary showing student averages and positions
    """
    user = request.user
    
    if user.role not in [User.Role.TEACHER, User.Role.SCHOOL_ADMIN]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        school_class = SchoolClass.objects.get(
            id=class_id,
            school=user.school
        )
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    # Get term results
    summaries = TermResultSummary.objects.filter(
        school_class=school_class,
        academic_session=session,
        term=term
    ).order_by('position')
    
    results_data = [{
        'position': s.position,
        'student': str(s.student),
        'admission': s.student.admission_number,
        'total': s.total_score,
        'average': round(s.average, 2)
    } for s in summaries]
    
    return JsonResponse({
        'success': True,
        'results': results_data
    })


@login_required
@require_POST
def teacher_trigger_compute_results(request, class_id):
    """AJAX endpoint to trigger computation of term results for a class"""
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    session_id = data.get('session_id')
    term = data.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except (SchoolClass.DoesNotExist, AcademicSession.DoesNotExist):
        return JsonResponse({'error': 'Class or session not found'}, status=404)
    
    # Check if there are any results to compute
    results_count = StudentResult.objects.filter(
        school_class=school_class,
        academic_session=session,
        term=term
    ).count()
    
    if results_count == 0:
        return JsonResponse({
            'error': 'No student results found for this class/session/term combination',
            'message': 'Please enter scores for students first'
        }, status=400)
    
    try:
        # Compute term results (calculates averages and positions)
        compute_term_results(school_class, session, term)
        
        # Get the computed summaries
        summaries = TermResultSummary.objects.filter(
            school_class=school_class,
            academic_session=session,
            term=term
        ).order_by('position')
        
        summary_data = [{
            'student': str(s.student),
            'admission': s.student.admission_number,
            'total': s.total_score,
            'average': round(s.average, 2),
            'position': s.position
        } for s in summaries]
        
        return JsonResponse({
            'success': True,
            'message': 'Term results computed successfully',
            'count': len(summary_data),
            'summaries': summary_data,
            'results_url': f'/portal/teacher/{class_id}/results/?session_id={session_id}&term={term}'
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error computing results: {str(e)}'}, status=400)

# ========================================
# Form Teacher Final Results (Combined All Subjects)
# ========================================

@login_required
@require_POST
def form_teacher_generate_final_results(request, class_id):
    """
    AJAX endpoint for form teacher to generate combined final results
    Combines all subjects for each student, calculates average, and assigns position
    """
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    user = request.user
    
    if user.role not in [User.Role.TEACHER, User.Role.SCHOOL_ADMIN]:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        if user.role == User.Role.TEACHER:
            teacher_profile = TeacherProfile.objects.get(user=user)
        else:
            # For school admin, we'll allow it for now
            teacher_profile = None
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    session_id = data.get('session_id')
    term = data.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id)
        session = AcademicSession.objects.get(id=session_id)
        
        # Verify user is the form teacher or school admin
        if teacher_profile and school_class.form_teacher != teacher_profile:
            if user.role != User.Role.SCHOOL_ADMIN:
                return JsonResponse({'error': 'Only form teacher can generate final results'}, status=403)
        
        if school_class.school != session.school:
            return JsonResponse({'error': 'Session does not belong to this school'}, status=403)
    except (SchoolClass.DoesNotExist, AcademicSession.DoesNotExist):
        return JsonResponse({'error': 'Class or session not found'}, status=404)
    
    try:
        # Get all students in the class
        students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
        
        # Get all subjects for this class
        all_subjects = Subject.objects.filter(
            class_subjects__school_class=school_class
        ).distinct().order_by('name')
        
        student_results = []
        
        for student in students:
            # Get all scores for this student across all subjects
            scores_by_subject = {}
            total_score = 0
            subject_count = 0
            
            for subject in all_subjects:
                try:
                    result = StudentResult.objects.get(
                        student=student,
                        school_class=school_class,
                        subject=subject,
                        academic_session=session,
                        term=term
                    )
                    scores_by_subject[subject.name] = {
                        'ca1': result.ca1,
                        'ca2': result.ca2,
                        'ca3': result.ca3,
                        'ca4': result.ca4,
                        'test1': result.test1,
                        'test2': result.test2,
                        'exam': result.exam,
                        'total': result.total,
                        'grade': result.grade
                    }
                    total_score += result.total
                    subject_count += 1
                except StudentResult.DoesNotExist:
                    scores_by_subject[subject.name] = {
                        'ca1': 0, 'ca2': 0, 'ca3': 0, 'ca4': 0,
                        'test1': 0, 'test2': 0,
                        'exam': 0, 'total': 0, 'grade': '-'
                    }
            
            # Calculate average across all subjects
            average = (total_score / subject_count) if subject_count > 0 else 0
            
            student_results.append({
                'student_id': student.id,
                'student': str(student),
                'admission': student.admission_number,
                'subjects': scores_by_subject,
                'total': total_score,
                'average': round(average, 2),
                'subject_count': subject_count,
            })
        
        # Sort by average to assign positions (handle ties)
        student_results.sort(key=lambda x: x['average'], reverse=True)
        
        # Assign positions (handle ties correctly)
        current_position = 1
        last_average = None
        
        for index, result in enumerate(student_results):
            if last_average is not None and result['average'] < last_average:
                current_position = index + 1
            
            result['position'] = current_position
            last_average = result['average']
        
        return JsonResponse({
            'success': True,
            'message': 'Final results compiled successfully',
            'count': len(student_results),
            'subjects': [s.name for s in all_subjects],
            'results': student_results
        })
    
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error generating results: {str(e)}'}, status=400)


# ========================================
# API Endpoints for Admin Dashboard
# ========================================

@login_required
@require_GET
def get_school_classes(request):
    """Get all classes in school for admin dropdown"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    classes = SchoolClass.objects.filter(school=request.user.school, is_active=True).order_by('name')
    return JsonResponse({
        'classes': [{'id': c.id, 'name': c.name} for c in classes]
    })


@login_required
@require_GET
def get_school_sessions(request):
    """Get all academic sessions for admin dropdown"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    sessions = AcademicSession.objects.filter(school=request.user.school).order_by('-name')
    return JsonResponse({
        'sessions': [{'id': s.id, 'name': s.name} for s in sessions]
    })


@login_required
@require_GET
def download_class_results_pdf(request, class_id):
    """
    Download individual student result PDFs as ZIP (School Admin only)
    """
    user = request.user
    
    # Check if user is school admin
    if user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized - School Admin only'}, status=403)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=user.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing session_id or term parameter'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=user.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Academic session not found'}, status=404)
    
    try:
        # Get all students in the class
        students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
        
        # Get all subjects for this class
        all_subjects = Subject.objects.filter(
            class_subjects__school_class=school_class
        ).distinct().order_by('name')
        
        student_results = []
        
        for student in students:
            # Get all scores for this student across all subjects
            scores_by_subject = {}
            total_score = 0
            subject_count = 0
            
            for subject in all_subjects:
                try:
                    result = StudentResult.objects.get(
                        student=student,
                        school_class=school_class,
                        subject=subject,
                        academic_session=session,
                        term=term
                    )
                    scores_by_subject[subject.name] = {
                        'test1': result.test1,
                        'test2': result.test2,
                        'exam': result.exam,
                        'total': result.total,
                        'grade': result.grade
                    }
                    total_score += result.total
                    subject_count += 1
                except StudentResult.DoesNotExist:
                    scores_by_subject[subject.name] = {
                        'test1': 0,
                        'test2': 0,
                        'exam': 0,
                        'total': 0,
                        'grade': '-'
                    }
            
            # Calculate average across all subjects
            average = (total_score / subject_count) if subject_count > 0 else 0
            
            student_results.append({
                'student_id': student.id,
                'student': str(student),
                'admission': student.admission_number,
                'subjects': scores_by_subject,
                'total': total_score,
                'average': round(average, 2),
                'subject_count': subject_count,
            })
        
        # Sort by average to assign positions (handle ties)
        student_results.sort(key=lambda x: x['average'], reverse=True)
        
        # Assign positions (handle ties correctly)
        current_position = 1
        last_average = None
        
        for index, result in enumerate(student_results):
            if last_average is not None and result['average'] < last_average:
                current_position = index + 1
            
            result['position'] = current_position
            last_average = result['average']
        
        # Generate Broadsheet PDF using the new generator
        from .result_pdf_generator import generate_class_broadsheet_pdf
        pdf_buffer = generate_class_broadsheet_pdf(
            school=school_class.school,
            school_class=school_class,
            academic_session=session,
            term=term,
            students_data=student_results,
            subjects=all_subjects
        )
        
        # Create response
        response = FileResponse(pdf_buffer, content_type='application/pdf')
        filename = f"{school_class.name}_{term}Term_Broadsheet_{session.name.replace('/', '-')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error generating PDFs: {str(e)}'}, status=400)


@login_required
def download_form_teacher_broadsheet_pdf(request, class_id):
    """
    Download class results broadsheet as PDF (Form Teacher only)
    Combined view of all students in the class
    """
    user = request.user
    
    # Check if user is a teacher
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized - Teachers only'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    # Check if user is the form teacher of this class
    if school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Unauthorized - You must be the form teacher of this class'}, status=403)
    
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing session_id or term parameter'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Academic session not found'}, status=404)
    
    try:
        # Get all students in the class
        students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
        
        # Get all subjects for this class
        all_subjects = Subject.objects.filter(
            class_subjects__school_class=school_class
        ).distinct().order_by('name')
        
        student_results = []
        
        for student in students:
            # Get all scores for this student across all subjects
            scores_by_subject = {}
            total_score = 0
            subject_count = 0
            
            for subject in all_subjects:
                try:
                    result = StudentResult.objects.get(
                        student=student,
                        school_class=school_class,
                        subject=subject,
                        academic_session=session,
                        term=term
                    )
                    scores_by_subject[subject.name] = {
                        'ca1': result.ca1,
                        'ca2': result.ca2,
                        'ca3': result.ca3,
                        'ca4': result.ca4,
                        'test1': result.test1,
                        'test2': result.test2,
                        'exam': result.exam,
                        'total': result.total,
                        'grade': result.grade,
                        'subject_position': result.subject_position,
                        'subject_highest': result.subject_highest,
                    }
                    total_score += result.total
                    subject_count += 1
                except StudentResult.DoesNotExist:
                    scores_by_subject[subject.name] = {
                        'ca1': 0, 'ca2': 0, 'ca3': 0, 'ca4': 0,
                        'test1': 0, 'test2': 0, 'exam': 0, 'total': 0,
                        'grade': '-', 'subject_position': None, 'subject_highest': 0
                    }
            
            # Calculate average across all subjects
            average = (total_score / subject_count) if subject_count > 0 else 0
            
            student_results.append({
                'student_id': student.id,
                'student': str(student),
                'admission': student.admission_number,
                'subjects': scores_by_subject,
                'total': total_score,
                'average': round(average, 2),
                'subject_count': subject_count,
            })
        
        # Sort by average to assign positions (handle ties)
        student_results.sort(key=lambda x: x['average'], reverse=True)
        
        # Assign positions (handle ties correctly)
        current_position = 1
        last_average = None
        
        for index, result in enumerate(student_results):
            if last_average is not None and result['average'] < last_average:
                current_position = index + 1
            
            result['position'] = current_position
            last_average = result['average']
        
        # Generate class broadsheet PDF
        pdf_buffer = generate_class_broadsheet_pdf(
            school=teacher_profile.school,
            school_class=school_class,
            academic_session=session,
            term=term,
            students_data=student_results,
            subjects=all_subjects
        )
        
        # Create response
        response = FileResponse(pdf_buffer, content_type='application/pdf')
        filename = f"{teacher_profile.school.name.replace(' ', '_')}_{school_class.name}_Broadsheet_{term}Term_{session.name.replace('/', '-')}.pdf"
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error generating PDF: {str(e)}'}, status=400)


# ========================================
# School Admin Management APIs
# ========================================

@login_required
@require_POST
def create_teacher(request):
    """Create a new teacher (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        
        # Create user
        username = data.get('username')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        password = data.get('password')
        phone = data.get('phone', '')
        staff_id = data.get('staff_id')
        
        if not all([username, first_name, last_name, staff_id, password]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Check if username exists
        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'Username already exists'}, status=400)
        
        # Create user and teacher profile
        with transaction.atomic():
            user = User(
                username=username,
                first_name=first_name,
                last_name=last_name,
                role=User.Role.TEACHER,
                school=request.user.school
            )
            user.set_password(password)
            user.save()
            
            teacher = TeacherProfile.objects.create(
                user=user,
                school=request.user.school,
                middle_name=data.get('middle_name', ''),
                phone=phone,
                staff_id=staff_id
            )
        
        return JsonResponse({
            'success': True,
            'message': f'Teacher {first_name} {last_name} created successfully',
            'teacher': {
                'id': teacher.id,
                'name': str(teacher),
                'username': username,
                'staff_id': staff_id,
                'phone': phone
            }
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def edit_teacher(request, teacher_id):
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        teacher = get_object_or_404(TeacherProfile, id=teacher_id, school=request.user.school)
        user = teacher.user
        
        user.first_name = data.get('first_name', user.first_name)
        user.last_name = data.get('last_name', user.last_name)
        if data.get('password'):
            user.set_password(data['password'])
        user.save()
        
        teacher.middle_name = data.get('middle_name', teacher.middle_name)
        teacher.staff_id = data.get('staff_id', teacher.staff_id)
        teacher.phone = data.get('phone', teacher.phone)
        teacher.save()
        
        return JsonResponse({'success': True, 'message': 'Teacher updated successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_teacher(request, teacher_id):
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    teacher = get_object_or_404(TeacherProfile, id=teacher_id, school=request.user.school)
    user = teacher.user
    teacher.delete()
    user.delete()
    return JsonResponse({'success': True, 'message': 'Teacher deleted successfully'})

@login_required
@require_POST
def edit_subject(request, subject_id):
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        subject = get_object_or_404(Subject, id=subject_id, school=request.user.school)
        subject.name = data.get('name', subject.name)
        subject.code = data.get('code', subject.code)
        subject.save()
        return JsonResponse({'success': True, 'message': 'Subject updated successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_subject(request, subject_id):
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    subject = get_object_or_404(Subject, id=subject_id, school=request.user.school)
    subject.delete()
    return JsonResponse({'success': True, 'message': 'Subject deleted successfully'})

@login_required
@require_POST
def edit_class(request, class_id):
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        school_class = get_object_or_404(SchoolClass, id=class_id, school=request.user.school)
        school_class.name = data.get('name', school_class.name)
        
        form_teacher_id = data.get('form_teacher_id')
        if form_teacher_id:
            school_class.form_teacher = get_object_or_404(TeacherProfile, id=form_teacher_id, school=request.user.school)
        else:
            school_class.form_teacher = None
            
        school_class.save()
        return JsonResponse({'success': True, 'message': 'Class updated successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_class(request, class_id):
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    school_class = get_object_or_404(SchoolClass, id=class_id, school=request.user.school)
    school_class.delete()
    return JsonResponse({'success': True, 'message': 'Class deleted successfully'})

@login_required
@require_POST
def create_session(request):
    """Create a new academic session (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    try:
        data = json.loads(request.body)
        name = data.get('name')
        is_active = data.get('is_active', False)
        
        if not name:
            return JsonResponse({'error': 'Session name is required'}, status=400)
            
        with transaction.atomic():
            if is_active:
                # Deactivate other sessions for this school
                AcademicSession.objects.filter(school=request.user.school).update(is_active=False)
            
            session = AcademicSession.objects.create(
                school=request.user.school,
                name=name,
                is_active=is_active
            )
        return JsonResponse({'success': True, 'message': f'Session {name} created successfully', 'id': session.id})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_GET
def list_teachers(request):
    """List all teachers in school (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    teachers = TeacherProfile.objects.filter(school=request.user.school).order_by('user__last_name')
    return JsonResponse({
        'teachers': [
            {
                'id': t.id,
                'first_name': t.user.first_name,
                'last_name': t.user.last_name,
                'middle_name': t.middle_name,
                'name': f"{t.user.last_name} {t.user.first_name} {t.middle_name or ''}".strip(),
                'username': t.user.username,
                'staff_id': t.staff_id,
                'phone': t.phone
            }
            for t in teachers
        ]
    })


@login_required
@require_POST
def create_subject(request):
    """Create a new subject (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        name = data.get('name')
        code = data.get('code', '')
        
        if not name:
            return JsonResponse({'error': 'Subject name is required'}, status=400)
        
        # Check if subject exists for this school
        if Subject.objects.filter(school=request.user.school, name=name).exists():
            return JsonResponse({'error': 'Subject already exists in this school'}, status=400)
        
        subject = Subject.objects.create(
            school=request.user.school,
            name=name,
            code=code
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Subject {name} created successfully',
            'subject': {
                'id': subject.id,
                'name': subject.name,
                'code': subject.code
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def list_subjects(request):
    """List all subjects in school (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    subjects = Subject.objects.filter(school=request.user.school).order_by('name')
    return JsonResponse({
        'subjects': [
            {
                'id': s.id,
                'name': s.name,
                'code': s.code
            }
            for s in subjects
        ]
    })


@login_required
@require_POST
def create_class(request):
    """Create a new class (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        name = data.get('name')
        form_teacher_id = data.get('form_teacher_id')
        
        if not name:
            return JsonResponse({'error': 'Class name is required'}, status=400)
        
        # Check if class exists for this school
        if SchoolClass.objects.filter(school=request.user.school, name=name).exists():
            return JsonResponse({'error': 'Class already exists in this school'}, status=400)
        
        form_teacher = None
        if form_teacher_id:
            try:
                form_teacher = TeacherProfile.objects.get(id=form_teacher_id, school=request.user.school)
            except TeacherProfile.DoesNotExist:
                return JsonResponse({'error': 'Form teacher not found'}, status=400)
        
        school_class = SchoolClass.objects.create(
            school=request.user.school,
            name=name,
            form_teacher=form_teacher,
            is_active=True
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Class {name} created successfully',
            'class': {
                'id': school_class.id,
                'name': school_class.name,
                'form_teacher': str(form_teacher) if form_teacher else 'Not assigned'
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def list_classes(request):
    """List all classes in school (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    classes = SchoolClass.objects.filter(school=request.user.school, is_active=True).order_by('name')
    return JsonResponse({
        'classes': [
            {
                'id': c.id,
                'name': c.name,
                'form_teacher_id': c.form_teacher.id if c.form_teacher else '',
                'form_teacher': str(c.form_teacher) if c.form_teacher else 'Not assigned',
                'students': c.students.count()
            }
            for c in classes
        ]
    })


@login_required
@require_POST
def assign_teacher_to_class(request):
    """Assign teacher to class+subject (School Admin only)"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
        class_id = data.get('class_id')
        subject_id = data.get('subject_id')
        teacher_id = data.get('teacher_id')
        
        if not all([class_id, subject_id, teacher_id]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
        
        # Validate all exist and belong to school
        try:
            school_class = SchoolClass.objects.get(id=class_id, school=request.user.school)
            subject = Subject.objects.get(id=subject_id, school=request.user.school)
            teacher = TeacherProfile.objects.get(id=teacher_id, school=request.user.school)
        except (SchoolClass.DoesNotExist, Subject.DoesNotExist, TeacherProfile.DoesNotExist):
            return JsonResponse({'error': 'Class, subject, or teacher not found'}, status=400)
        
        # Create or update ClassSubject
        class_subject, created = ClassSubject.objects.update_or_create(
            school_class=school_class,
            subject=subject,
            defaults={'teacher': teacher}
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Teacher {teacher} assigned to {subject.name} in {school_class.name}',
            'assignment': {
                'class': school_class.name,
                'subject': subject.name,
                'teacher': str(teacher)
            }
        })
    
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def edit_student(request, student_id):
    user = request.user
    student = get_object_or_404(Student, id=student_id, school=user.school)
    
    # Check authorization
    if user.role == User.Role.TEACHER:
        # Teacher must be the form teacher of the student's class
        if student.school_class.form_teacher.user != user:
            return JsonResponse({'error': 'Only form teacher can edit student'}, status=403)
    elif user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        student.first_name = data.get('first_name', student.first_name)
        student.last_name = data.get('last_name', student.last_name)
        student.middle_name = data.get('middle_name', student.middle_name)
        student.admission_number = data.get('admission_number', student.admission_number)
        student.gender = data.get('gender', student.gender)
        
        date_of_birth = data.get('date_of_birth')
        if date_of_birth:
            from datetime import datetime
            try:
                student.date_of_birth = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                pass
        elif 'date_of_birth' in data and data['date_of_birth'] is None:
            student.date_of_birth = None
        
        # If admission number changed, update linked user username
        if 'admission_number' in data and data['admission_number'] != student.user.username:
            if User.objects.filter(username=data['admission_number']).exists():
                 return JsonResponse({'error': 'Admission number already exists as username'}, status=400)
            user_obj = student.user
            user_obj.username = data['admission_number']
            user_obj.save()
            
        # Allow admin/form teacher to reset student password
        if data.get('password'):
            user_obj = student.user
            user_obj.set_password(data['password'])
            user_obj.save()
            
        student.save()
        return JsonResponse({'success': True, 'message': 'Student updated successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@login_required
@require_POST
def delete_student(request, student_id):
    user = request.user
    student = get_object_or_404(Student, id=student_id, school=user.school)
    
    # Check authorization
    if user.role == User.Role.TEACHER:
        if student.school_class.form_teacher.user != user:
            return JsonResponse({'error': 'Only form teacher can delete student'}, status=403)
    elif user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    user_obj = student.user
    student.delete()
    if user_obj:
        user_obj.delete()
    return JsonResponse({'success': True, 'message': 'Student deleted successfully'})

@login_required
@require_POST
def admin_add_student(request):
    """Admin endpoint to add student to ANY class"""
    if request.user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
        
    try:
        data = json.loads(request.body)
        class_id = data.get('class_id')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        middle_name = data.get('middle_name', '')
        admission_number = data.get('admission_number')
        gender = data.get('gender', 'M')
        date_of_birth = data.get('date_of_birth')
        
        if not all([class_id, first_name, last_name, admission_number]):
            return JsonResponse({'error': 'Missing required fields'}, status=400)
            
        school_class = get_object_or_404(SchoolClass, id=class_id, school=request.user.school)
        
        if Student.objects.filter(admission_number=admission_number).exists():
            return JsonResponse({'error': 'Admission number already exists'}, status=400)
        
        # Parse date_of_birth if provided
        dob = None
        if date_of_birth:
            from datetime import datetime
            try:
                dob = datetime.strptime(date_of_birth, '%Y-%m-%d').date()
            except ValueError:
                pass
            
        student = Student.objects.create(
            school=request.user.school,
            school_class=school_class,
            first_name=first_name,
            last_name=last_name,
            middle_name=middle_name,
            admission_number=admission_number,
            gender=gender,
            date_of_birth=dob
        )
        return JsonResponse({'success': True, 'message': f'Student {first_name} added to {school_class.name}'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# ========================================
# Form Teacher Assessment Entry Views
# ========================================

@login_required
@require_POST
def generate_auto_comments(request, class_id):
    """
    Generate automatic comments for students based on their performance
    """
    user = request.user
    try:
        data = json.loads(request.body)
        session_id = data.get('session_id')
        term = data.get('term')
        
        if not all([session_id, term]):
            return JsonResponse({'error': 'Missing session_id or term'}, status=400)
            
        school_class = get_object_or_404(SchoolClass, id=class_id, school=user.school)
        session = get_object_or_404(AcademicSession, id=session_id, school=user.school)
        
        # Get students
        students = school_class.students.filter(is_active=True)
        
        # For each student, find their average and generate a comment
        comments_generated = 0
        for student in students:
            # Calculate average for current term
            results = StudentResult.objects.filter(
                student=student,
                school_class=school_class,
                academic_session=session,
                term=term
            )
            
            if not results.exists():
                continue
                
            total_score = sum(r.total for r in results)
            subject_count = results.count()
            average = total_score / subject_count if subject_count > 0 else 0
            
            # Generate comment based on average
            if average >= 80:
                comment = "An excellent result. You are a star! Keep up the brilliant performance."
            elif average >= 70:
                comment = "A very good performance. You have shown great potential. Keep it up."
            elif average >= 60:
                comment = "A good result. With more focus on your weak areas, you can do even better."
            elif average >= 50:
                comment = "A fair performance. You need to put in more effort to reach your full potential."
            elif average >= 40:
                comment = "Pass mark obtained. You are capable of much more; please study harder next term."
            else:
                comment = "Poor performance. You need to be far more serious with your studies. See me for counseling."
                
            # Save or update comment in StudentTermReport
            report, created = StudentTermReport.objects.get_or_create(
                student=student,
                school_class=school_class,
                academic_session=session,
                term=term
            )
            report.class_teacher_comment = comment
            report.save()
            comments_generated += 1
            
        return JsonResponse({
            'success': True, 
            'message': f'Automatically generated comments for {comments_generated} students based on their performance.'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


# form_teacher_assessment_page removed as requested

@login_required
def teacher_result_report_sheet(request, class_id):
    """
    New page for per-student assessment entry (Result Report Sheet)
    """
    user = request.user
    
    if user.role != User.Role.TEACHER and user.role != User.Role.SCHOOL_ADMIN:
        return render(request, "portal/unauthorized.html")
    
    try:
        if user.role == User.Role.TEACHER:
            teacher_profile = TeacherProfile.objects.get(user=user)
            school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
            if school_class.form_teacher != teacher_profile:
                return render(request, "portal/unauthorized.html")
        else: # Admin
            school_class = SchoolClass.objects.get(id=class_id, school=user.school)
    except (TeacherProfile.DoesNotExist, SchoolClass.DoesNotExist):
        return render(request, "portal/unauthorized.html")
    
    # Get students
    students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
    
    # Get sessions
    sessions = AcademicSession.objects.filter(school=school_class.school).order_by('-name')
    
    context = {
        'school_class': school_class,
        'students': students,
        'sessions': sessions,
        'terms': [('First', 'First Term'), ('Second', 'Second Term'), ('Third', 'Third Term')],
        'rating_choices': RATING_CHOICES,
    }
    
    return render(request, "portal/teacher_result_report_sheet.html", context)


@login_required
@require_GET
def get_student_assessments(request, class_id):
    """
    AJAX endpoint to get all assessments for students in a class for a given term
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    # If user is admin, allow
    if user.role == User.Role.SCHOOL_ADMIN:
        pass
    # Check if user is form teacher
    elif school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Only form teacher can access this'}, status=403)
    
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    # Get class term info
    class_info, _ = ClassTermInfo.objects.get_or_create(
        school_class=school_class,
        academic_session=session,
        term=term,
        defaults={
            'class_population': school_class.students.filter(is_active=True).count(),
            'times_school_opened': 0
        }
    )
    
    # Get all students
    students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
    
    students_data = []
    for student in students:
        # Get attendance
        try:
            attendance = StudentAttendance.objects.get(
                student=student,
                school_class=school_class,
                academic_session=session,
                term=term
            )
            attendance_data = {
                'times_present': attendance.times_present,
                'times_school_opened': attendance.times_school_opened
            }
        except StudentAttendance.DoesNotExist:
            attendance_data = {'times_present': 0, 'times_school_opened': class_info.times_school_opened}
        
        # Get affective traits
        try:
            affective = StudentAffectiveTraits.objects.get(
                student=student,
                school_class=school_class,
                academic_session=session,
                term=term
            )
            affective_data = {
                'punctuality': affective.punctuality,
                'mental_alertness': affective.mental_alertness,
                'respect': affective.respect,
                'neatness': affective.neatness,
                'honesty': affective.honesty,
                'politeness': affective.politeness,
                'relationship_with_peers': affective.relationship_with_peers,
                'willingness_to_learn': affective.willingness_to_learn,
                'spirit_of_teamwork': affective.spirit_of_teamwork,
            }
        except StudentAffectiveTraits.DoesNotExist:
            affective_data = {
                'punctuality': 'C', 'mental_alertness': 'C', 'respect': 'C',
                'neatness': 'C', 'honesty': 'C', 'politeness': 'C',
                'relationship_with_peers': 'C', 'willingness_to_learn': 'C',
                'spirit_of_teamwork': 'C'
            }
        
        # Get psychomotor traits
        try:
            psychomotor = StudentPsychomotorTraits.objects.get(
                student=student,
                school_class=school_class,
                academic_session=session,
                term=term
            )
            psychomotor_data = {
                'games_and_sports': psychomotor.games_and_sports,
                'verbal_skills': psychomotor.verbal_skills,
                'artistic_creativity': psychomotor.artistic_creativity,
                'musical_skills': psychomotor.musical_skills,
                'dance_skills': psychomotor.dance_skills,
            }
        except StudentPsychomotorTraits.DoesNotExist:
            psychomotor_data = {
                'games_and_sports': 'C', 'verbal_skills': 'C',
                'artistic_creativity': 'C', 'musical_skills': 'C',
                'dance_skills': 'C'
            }
        
        # Get term report
        try:
            report = StudentTermReport.objects.get(
                student=student,
                school_class=school_class,
                academic_session=session,
                term=term
            )
            report_data = {
                'class_teacher_comment': report.class_teacher_comment,
                'promotion_status': report.promotion_status,
            }
        except StudentTermReport.DoesNotExist:
            report_data = {
                'class_teacher_comment': '',
                'promotion_status': 'PENDING'
            }
        
        # Get performance summary for informative comments
        results = StudentResult.objects.filter(
            student=student,
            school_class=school_class,
            academic_session=session,
            term=term
        )
        total_score = sum(r.total for r in results)
        count = results.count()
        avg = round(total_score / count, 2) if count > 0 else 0
        
        students_data.append({
            'student_id': student.id,
            'name': str(student),
            'admission_number': student.admission_number,
            'average': avg,
            'subject_count': count,
            'attendance': attendance_data,
            'affective_traits': affective_data,
            'psychomotor_traits': psychomotor_data,
            'report': report_data
        })
    
    return JsonResponse({
        'success': True,
        'class_info': {
            'times_school_opened': class_info.times_school_opened,
            'class_population': class_info.class_population,
            'next_term_begins': class_info.next_term_begins.strftime('%Y-%m-%d') if class_info.next_term_begins else ''
        },
        'students': students_data
    })


@login_required
@require_POST
def save_class_term_info(request, class_id):
    """
    AJAX endpoint to save class term info (times school opened, next term date)
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    if school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Only form teacher can update this'}, status=403)
    
    session_id = data.get('session_id')
    term = data.get('term')
    times_school_opened = data.get('times_school_opened', 0)
    next_term_begins = data.get('next_term_begins')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    from datetime import datetime
    next_term_date = None
    if next_term_begins:
        try:
            next_term_date = datetime.strptime(next_term_begins, '%Y-%m-%d').date()
        except ValueError:
            pass
    
    class_info, created = ClassTermInfo.objects.update_or_create(
        school_class=school_class,
        academic_session=session,
        term=term,
        defaults={
            'times_school_opened': int(times_school_opened),
            'class_population': school_class.students.filter(is_active=True).count(),
            'next_term_begins': next_term_date
        }
    )
    
    return JsonResponse({
        'success': True,
        'message': 'Class term info saved successfully'
    })


@login_required
@require_POST
def save_student_attendance(request, class_id):
    """
    AJAX endpoint to save student attendance
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    if school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Only form teacher can update this'}, status=403)
    
    session_id = data.get('session_id')
    term = data.get('term')
    attendance_list = data.get('attendance', [])
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    # Get class term info for times_school_opened
    class_info, _ = ClassTermInfo.objects.get_or_create(
        school_class=school_class,
        academic_session=session,
        term=term,
        defaults={'class_population': school_class.students.filter(is_active=True).count()}
    )
    
    saved_count = 0
    try:
        with transaction.atomic():
            for att in attendance_list:
                student_id = att.get('student_id')
                times_present = int(att.get('times_present', 0))
                
                try:
                    student = Student.objects.get(id=student_id, school_class=school_class)
                except Student.DoesNotExist:
                    continue
                
                StudentAttendance.objects.update_or_create(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term,
                    defaults={
                        'times_present': times_present,
                        'times_school_opened': class_info.times_school_opened
                    }
                )
                saved_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Attendance saved for {saved_count} students'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def save_student_affective_traits(request, class_id):
    """
    AJAX endpoint to save student affective traits
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    if school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Only form teacher can update this'}, status=403)
    
    session_id = data.get('session_id')
    term = data.get('term')
    traits_list = data.get('traits', [])
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    saved_count = 0
    try:
        with transaction.atomic():
            for trait in traits_list:
                student_id = trait.get('student_id')
                
                try:
                    student = Student.objects.get(id=student_id, school_class=school_class)
                except Student.DoesNotExist:
                    continue
                
                StudentAffectiveTraits.objects.update_or_create(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term,
                    defaults={
                        'punctuality': trait.get('punctuality', 'C'),
                        'mental_alertness': trait.get('mental_alertness', 'C'),
                        'respect': trait.get('respect', 'C'),
                        'neatness': trait.get('neatness', 'C'),
                        'honesty': trait.get('honesty', 'C'),
                        'politeness': trait.get('politeness', 'C'),
                        'relationship_with_peers': trait.get('relationship_with_peers', 'C'),
                        'willingness_to_learn': trait.get('willingness_to_learn', 'C'),
                        'spirit_of_teamwork': trait.get('spirit_of_teamwork', 'C'),
                    }
                )
                saved_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Affective traits saved for {saved_count} students'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def save_student_psychomotor_traits(request, class_id):
    """
    AJAX endpoint to save student psychomotor traits
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    if school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Only form teacher can update this'}, status=403)
    
    session_id = data.get('session_id')
    term = data.get('term')
    traits_list = data.get('traits', [])
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    saved_count = 0
    try:
        with transaction.atomic():
            for trait in traits_list:
                student_id = trait.get('student_id')
                
                try:
                    student = Student.objects.get(id=student_id, school_class=school_class)
                except Student.DoesNotExist:
                    continue
                
                StudentPsychomotorTraits.objects.update_or_create(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term,
                    defaults={
                        'games_and_sports': trait.get('games_and_sports', 'C'),
                        'verbal_skills': trait.get('verbal_skills', 'C'),
                        'artistic_creativity': trait.get('artistic_creativity', 'C'),
                        'musical_skills': trait.get('musical_skills', 'C'),
                        'dance_skills': trait.get('dance_skills', 'C'),
                    }
                )
                saved_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Psychomotor traits saved for {saved_count} students'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def save_student_term_reports(request, class_id):
    """
    AJAX endpoint to save student term reports (comments, promotion)
    """
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Unauthorized'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    if school_class.form_teacher != teacher_profile:
        return JsonResponse({'error': 'Only form teacher can update this'}, status=403)
    
    session_id = data.get('session_id')
    term = data.get('term')
    reports_list = data.get('reports', [])
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=teacher_profile.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    # Get class term info for next_term_begins
    class_info = ClassTermInfo.objects.filter(
        school_class=school_class,
        academic_session=session,
        term=term
    ).first()
    
    saved_count = 0
    try:
        with transaction.atomic():
            for rpt in reports_list:
                student_id = rpt.get('student_id')
                
                try:
                    student = Student.objects.get(id=student_id, school_class=school_class)
                except Student.DoesNotExist:
                    continue
                
                StudentTermReport.objects.update_or_create(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term,
                    defaults={
                        'class_teacher_comment': rpt.get('class_teacher_comment', ''),
                        'class_teacher_name': str(teacher_profile),
                        'promotion_status': rpt.get('promotion_status', 'PENDING'),
                        'next_term_begins': class_info.next_term_begins if class_info else None
                    }
                )
                saved_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Term reports saved for {saved_count} students'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_POST
def save_principal_comments(request, class_id):
    """
    AJAX endpoint for school admin to save principal comments
    """
    user = request.user
    
    if user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Unauthorized - School Admin only'}, status=403)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    try:
        school_class = SchoolClass.objects.get(id=class_id, school=user.school)
    except SchoolClass.DoesNotExist:
        return JsonResponse({'error': 'Class not found'}, status=404)
    
    session_id = data.get('session_id')
    term = data.get('term')
    comments_list = data.get('comments', [])
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing parameters'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=user.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Session not found'}, status=404)
    
    saved_count = 0
    try:
        with transaction.atomic():
            for cmt in comments_list:
                student_id = cmt.get('student_id')
                
                try:
                    student = Student.objects.get(id=student_id, school_class=school_class)
                except Student.DoesNotExist:
                    continue
                
                report, created = StudentTermReport.objects.get_or_create(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term
                )
                report.principal_comment = cmt.get('principal_comment', '')
                report.save()
                saved_count += 1
        
        return JsonResponse({
            'success': True,
            'message': f'Principal comments saved for {saved_count} students'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@login_required
@require_GET
def download_comprehensive_result_pdf(request, class_id):
    """
    Download comprehensive individual student result PDFs as ZIP (School Admin or Form Teacher)
    Uses the new result_pdf_generator that matches the sample format
    """
    user = request.user
    
    # Check if user is school admin or form teacher
    is_admin = user.role == User.Role.SCHOOL_ADMIN
    is_form_teacher = False
    
    try:
        if user.role == User.Role.TEACHER:
            teacher_profile = TeacherProfile.objects.get(user=user)
            school_class = SchoolClass.objects.get(id=class_id, school=teacher_profile.school)
            is_form_teacher = (school_class.form_teacher == teacher_profile)
        elif is_admin:
            school_class = SchoolClass.objects.get(id=class_id, school=user.school)
        else:
            return JsonResponse({'error': 'Unauthorized'}, status=403)
            
        if not (is_admin or is_form_teacher):
            return JsonResponse({'error': 'Unauthorized - Form Teacher or Admin only'}, status=403)
            
    except (TeacherProfile.DoesNotExist, SchoolClass.DoesNotExist):
        return JsonResponse({'error': 'Class or Teacher profile not found'}, status=404)
    
    session_id = request.GET.get('session_id')
    term = request.GET.get('term')
    
    if not all([session_id, term]):
        return JsonResponse({'error': 'Missing session_id or term parameter'}, status=400)
    
    try:
        session = AcademicSession.objects.get(id=session_id, school=user.school)
    except AcademicSession.DoesNotExist:
        return JsonResponse({'error': 'Academic session not found'}, status=404)
    
    try:
        # Get all students in the class
        students = school_class.students.filter(is_active=True).order_by('last_name', 'first_name')
        
        # Get all subjects for this class
        all_subjects = Subject.objects.filter(
            class_subjects__school_class=school_class
        ).distinct().order_by('name')
        
        # Get class term info
        class_info = ClassTermInfo.objects.filter(
            school_class=school_class,
            academic_session=session,
            term=term
        ).first()
        
        student_results = []
        
        for student in students:
            # Get all scores for this student across all subjects
            scores_by_subject = {}
            total_score = 0
            subject_count = 0
            
            for subject in all_subjects:
                try:
                    result = StudentResult.objects.get(
                        student=student,
                        school_class=school_class,
                        subject=subject,
                        academic_session=session,
                        term=term
                    )
                    scores_by_subject[subject.name] = {
                        'ca1': result.ca1,
                        'ca2': result.ca2,
                        'ca3': result.ca3,
                        'ca4': result.ca4,
                        'test1': result.test1,
                        'test2': result.test2,
                        'exam': result.exam,
                        'total': result.total,
                        'grade': result.grade,
                        'remark': result.remark,
                        'subject_position': result.subject_position,
                        'subject_highest': result.subject_highest,
                    }
                    total_score += result.total
                    subject_count += 1
                except StudentResult.DoesNotExist:
                    scores_by_subject[subject.name] = {
                        'ca1': 0, 'ca2': 0, 'ca3': 0, 'ca4': 0,
                        'test1': 0, 'test2': 0, 'exam': 0, 'total': 0,
                        'grade': '-', 'remark': '-',
                        'subject_position': None, 'subject_highest': 0
                    }
            
            # Calculate average across all subjects
            average = (total_score / subject_count) if subject_count > 0 else 0
            
            student_results.append({
                'student_id': student.id,
                'student_obj': student,
                'student': str(student),
                'admission': student.admission_number,
                'subjects': scores_by_subject,
                'total': total_score,
                'average': round(average, 2),
                'subject_count': subject_count,
            })
        
        # Sort by average to assign positions (handle ties)
        student_results.sort(key=lambda x: x['average'], reverse=True)
        
        # Assign positions (handle ties correctly)
        current_position = 1
        last_average = None
        
        for index, result in enumerate(student_results):
            if last_average is not None and result['average'] < last_average:
                current_position = index + 1
            
            result['position'] = current_position
            last_average = result['average']
        
        # Create ZIP file with individual PDFs
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for result in student_results:
                student = result['student_obj']
                
                # Get attendance
                attendance = StudentAttendance.objects.filter(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term
                ).first()
                
                # Get affective traits
                affective = StudentAffectiveTraits.objects.filter(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term
                ).first()
                
                # Get psychomotor traits
                psychomotor = StudentPsychomotorTraits.objects.filter(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term
                ).first()
                
                # Get term report
                term_report = StudentTermReport.objects.filter(
                    student=student,
                    school_class=school_class,
                    academic_session=session,
                    term=term
                ).first()

                # Get all results for this student in this session for previous term total calculation
                all_session_results = StudentResult.objects.filter(
                    student=student,
                    academic_session=session
                ).select_related('subject')
                
                all_term_results = {}
                for r in all_session_results:
                    if r.term not in all_term_results:
                        all_term_results[r.term] = {}
                    all_term_results[r.term][r.subject.name] = {
                        'total': r.total,
                        'grade': r.grade
                    }
                
                # Generate comprehensive PDF using the class school (more direct)
                pdf_buffer = generate_student_result_pdf(
                    school=school_class.school,
                    school_class=school_class,
                    academic_session=session,
                    term=term,
                    student_data=result,
                    subjects=all_subjects,
                    attendance_data=attendance,
                    affective_traits=affective,
                    psychomotor_traits=psychomotor,
                    term_report=term_report,
                    class_info=class_info,
                    all_term_results=all_term_results
                )
                
                # Create filename
                student_name = result['student'].replace(' ', '_')
                admission_num = result['admission'].replace(' ', '_').replace('/', '-')
                filename = f"{student_name}_{admission_num}.pdf"
                
                # Add PDF to ZIP
                zip_file.writestr(filename, pdf_buffer.getvalue())
        
        # Reset buffer position
        zip_buffer.seek(0)
        
        # Create response
        response = FileResponse(zip_buffer, content_type='application/zip')
        zip_filename = f"{user.school.name.replace(' ', '_')}_{school_class.name}_{term}Term_Results_{session.name.replace('/', '-')}.zip"
        response['Content-Disposition'] = f'attachment; filename="{zip_filename}"'
        
        return response
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': f'Error generating PDFs: {str(e)}'}, status=400)

# --- AI Assistant (Chatbot, Question Generator, Lesson Note, Download, CBT Publish) ---

@login_required
def ai_assistant(request):
    """Main AI Assistant page (chatbot, generator, lesson note)"""
    user = request.user
    # You may want to pass assigned_classes for CBT publishing, etc.
    assigned_classes = []
    if hasattr(user, 'teacher_profile'):
        assigned_classes = SchoolClass.objects.filter(class_subjects__teacher=user.teacher_profile).distinct()
    return render(request, "portal/ai_assistant.html", {
        "assigned_classes": assigned_classes,
        "session_id": str(user.id),  # or a real session id
    })

@csrf_exempt
@login_required
def ai_assistant_generate(request):
    """Generate questions or lesson notes via DeepSeek API"""
    from ai_assistant.services import DeepSeekService
    user = request.user
    teacher = getattr(user, 'teacher_profile', None)
    if not teacher:
        return JsonResponse({"error": "Only teachers can use the AI Assistant to generate content."}, status=400)
    data = json.loads(request.body)
    subject = data.get('subject')
    level = data.get('level')
    topic = data.get('topic')
    type_ = data.get('type')
    num_objective = int(data.get('num_objective', 10))
    num_theory = int(data.get('num_theory', 5))
    service = DeepSeekService()
    if type_ == 'QUESTION':
        result, content_id = service.generate_questions(teacher, subject, level, topic, num_objective, num_theory)
    else:
        result, content_id = service.generate_lesson_note(teacher, subject, level, topic)
    return JsonResponse({"result": result, "content_id": content_id})

@csrf_exempt
@login_required
def ai_assistant_chat(request):
    """Chatbot endpoint for AI assistant (DeepSeek)"""
    from ai_assistant.services import DeepSeekService
    user = request.user
    teacher = getattr(user, 'teacher_profile', None)
    data = json.loads(request.body)
    session_id = data.get('session_id')
    message = data.get('message')
    service = DeepSeekService()
    response = service.chat(teacher, session_id, message)
    return JsonResponse({"response": response})

@login_required
def ai_assistant_download(request, content_id):
    """Download generated content as Word file"""
    # ... file generation logic ...
    return FileResponse(io.BytesIO(b"Demo Word file"), as_attachment=True, filename="generated.docx")

@csrf_exempt
@login_required
def ai_assistant_publish_exam(request):
    """Publish generated questions as CBT exam"""
    # ... CBT publishing logic ...
    return JsonResponse({"status": "success", "message": "CBT published!"})


# ========================================
# Signature Upload Endpoints
# ========================================

@login_required
@require_POST
def upload_teacher_signature(request):
    """AJAX endpoint for teachers to upload their signature"""
    user = request.user
    
    if user.role != User.Role.TEACHER:
        return JsonResponse({'error': 'Only teachers can upload teacher signatures'}, status=403)
    
    try:
        teacher_profile = TeacherProfile.objects.get(user=user)
    except TeacherProfile.DoesNotExist:
        return JsonResponse({'error': 'Teacher profile not found'}, status=404)
    
    if 'signature' not in request.FILES:
        return JsonResponse({'error': 'No signature file provided'}, status=400)
    
    signature_file = request.FILES['signature']
    
    # Validate file type
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif']
    if signature_file.content_type not in allowed_types:
        return JsonResponse({'error': 'Invalid file type. Please upload PNG, JPG, or GIF.'}, status=400)
    
    # Validate file size (max 2MB)
    if signature_file.size > 2 * 1024 * 1024:
        return JsonResponse({'error': 'File too large. Maximum size is 2MB.'}, status=400)
    
    # Save signature
    teacher_profile.signature = signature_file
    teacher_profile.save()
    
    return JsonResponse({
        'success': True,
        'message': 'Signature uploaded successfully',
        'signature_url': teacher_profile.signature.url if teacher_profile.signature else None
    })


@login_required
@require_POST
def upload_school_signature(request):
    """AJAX endpoint for school admins to upload principal signature and/or stamp"""
    user = request.user
    
    if user.role != User.Role.SCHOOL_ADMIN:
        return JsonResponse({'error': 'Only school admins can upload school signatures'}, status=403)
    
    school = user.school
    if not school:
        return JsonResponse({'error': 'School not found'}, status=404)
    
    allowed_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif']
    max_size = 2 * 1024 * 1024  # 2MB
    
    updated = []
    
    # Handle principal signature
    if 'principal_signature' in request.FILES:
        sig_file = request.FILES['principal_signature']
        if sig_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Invalid signature file type. Use PNG, JPG, or GIF.'}, status=400)
        if sig_file.size > max_size:
            return JsonResponse({'error': 'Signature file too large. Max 2MB.'}, status=400)
        school.principal_signature = sig_file
        updated.append('principal_signature')
    
    # Handle stamp
    if 'stamp' in request.FILES:
        stamp_file = request.FILES['stamp']
        if stamp_file.content_type not in allowed_types:
            return JsonResponse({'error': 'Invalid stamp file type. Use PNG, JPG, or GIF.'}, status=400)
        if stamp_file.size > max_size:
            return JsonResponse({'error': 'Stamp file too large. Max 2MB.'}, status=400)
        school.stamp = stamp_file
        updated.append('stamp')
    
    if not updated:
        return JsonResponse({'error': 'No files provided'}, status=400)
    
    school.save()
    
    return JsonResponse({
        'success': True,
        'message': f'Updated: {", ".join(updated)}',
        'principal_signature_url': school.principal_signature.url if school.principal_signature else None,
        'stamp_url': school.stamp.url if school.stamp else None
    })


@login_required
@require_GET
def get_signature_status(request):
    """Get current signature status for the logged-in user"""
    user = request.user
    
    if user.role == User.Role.TEACHER:
        try:
            teacher_profile = TeacherProfile.objects.get(user=user)
            return JsonResponse({
                'success': True,
                'has_signature': bool(teacher_profile.signature),
                'signature_url': teacher_profile.signature.url if teacher_profile.signature else None
            })
        except TeacherProfile.DoesNotExist:
            return JsonResponse({'success': False, 'has_signature': False})
    
    elif user.role == User.Role.SCHOOL_ADMIN:
        school = user.school
        if school:
            return JsonResponse({
                'success': True,
                'has_principal_signature': bool(school.principal_signature),
                'has_stamp': bool(school.stamp),
                'principal_signature_url': school.principal_signature.url if school.principal_signature else None,
                'stamp_url': school.stamp.url if school.stamp else None
            })
        return JsonResponse({'success': False})
    
    return JsonResponse({'error': 'Invalid user role'}, status=403)