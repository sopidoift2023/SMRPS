from django.contrib import admin
from .models import School, Scheme, SchoolSubscription, AcademicSession, Term

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ("name", "get_is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)

    def get_is_active(self, obj):
        return obj.is_active
    get_is_active.short_description = "Active"

@admin.register(Scheme)
class SchemeAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_months")
    search_fields = ("name",)

@admin.register(SchoolSubscription)
class SchoolSubscriptionAdmin(admin.ModelAdmin):
    list_display = ("get_school", "get_scheme", "start_date", "end_date", "is_active")
    search_fields = ("school__name", "scheme__name")
    autocomplete_fields = ("school", "scheme")
    list_filter = ("is_active",)

    def get_school(self, obj):
        return obj.school.name
    get_school.short_description = "School"

    def get_scheme(self, obj):
        return obj.scheme.name
    get_scheme.short_description = "Scheme"

@admin.register(AcademicSession)
class AcademicSessionAdmin(admin.ModelAdmin):
    list_display = ("name", "get_school", "is_active")
    search_fields = ("name",)
    autocomplete_fields = ("school",)

    def get_school(self, obj):
        return obj.school.name
    get_school.short_description = "School"

@admin.register(Term)
class TermAdmin(admin.ModelAdmin):
    list_display = ("name", "get_session", "is_active")
    search_fields = ("name",)
    autocomplete_fields = ("session",)

    def get_session(self, obj):
        return obj.session.name
    get_session.short_description = "Session"
