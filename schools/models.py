from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone


class Scheme(models.Model):
    """
    Global subscription scheme (not tied to any school)
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.PositiveIntegerField()

    class Meta:
        ordering = ["price"]

    def clean(self):
        if self.duration_months <= 0:
            raise ValidationError("Duration must be greater than zero.")

    def __str__(self) -> str:
        return self.name


class School(models.Model):
    """
    Root entity. Every other domain object must belong to a School.
    """
    name = models.CharField(max_length=255, unique=True)
    address = models.TextField()
    motto = models.CharField(max_length=255, blank=True, null=True)
    logo = models.ImageField(upload_to="school_logos/", blank=True, null=True)
    principal_signature = models.ImageField(upload_to="school_signatures/", blank=True, null=True, help_text="Principal's signature")
    stamp = models.ImageField(upload_to="school_stamps/", blank=True, null=True, help_text="School Official Stamp")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class SchoolSubscription(models.Model):
    """
    Tracks subscription lifecycle per school
    """
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="subscriptions"
    )
    scheme = models.ForeignKey(
        Scheme,
        on_delete=models.PROTECT
    )
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gt=models.F("start_date")),
                name="subscription_end_after_start",
            )
        ]

    def clean(self):
        if self.start_date >= self.end_date:
            raise ValidationError("End date must be after start date.")

    def __str__(self) -> str:
        return f"{self.school} → {self.scheme}"


class AcademicSession(models.Model):
    """
    Academic session (e.g. 2024/2025)
    Enforced: only one active session per school
    """
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="academic_sessions"
    )
    name = models.CharField(max_length=20)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ("school", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["school"],
                condition=Q(is_active=True),
                name="one_active_session_per_school",
            )
        ]
        ordering = ["-name"]

    def __str__(self) -> str:
        return f"{self.school} | {self.name}"


class Term(models.Model):
    """
    Academic term inside a session
    Enforced: only one active term per session
    """
    FIRST = "FIRST"
    SECOND = "SECOND"
    THIRD = "THIRD"

    TERM_CHOICES = (
        (FIRST, "First Term"),
        (SECOND, "Second Term"),
        (THIRD, "Third Term"),
    )

    session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE,
        related_name="terms"
    )
    name = models.CharField(max_length=10, choices=TERM_CHOICES)
    is_active = models.BooleanField(default=False)

    class Meta:
        unique_together = ("session", "name")
        constraints = [
            models.UniqueConstraint(
                fields=["session"],
                condition=Q(is_active=True),
                name="one_active_term_per_session",
            )
        ]

    def __str__(self) -> str:
        return f"{self.session} | {self.name}"
