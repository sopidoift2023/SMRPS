from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from schools.models import School
from teachers.models import TeacherProfile
from academics.models import SchoolClass, ClassSubject, Subject


class TeacherAccessControlTests(TestCase):
    def setUp(self):
        self.school = School.objects.create(
            name='Test School',
            address='Main Street',
        )

        self.form_teacher_user = User.objects.create_user(
            username='formteacher',
            password='password123',
            role=User.Role.TEACHER,
            school=self.school,
        )
        self.form_teacher = TeacherProfile.objects.create(
            user=self.form_teacher_user,
            school=self.school,
            staff_id='FT-001',
            phone='08000000001',
        )

        self.other_teacher_user = User.objects.create_user(
            username='otherteacher',
            password='password123',
            role=User.Role.TEACHER,
            school=self.school,
        )
        self.other_teacher = TeacherProfile.objects.create(
            user=self.other_teacher_user,
            school=self.school,
            staff_id='OT-001',
            phone='08000000002',
        )

        self.unassigned_teacher_user = User.objects.create_user(
            username='unassignedteacher',
            password='password123',
            role=User.Role.TEACHER,
            school=self.school,
        )
        self.unassigned_teacher = TeacherProfile.objects.create(
            user=self.unassigned_teacher_user,
            school=self.school,
            staff_id='UT-001',
            phone='08000000003',
        )

        self.subject = Subject.objects.create(
            school=self.school,
            name='Mathematics',
            code='MATH',
        )
        self.school_class = SchoolClass.objects.create(
            school=self.school,
            name='JSS1',
            form_teacher=self.form_teacher,
        )
        ClassSubject.objects.create(
            school_class=self.school_class,
            subject=self.subject,
            teacher=self.other_teacher,
        )

    def test_unassigned_teacher_is_blocked_from_class_management(self):
        self.client.force_login(self.unassigned_teacher_user)
        response = self.client.get(reverse('portal:teacher_class_management', args=[self.school_class.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Access Denied')

    def test_unassigned_teacher_cannot_add_student_to_class(self):
        self.client.force_login(self.other_teacher_user)
        response = self.client.post(
            reverse('portal:teacher_add_student', args=[self.school_class.id]),
            {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'admission_number': 'A-100',
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertJSONEqual(response.content, {'error': 'Only form teacher can add students to this class'})

    def test_form_teacher_can_add_student(self):
        self.client.force_login(self.form_teacher_user)
        response = self.client.post(
            reverse('portal:teacher_add_student', args=[self.school_class.id]),
            {
                'first_name': 'John',
                'last_name': 'Smith',
                'admission_number': 'A-101',
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(response.content, {'success': True, 'message': 'Student John Smith added successfully'})
