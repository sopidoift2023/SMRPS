from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    path("class/<int:class_id>/download-cumulative-zip/", views.download_class_cumulative_zip, name="download_class_cumulative_zip"),
    path("student/download-cumulative/", views.download_cumulative_result, name="download_cumulative_result"),
    path("change-password/", views.change_password, name="change_password"),
    path("", views.dashboard_redirect, name="dashboard"),
    
    # Teacher
    path("teacher/", views.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/results/", views.teacher_result_entry, name="teacher_result_entry"),
    
    # Interactive Teacher Dashboard
    path("teacher/<int:class_id>/", views.teacher_class_management, name="teacher_class_management"),
    path("teacher/<int:class_id>/add-student/", views.teacher_add_student, name="teacher_add_student"),
    path("teacher/<int:class_id>/enter-scores/", views.teacher_enter_subject_scores, name="teacher_enter_subject_scores"),
    path("teacher/<int:class_id>/save-scores/", views.teacher_save_subject_scores, name="teacher_save_subject_scores"),
    path("teacher/<int:class_id>/results/", views.teacher_generate_results, name="teacher_generate_results"),
    path("teacher/<int:class_id>/compute-results/", views.teacher_trigger_compute_results, name="teacher_trigger_compute_results"),
    path("teacher/<int:class_id>/final-results/", views.form_teacher_generate_final_results, name="form_teacher_generate_final_results"),
    
    # Form Teacher Assessment Entry
    # form_teacher_assessment_page removed as requested
    path("teacher/<int:class_id>/report-sheet/", views.teacher_result_report_sheet, name="teacher_result_report_sheet"),
    path("teacher/<int:class_id>/assessments/get/", views.get_student_assessments, name="get_student_assessments"),
    path("teacher/<int:class_id>/assessments/auto-comments/", views.generate_auto_comments, name="generate_auto_comments"),
    path("teacher/<int:class_id>/assessments/class-info/", views.save_class_term_info, name="save_class_term_info"),
    path("teacher/<int:class_id>/assessments/attendance/", views.save_student_attendance, name="save_student_attendance"),
    path("teacher/<int:class_id>/assessments/affective-traits/", views.save_student_affective_traits, name="save_student_affective_traits"),
    path("teacher/<int:class_id>/assessments/psychomotor-traits/", views.save_student_psychomotor_traits, name="save_student_psychomotor_traits"),
    path("teacher/<int:class_id>/assessments/term-reports/", views.save_student_term_reports, name="save_student_term_reports"),
    
    # PDF Download
    path("admin/<int:class_id>/results-pdf/", views.download_class_results_pdf, name="download_class_results_pdf"),
    path("admin/<int:class_id>/comprehensive-pdf/", views.download_comprehensive_result_pdf, name="download_comprehensive_result_pdf"),
    path("teacher/<int:class_id>/broadsheet-pdf/", views.download_form_teacher_broadsheet_pdf, name="download_form_teacher_broadsheet_pdf"),
    
    # Principal Comments (School Admin)
    path("admin/<int:class_id>/principal-comments/", views.save_principal_comments, name="save_principal_comments"),
    
    # AJAX Endpoints - Data Retrieval
    path("api/students/", views.get_students_by_class, name="get_students_by_class"),
    path("api/class-subjects/", views.get_class_subjects, name="get_class_subjects"),
    path("api/students-results/", views.get_students_results, name="get_students_results"),
    path("api/term-results/", views.get_term_results, name="get_term_results"),
    path("api/classes/", views.get_school_classes, name="get_school_classes"),
    path("api/sessions/", views.get_school_sessions, name="get_school_sessions"),
    
    # School Admin Management APIs
    path("api/admin/teachers/", views.list_teachers, name="list_teachers"),
    path("api/admin/teachers/create/", views.create_teacher, name="create_teacher"),
    path("api/admin/teachers/<int:teacher_id>/edit/", views.edit_teacher, name="edit_teacher"),
    path("api/admin/teachers/<int:teacher_id>/delete/", views.delete_teacher, name="delete_teacher"),
    
    path("api/admin/subjects/", views.list_subjects, name="list_subjects"),
    path("api/admin/subjects/create/", views.create_subject, name="create_subject"),
    path("api/admin/subjects/<int:subject_id>/edit/", views.edit_subject, name="edit_subject"),
    path("api/admin/subjects/<int:subject_id>/delete/", views.delete_subject, name="delete_subject"),
    
    path("api/admin/classes/", views.list_classes, name="list_classes"),
    path("api/admin/classes/create/", views.create_class, name="create_class"),
    path("api/admin/classes/<int:class_id>/edit/", views.edit_class, name="edit_class"),
    path("api/admin/classes/<int:class_id>/delete/", views.delete_class, name="delete_class"),
    
    path("api/admin/assign-teacher/", views.assign_teacher_to_class, name="assign_teacher_to_class"),
    path("api/admin/create-session/", views.create_session, name="create_session"),
    path("api/admin/add-student/", views.admin_add_student, name="admin_add_student"),
    
    # Student Management
    path("api/students/<int:student_id>/edit/", views.edit_student, name="edit_student"),
    path("api/students/<int:student_id>/delete/", views.delete_student, name="delete_student"),
    
    # AJAX Endpoints - Data Manipulation
    path("api/save-result/", views.save_student_result, name="save_student_result"),
    path("api/bulk-save/", views.bulk_save_results, name="bulk_save_results"),
    path("api/compute-results/", views.compute_class_results, name="compute_class_results"),

    # School admin
    path("admin/", views.school_admin_dashboard, name="school_admin_dashboard"),

    # Student
    path("student/", views.student_dashboard, name="student_dashboard"),

    # AI Assistant (Chatbot, Question Generator, Lesson Note)
    path("ai-assistant/", views.ai_assistant, name="ai_assistant"),
    path("ai-assistant/generate/", views.ai_assistant_generate, name="ai_assistant_generate"),
    path("ai-assistant/chat/", views.ai_assistant_chat, name="ai_assistant_chat"),
    path("ai-assistant/download/<int:content_id>/", views.ai_assistant_download, name="ai_assistant_download"),
    path("ai-assistant/publish-exam/", views.ai_assistant_publish_exam, name="ai_assistant_publish_exam"),
    
    # Signature Upload
    path("api/signature/teacher/upload/", views.upload_teacher_signature, name="upload_teacher_signature"),
    path("api/signature/school/upload/", views.upload_school_signature, name="upload_school_signature"),
    path("api/signature/status/", views.get_signature_status, name="get_signature_status"),
]