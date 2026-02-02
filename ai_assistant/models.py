from django.db import models
from django.conf import settings
from teachers.models import TeacherProfile
from academics.models import SchoolClass
from students.models import Student

class AIContent(models.Model):
    CONTENT_TYPE_CHOICES = [
        ('QUESTION', 'Exam/Test Questions'),
        ('NOTE', 'Lesson Note'),
    ]

    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='ai_contents')
    content_type = models.CharField(max_length=20, choices=CONTENT_TYPE_CHOICES)
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    level = models.CharField(max_length=50)  # e.g., Senior WAEC, Junior WAEC
    generated_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "AI Generated Content"
        verbose_name_plural = "AI Generated Contents"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_content_type_display()} - {self.subject} ({self.topic})"

class AIConversation(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='ai_conversations')
    session_id = models.CharField(max_length=100, unique=True)
    history = models.JSONField(default=list)  # Stores the chat history for context
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Chat with {self.teacher.user.get_full_name()} - {self.session_id}"

class CBTMockExam(models.Model):
    teacher = models.ForeignKey(TeacherProfile, on_delete=models.CASCADE, related_name='mock_exams')
    school_class = models.ForeignKey(SchoolClass, on_delete=models.CASCADE, related_name='mock_exams')
    subject = models.CharField(max_length=100)
    topic = models.CharField(max_length=255)
    level = models.CharField(max_length=50)
    duration_minutes = models.PositiveIntegerField(default=30)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "CBT Mock Exam"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} ({self.topic}) - {self.school_class.name}"

class CBTQuestion(models.Model):
    QUESTION_TYPE_CHOICES = [
        ('OBJ', 'Objective'),
        ('THEORY', 'Theory/Essay'),
    ]
    exam = models.ForeignKey(CBTMockExam, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField(max_length=10, choices=QUESTION_TYPE_CHOICES)
    question_text = models.TextField()
    
    # Objective fields
    option_a = models.CharField(max_length=255, blank=True, null=True)
    option_b = models.CharField(max_length=255, blank=True, null=True)
    option_c = models.CharField(max_length=255, blank=True, null=True)
    option_d = models.CharField(max_length=255, blank=True, null=True)
    correct_option = models.CharField(max_length=1, blank=True, null=True) # A, B, C, or D

    def __str__(self):
        return f"Q: {self.question_text[:50]}"

class CBTAttempt(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='cbt_attempts')
    exam = models.ForeignKey(CBTMockExam, on_delete=models.CASCADE, related_name='attempts')
    start_time = models.DateTimeField(auto_now_add=True)
    end_time = models.DateTimeField(null=True, blank=True)
    is_submitted = models.BooleanField(default=False)
    
    objective_score = models.FloatField(default=0.0)
    theory_feedback = models.JSONField(default=dict) # Stores per-question AI feedback and scores
    total_score = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('student', 'exam') # One attempt per exam per student

    def __str__(self):
        return f"{self.student.user.get_full_name()} - {self.exam.subject}"

class CBTAnswer(models.Model):
    attempt = models.ForeignKey(CBTAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(CBTQuestion, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, blank=True, null=True) # For Objective
    theory_answer = models.TextField(blank=True, null=True) # For Theory
    
    is_correct = models.BooleanField(null=True) # Auto-filled for OBJ, AI-filled for Theory
    score = models.FloatField(default=0.0)
    ai_feedback = models.TextField(blank=True, null=True)
