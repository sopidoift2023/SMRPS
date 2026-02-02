from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "email", "get_role", "get_school", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    list_filter = ("is_staff", "is_superuser", "is_active")
    autocomplete_fields = ("school",)

    fieldsets = BaseUserAdmin.fieldsets + (
        ("Custom fields", {"fields": ("role", "school")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Custom fields", {"fields": ("role", "school")}),
    )

    def get_role(self, obj):
        return obj.role if hasattr(obj, "role") else "N/A"
    get_role.short_description = "Role"

    def get_school(self, obj):
        return obj.school.name if obj.school else "N/A"
    get_school.short_description = "School"
