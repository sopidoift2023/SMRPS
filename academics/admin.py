
from django.contrib import admin, messages
from .models import CBTQuestion, CBTSession, CBTResponse

# CBT Models Registration
@admin.register(CBTQuestion)
class CBTQuestionAdmin(admin.ModelAdmin):
    list_display = ("subject", "school_class", "teacher", "text", "created_at")
    list_filter = ("school", "school_class", "subject", "teacher")
    search_fields = ("text",)

@admin.register(CBTSession)
class CBTSessionAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "subject", "started_at", "completed_at", "score")
    list_filter = ("school_class", "subject")
    search_fields = ("student__first_name", "student__last_name")

@admin.register(CBTResponse)
class CBTResponseAdmin(admin.ModelAdmin):
    list_display = ("session", "question", "selected_option", "is_correct")
    list_filter = ("session", "question", "is_correct")
from django.contrib import admin, messages
from .models import (
    SchoolClass, Subject, ClassSubject, StudentResult,
    StudentAttendance, StudentAffectiveTraits, StudentPsychomotorTraits,
    StudentTermReport, ClassTermInfo
)
from .services import compute_term_results
from students.models import Student


@admin.register(SchoolClass)
class SchoolClassAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "is_active")
    list_filter = ("school", "is_active")
    search_fields = ("name",)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("name", "school", "code")
    list_filter = ("school",)
    search_fields = ("name", "code")


@admin.register(ClassSubject)
class ClassSubjectAdmin(admin.ModelAdmin):
    list_display = ("school_class", "subject", "teacher")
    list_filter = ("school_class",)
    autocomplete_fields = ("teacher",)


@admin.register(StudentResult)
class StudentResultAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "subject",
        "school_class",
        "academic_session",
        "term",
        "test1",
        "test2",
        "exam",
        "total",
        "grade",
    )
    
    exclude = ('ca1', 'ca2', 'ca3', 'ca4')

    list_filter = ("school_class", "academic_session", "term", "subject")
    search_fields = ("student__first_name", "student__last_name")
    actions = ["compute_results"]

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        user = request.user

        if not user.is_superuser and user.school:
            if db_field.name == "student":
                kwargs["queryset"] = Student.objects.filter(
                    school=user.school,
                    is_active=True
                )
            elif db_field.name == "school_class":
                kwargs["queryset"] = SchoolClass.objects.filter(
                    school=user.school,
                    is_active=True
                )
            elif db_field.name == "subject":
                kwargs["queryset"] = Subject.objects.filter(
                    school=user.school
                )

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def compute_results(self, request, queryset):
        if not queryset.exists():
            self.message_user(request, "No results selected.", messages.WARNING)
            return

        sample = queryset.first()

        compute_term_results(
            school_class=sample.school_class,
            academic_session=sample.academic_session,
            term=sample.term,
        )

        self.message_user(
            request,
            "Term results computed successfully.",
            messages.SUCCESS,
        )

    compute_results.short_description = "Compute Term Results"


@admin.register(StudentAttendance)
class StudentAttendanceAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "term", "times_present", "times_school_opened")
    list_filter = ("school_class", "academic_session", "term")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(StudentAffectiveTraits)
class StudentAffectiveTraitsAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "term", "punctuality", "respect", "honesty")
    list_filter = ("school_class", "academic_session", "term")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(StudentPsychomotorTraits)
class StudentPsychomotorTraitsAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "term", "games_and_sports", "verbal_skills")
    list_filter = ("school_class", "academic_session", "term")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(StudentTermReport)
class StudentTermReportAdmin(admin.ModelAdmin):
    list_display = ("student", "school_class", "term", "promotion_status", "next_term_begins")
    list_filter = ("school_class", "academic_session", "term", "promotion_status")
    search_fields = ("student__first_name", "student__last_name")


@admin.register(ClassTermInfo)
class ClassTermInfoAdmin(admin.ModelAdmin):
    list_display = ("school_class", "academic_session", "term", "class_population", "times_school_opened", "next_term_begins")
    list_filter = ("school_class", "academic_session", "term")
