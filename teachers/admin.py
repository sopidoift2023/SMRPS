from django.contrib import admin
from .models import TeacherProfile


@admin.register(TeacherProfile)
class TeacherProfileAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "school",
    )
    list_filter = (
        "school",
    )
    search_fields = (
        "user__username",
        "user__email",
    )
    autocomplete_fields = (
        "user",
        "school",
    )
