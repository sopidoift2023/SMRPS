# students/admin.py

from django.contrib import admin
from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = (
        "admission_number",
        "last_name",
        "first_name",
        "school",
        "school_class",
        "is_active",
    )

    list_filter = ("school", "school_class", "is_active")
    search_fields = ("admission_number", "first_name", "last_name")
    ordering = ("school_class", "last_name")
