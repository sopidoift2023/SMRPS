# students/models.py

from django.db import models
from schools.models import School
from academics.models import SchoolClass
from accounts.models import User


class Student(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="student_profile"
    )
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="students"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="students"
    )

    first_name = models.CharField(max_length=50)
    last_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)

    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
    )
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='M')
    date_of_birth = models.DateField(null=True, blank=True)

    admission_number = models.CharField(
        max_length=30,
        unique=True
    )

    is_active = models.BooleanField(default=True)
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["last_name", "first_name"]

    @property
    def age(self):
        if not self.date_of_birth:
            return None
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def __str__(self):
        return f"{self.last_name} {self.first_name} ({self.admission_number})"


# Signal to create user for student
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction

@receiver(post_save, sender=Student)
def create_student_user(sender, instance, created, **kwargs):
    if created and not instance.user:
        # Check if user with admission number already exists
        username = instance.admission_number.strip()
        user = User.objects.filter(username=username).first()
        
        if not user:
            # Create new user
            user = User.objects.create_user(
                username=username,
                password=username, # Default password is admission number
                role=User.Role.STUDENT,
                school=instance.school
            )
        else:
            # If user exists but no role set (rare), set it
            if not user.role:
                user.role = User.Role.STUDENT
                user.save()
            # If school not set
            if not user.school:
                user.school = instance.school
                user.save()
                
        # Link user to student
        instance.user = user
        instance.save()
