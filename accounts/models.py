from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.exceptions import ValidationError


class User(AbstractUser):
    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        SCHOOL_ADMIN = "SCHOOL_ADMIN", "School Admin"
        TEACHER = "TEACHER", "Teacher"
        STUDENT = "STUDENT", "Student"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        null=True,  # allow blank for superuser creation
        blank=True,
        help_text="Select user role"
    )

    school = models.ForeignKey(
        "schools.School",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="users",
        help_text="Non-super users must belong to a school"
    )

    def clean(self):
        """
        Validation rules:
        - Skip if role is blank (used during createsuperuser)
        - Super Admin does not need a school
        - Non-super users must belong to a school
        """
        if not self.role:
            return  # blank role allowed during superuser creation

        if self.role != self.Role.SUPER_ADMIN and not self.school:
            raise ValidationError({
                "__all__": "Non-super users must belong to a school."
            })

    def save(self, *args, **kwargs):
        """
        Save the user.
        Skip validation if 'skip_clean=True' is passed (useful for programmatic updates)
        """
        skip_clean = kwargs.pop("skip_clean", False)
        if not skip_clean:
            self.full_clean()
        super().save(*args, **kwargs)
