from django.db import models
from accounts.models import User
from schools.models import School

class TeacherProfile(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'TEACHER'}
    )
    school = models.ForeignKey(School, on_delete=models.CASCADE)
    staff_id = models.CharField(max_length=50, unique=True)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    phone = models.CharField(max_length=20)
    signature = models.ImageField(upload_to="teacher_signatures/", blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username
