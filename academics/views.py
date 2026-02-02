
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.http import HttpResponseForbidden
from .models import CBTQuestion, CBTSession, CBTResponse
from students.models import Student
from academics.models import SchoolClass, Subject
from ai_assistant.services import generate_cbt_questions

@login_required
@csrf_exempt
def teacher_add_cbt_question(request):
	teacher = request.user.teacherprofile
	# Use the same logic as teacher_result_entry for assigned classes/subjects
	from .models import ClassSubject
	assigned_classsubjects = ClassSubject.objects.filter(teacher=teacher).select_related('school_class', 'subject')
	classes = []
	subjects = []
	options = []
	for cs in assigned_classsubjects:
		if cs.school_class not in classes:
			classes.append(cs.school_class)
		if cs.subject not in subjects:
			subjects.append(cs.subject)
		options.append({
			'class_id': cs.school_class.id,
			'subject_id': cs.subject.id,
			'class_name': cs.school_class.name,
			'subject_name': cs.subject.name
		})
	# Determine selected class/subject
	class_id = request.GET.get('class_id') or request.POST.get('class_id')
	subject_id = request.GET.get('subject_id') or request.POST.get('subject_id')
	school_class = None
	subject = None
	if class_id and subject_id:
		school_class = get_object_or_404(SchoolClass, id=class_id)
		subject = get_object_or_404(Subject, id=subject_id)
	elif len(options) == 1:
		# Only one assignment, pre-select
		school_class = assignments[0].school_class
		subject = assignments[0].subject
		class_id = school_class.id
		subject_id = subject.id
	if request.method == 'POST' and school_class and subject:
		CBTQuestion.objects.create(
			school=school_class.school,
			school_class=school_class,
			subject=subject,
			teacher=teacher,
			text=request.POST['text'],
			option_a=request.POST['option_a'],
			option_b=request.POST['option_b'],
			option_c=request.POST['option_c'],
			option_d=request.POST['option_d'],
			correct_option=request.POST['correct_option']
		)
		return redirect('teacher_review_cbt_questions', class_id=school_class.id, subject_id=subject.id)
	return render(request, 'academics/cbt_add.html', {
		'school_class': school_class,
		'subject': subject,
		'options': options,
		'selected_class_id': class_id,
		'selected_subject_id': subject_id,
	})


# Teacher edit CBT question
@login_required
def teacher_edit_cbt_question(request, question_id):
		question = get_object_or_404(CBTQuestion, id=question_id, teacher=request.user.teacherprofile)
		if request.method == 'POST':
			question.text = request.POST.get('text', question.text)
			question.option_a = request.POST.get('option_a', question.option_a)
			question.option_b = request.POST.get('option_b', question.option_b)
			question.option_c = request.POST.get('option_c', question.option_c)
			question.option_d = request.POST.get('option_d', question.option_d)
			question.correct_option = request.POST.get('correct_option', question.correct_option)
			question.save()
			return redirect('teacher_review_cbt_questions', class_id=question.school_class.id, subject_id=question.subject.id)
		return render(request, 'academics/cbt_edit.html', {'question': question})

# Teacher delete CBT question
@login_required
def teacher_delete_cbt_question(request, question_id):
	question = get_object_or_404(CBTQuestion, id=question_id, teacher=request.user.teacherprofile)
	class_id = question.school_class.id
	subject_id = question.subject.id
	if request.method == 'POST':
		question.delete()
		return redirect('teacher_review_cbt_questions', class_id=class_id, subject_id=subject_id)
	return render(request, 'academics/cbt_delete_confirm.html', {'question': question})


# Student starts a CBT session (only published questions)
@login_required
def cbt_start(request, subject_id):
	student = get_object_or_404(Student, user=request.user)
	subject = get_object_or_404(Subject, id=subject_id)
	school_class = student.school_class
	session, created = CBTSession.objects.get_or_create(
		student=student, school_class=school_class, subject=subject, completed_at=None
	)
	questions = CBTQuestion.objects.filter(school_class=school_class, subject=subject, is_published=True)
	if request.method == 'POST':
		for q in questions:
			selected = request.POST.get(f'question_{q.id}')
			if selected:
				CBTResponse.objects.update_or_create(
					session=session, question=q,
					defaults={
						'selected_option': selected,
						'is_correct': selected == q.correct_option
					}
				)
		total = questions.count()
		correct = CBTResponse.objects.filter(session=session, is_correct=True).count()
		session.score = (correct / total) * 100 if total > 0 else 0
		session.completed_at = timezone.now()
		session.save()

		# Auto-score entry for test/exam CBTs
		from .models import CBTExam, StudentResult
		exam = CBTExam.objects.filter(school_class=school_class, subject=subject, is_published=True).order_by('-created_at').first()
		if exam and exam.cbt_type in ['first_test', 'second_test', 'exam']:
			# Get current academic session and term
			from schools.models import AcademicSession, Term
			academic_session = AcademicSession.objects.filter(school=school_class.school, is_active=True).first()
			term_obj = Term.objects.filter(session=academic_session, is_active=True).first()
			term = term_obj.name if term_obj else 'First'
			# Find or create StudentResult
			result, _ = StudentResult.objects.get_or_create(
				student=student,
				school_class=school_class,
				subject=subject,
				academic_session=academic_session,
				term=term
			)
			# Map CBT score to correct field
			# Scale score to marks
			if exam.cbt_type == 'first_test':
				score_val = int(round((correct / total) * 20)) if total > 0 else 0
				result.test1 = score_val
			elif exam.cbt_type == 'second_test':
				score_val = int(round((correct / total) * 20)) if total > 0 else 0
				result.test2 = score_val
			elif exam.cbt_type == 'exam':
				score_val = int(round((correct / total) * 60)) if total > 0 else 0
				result.exam = score_val
			# Recalculate total and grade
			result.total = (result.test1 or 0) + (result.test2 or 0) + (result.exam or 0)
			result.grade = result.calculate_grade()
			result.remark = result.calculate_remark()
			result.save()

		return redirect('cbt_result', session_id=session.id)
	responses = {r.question_id: r.selected_option for r in session.responses.all()}
	from .models import CBTExam
	# Always fetch the latest published exam after possible update
	exam = CBTExam.objects.filter(school_class=school_class, subject=subject, is_published=True).order_by('-created_at').first()
	duration = exam.duration if exam else 30
	return render(request, 'academics/cbt_start.html', {
		'questions': questions,
		'session': session,
		'responses': responses,
		'duration': duration,
	})

# Teacher review and publish CBT questions
@login_required
def teacher_review_cbt_questions(request, class_id, subject_id):
	school_class = get_object_or_404(SchoolClass, id=class_id)
	subject = get_object_or_404(Subject, id=subject_id)
	teacher = request.user.teacherprofile
	# Only allow if teacher is assigned to this class/subject
	from .models import ClassSubject
	if not ClassSubject.objects.filter(school_class=school_class, subject=subject, teacher=teacher).exists():
		return HttpResponseForbidden("You are not assigned to this class/subject.")
	questions = CBTQuestion.objects.filter(school_class=school_class, subject=subject, teacher=teacher)
	from .models import CBTExam
	exam, _ = CBTExam.objects.get_or_create(school=school_class.school, school_class=school_class, subject=subject)
	if request.method == 'POST':
		# Set CBT type and duration
		cbt_type = request.POST.get('cbt_type', 'practice')
		duration = int(request.POST.get('duration', 30))
		exam.cbt_type = cbt_type
		exam.duration = duration
		# Depublish/lock logic
		if 'depublish_exam' in request.POST:
			exam.is_published = False
		else:
			exam.is_published = 'publish_exam' in request.POST
		exam.save()
		# Publish selected questions
		ids = request.POST.getlist('publish')
		CBTQuestion.objects.filter(id__in=ids, teacher=teacher).update(is_published=True)
		# Optionally, unpublish others
		if 'unpublish_others' in request.POST:
			CBTQuestion.objects.filter(school_class=school_class, subject=subject, teacher=teacher).exclude(id__in=ids).update(is_published=False)
		return redirect('teacher_review_cbt_questions', class_id=class_id, subject_id=subject_id)
	return render(request, 'academics/cbt_review.html', {
		'school_class': school_class,
		'subject': subject,
		'questions': questions,
		'exam': exam,
	})

# Student views CBT result
@login_required
def cbt_result(request, session_id):
	session = get_object_or_404(CBTSession, id=session_id, student__user=request.user)
	responses = list(session.responses.select_related('question'))
	total_questions = len(responses)
	correct_count = sum(1 for r in responses if r.is_correct)
	incorrect_count = total_questions - correct_count
	return render(request, 'academics/cbt_result.html', {
		'session': session,
		'responses': responses,
		'total_questions': total_questions,
		'correct_count': correct_count,
		'incorrect_count': incorrect_count,
	})

# Teacher generates CBT questions using AI assistant
@login_required
def teacher_generate_cbt_questions(request, class_id=None, subject_id=None):
	teacher = request.user.teacherprofile
	from .models import ClassSubject
	assigned_classsubjects = ClassSubject.objects.filter(teacher=teacher).select_related('school_class', 'subject')
	classes = []
	subjects = []
	options = []
	for cs in assigned_classsubjects:
		if cs.school_class not in classes:
			classes.append(cs.school_class)
		if cs.subject not in subjects:
			subjects.append(cs.subject)
		options.append({
			'class_id': cs.school_class.id,
			'subject_id': cs.subject.id,
			'class_name': cs.school_class.name,
			'subject_name': cs.subject.name
		})
	# Determine selected class/subject
	class_id = class_id or request.GET.get('class_id') or request.POST.get('class_id')
	subject_id = subject_id or request.GET.get('subject_id') or request.POST.get('subject_id')
	school_class = None
	subject = None
	if class_id and subject_id:
		school_class = get_object_or_404(SchoolClass, id=class_id)
		subject = get_object_or_404(Subject, id=subject_id)
	elif len(options) == 1:
		school_class = assignments[0].school_class
		subject = assignments[0].subject
		class_id = school_class.id
		subject_id = subject.id
	if request.method == 'POST' and school_class and subject:
		num_questions = int(request.POST.get('num_questions', 10))
		questions = generate_cbt_questions(school_class, subject, num_questions)
		for q in questions:
			CBTQuestion.objects.create(
				school=school_class.school,
				school_class=school_class,
				subject=subject,
				teacher=teacher,
				text=q['text'],
				option_a=q['option_a'],
				option_b=q['option_b'],
				option_c=q['option_c'],
				option_d=q['option_d'],
				correct_option=q['correct_option']
			)
		return render(request, 'academics/cbt_generate_done.html', {'school_class': school_class, 'subject': subject})
	return render(request, 'academics/cbt_generate.html', {
		'school_class': school_class,
		'subject': subject,
		'options': options,
		'selected_class_id': class_id,
		'selected_subject_id': subject_id,
	})

# Create your views here.
