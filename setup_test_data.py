#!/usr/bin/env python
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
from schools.models import School, AcademicSession
from teachers.models import TeacherProfile
from academics.models import SchoolClass, Subject, ClassSubject
from students.models import Student

# Get or create test school
school, _ = School.objects.get_or_create(name="Test School")

# Create Form Teacher
try:
    form_teacher_user = User.objects.get(username='form_teacher')
except User.DoesNotExist:
    form_teacher_user = User(
        username='form_teacher',
        role='TEACHER',
        school=school,
    )
    form_teacher_user.set_password('password123')
    form_teacher_user.save()

form_teacher, _ = TeacherProfile.objects.get_or_create(
    user=form_teacher_user,
    defaults={'school': school, 'staff_id': 'FT001', 'phone': '1111111111'}
)

# Create Subject Teachers
teachers_data = [
    ('teacher_math', 'Mathematics', 'T002'),
    ('teacher_eng', 'English', 'T003'),
    ('teacher_sci', 'Science', 'T004'),
]

teachers = {}
for username, subject_name, staff_id in teachers_data:
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        user = User(
            username=username,
            role='TEACHER',
            school=school,
        )
        user.set_password('password123')
        user.save()
    
    teacher, _ = TeacherProfile.objects.get_or_create(
        user=user,
        defaults={'school': school, 'staff_id': staff_id, 'phone': '2222222222'}
    )
    teachers[subject_name] = teacher

# Create class and assign form teacher
school_class, _ = SchoolClass.objects.get_or_create(
    school=school,
    name='JSS1',
    defaults={'form_teacher': form_teacher, 'is_active': True}
)

# Create subjects and assign teachers
subjects = {}
for username, subject_name, _ in teachers_data:
    subject, _ = Subject.objects.get_or_create(
        school=school,
        name=subject_name,
        defaults={'code': subject_name[:3]}
    )
    subjects[subject_name] = subject
    
    # Assign subject teacher to class
    ClassSubject.objects.get_or_create(
        school_class=school_class,
        subject=subject,
        defaults={'teacher': teachers[subject_name]}
    )

# Create academic session
session, _ = AcademicSession.objects.get_or_create(
    school=school,
    name='2024/2025',
    defaults={'is_active': True}
)

# Create students
students = []
for i in range(3):
    student, _ = Student.objects.get_or_create(
        school=school,
        school_class=school_class,
        admission_number=f'ADM{i+1:03d}',
        defaults={
            'first_name': f'Student{i+1}',
            'last_name': f'Last{i+1}',
            'is_active': True
        }
    )
    students.append(student)

print("Test Data Created!")
print(f"School: {school.name}")
print(f"Form Teacher: {form_teacher_user.username} (password: password123)")
print(f"Class: {school_class.name}")
print(f"\nSubjects & Teachers:")
for subj_name, teacher in teachers.items():
    print(f"  - {subj_name}: {teacher.user.username} (password: password123)")
print(f"\nStudents: {len(students)}")
print(f"Session: {session.name}")
print("\n Test Workflow:")
print("1. Login as each subject teacher and enter scores for their subject")
print("2. Login as form_teacher to publish final combined results")
