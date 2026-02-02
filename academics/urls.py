from django.urls import path
from . import views

urlpatterns = [
    path('cbt/add/', views.teacher_add_cbt_question, name='teacher_add_cbt_question'),
    path('cbt/start/<int:subject_id>/', views.cbt_start, name='cbt_start'),
    path('cbt/result/<int:session_id>/', views.cbt_result, name='cbt_result'),
    path('cbt/generate/<int:class_id>/<int:subject_id>/', views.teacher_generate_cbt_questions, name='teacher_generate_cbt_questions'),
    path('cbt/review/<int:class_id>/<int:subject_id>/', views.teacher_review_cbt_questions, name='teacher_review_cbt_questions'),
    path('cbt/edit/<int:question_id>/', views.teacher_edit_cbt_question, name='teacher_edit_cbt_question'),
    path('cbt/delete/<int:question_id>/', views.teacher_delete_cbt_question, name='teacher_delete_cbt_question'),
]
