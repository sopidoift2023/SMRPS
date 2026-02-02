
from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from schools.models import School, AcademicSession
from teachers.models import TeacherProfile

# -------------------------
# TermResultSummary (for term summaries)
# -------------------------
class TermResultSummary(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='term_summaries')
    school_class = models.ForeignKey('academics.SchoolClass', on_delete=models.CASCADE)
    academic_session = models.ForeignKey('schools.AcademicSession', on_delete=models.CASCADE)
    term = models.CharField(max_length=10)
    total_score = models.PositiveIntegerField(default=0)
    average = models.FloatField(default=0.0)
    position = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = (
            'student', 'school_class', 'academic_session', 'term'
        )
        ordering = ['position']

    def __str__(self):
        return f"{self.student} - {self.term} ({self.average})"

# ...existing code...


# -------------------------

# CBT Exam (per subject/class, holds duration and publish state)
class CBTExam(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE)
    school_class = models.ForeignKey('academics.SchoolClass', on_delete=models.CASCADE)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    duration = models.PositiveIntegerField(default=30, help_text="Time allowed for this CBT exam (in minutes)")
    is_published = models.BooleanField(default=False, help_text="Only published exams are visible to students.")
    cbt_type = models.CharField(max_length=20, choices=[
        ("practice", "Practice"),
        ("first_test", "1st Test"),
        ("second_test", "2nd Test"),
        ("exam", "Exam")
    ], default="practice", help_text="Type of CBT: practice, test, or exam.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("school_class", "subject", "cbt_type")

    def __str__(self):
        return f"CBTExam: {self.school_class} - {self.subject} ({self.get_cbt_type_display()})"


class CBTQuestion(models.Model):
    school = models.ForeignKey('schools.School', on_delete=models.CASCADE)
    school_class = models.ForeignKey('academics.SchoolClass', on_delete=models.CASCADE)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('teachers.TeacherProfile', on_delete=models.SET_NULL, null=True)
    text = models.TextField()
    option_a = models.CharField(max_length=255)
    option_b = models.CharField(max_length=255)
    option_c = models.CharField(max_length=255)
    option_d = models.CharField(max_length=255)
    correct_option = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    is_published = models.BooleanField(default=False, help_text="Only published questions are visible to students.")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject.name} - {self.text[:40]}..."

class CBTSession(models.Model):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    school_class = models.ForeignKey('academics.SchoolClass', on_delete=models.CASCADE)
    subject = models.ForeignKey('academics.Subject', on_delete=models.CASCADE)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    score = models.FloatField(null=True, blank=True)

    def __str__(self):
        return f"Session: {self.student} - {self.subject} ({self.started_at})"

class CBTResponse(models.Model):
    session = models.ForeignKey(CBTSession, on_delete=models.CASCADE, related_name='responses')
    question = models.ForeignKey(CBTQuestion, on_delete=models.CASCADE)
    selected_option = models.CharField(max_length=1, choices=[('A','A'),('B','B'),('C','C'),('D','D')])
    is_correct = models.BooleanField()

    def __str__(self):
        return f"{self.session.student} - {self.question.subject} - QID:{self.question.id}"


# -------------------------
# School Class
# -------------------------
class SchoolClass(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="classes"
    )
    name = models.CharField(max_length=50)  # e.g., JSS1, SS3
    form_teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="form_classes",
        help_text="The form teacher who publishes final results for this class"
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.school.name} - {self.name}"


# -------------------------
# Subject
# -------------------------
class Subject(models.Model):
    school = models.ForeignKey(
        School,
        on_delete=models.CASCADE,
        related_name="subjects"
    )
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        unique_together = ("school", "name")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.school.name})"


# -------------------------
# ClassSubject (Teacher Assignment)
# -------------------------
class ClassSubject(models.Model):
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="class_subjects"
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="class_subjects"
    )
    teacher = models.ForeignKey(
        TeacherProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        unique_together = ("school_class", "subject")

    def clean(self):
        if self.teacher and self.teacher.school != self.school_class.school:
            raise ValidationError(
                "Assigned teacher must belong to the same school as the class."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.school_class} - {self.subject.name}"


# -------------------------
# Terms
# -------------------------
TERM_CHOICES = (
    ("First", "First Term"),
    ("Second", "Second Term"),
    ("Third", "Third Term"),
)


# -------------------------
# Student Result (Per Subject)
# -------------------------
class StudentResult(models.Model):
    student = models.ForeignKey(
        "students.Student",  # String reference avoids circular import
        on_delete=models.CASCADE,
        related_name="results"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE
    )
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE
    )
    term = models.CharField(
        max_length=10,
        choices=TERM_CHOICES
    )

    # CA Score fields (4 continuous assessments)
    ca1 = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Continuous Assessment 1 (0-10)"
    )
    ca2 = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Continuous Assessment 2 (0-10)"
    )
    ca3 = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Continuous Assessment 3 (0-10)"
    )
    ca4 = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(10)],
        help_text="Continuous Assessment 4 (0-10)"
    )
    exam = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(60)],
        help_text="Exam score (0-60)"
    )

    # Legacy fields (kept for backward compatibility)
    test1 = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    test2 = models.PositiveIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )

    # Computed fields
    total = models.PositiveIntegerField(default=0, editable=False)
    grade = models.CharField(max_length=1, default='F', editable=False)
    
    # Subject position and highest in class
    subject_position = models.PositiveIntegerField(null=True, blank=True)
    subject_highest = models.PositiveIntegerField(default=0)
    
    # Remark
    REMARK_CHOICES = (
        ("Excellent", "Excellent"),
        ("Very Good", "Very Good"),
        ("Good", "Good"),
        ("Pass", "Pass"),
        ("Fail", "Fail"),
    )
    remark = models.CharField(max_length=20, blank=True)

    class Meta:
        unique_together = (
            "student",
            "school_class",
            "subject",
            "academic_session",
            "term",
        )

    def save(self, *args, **kwargs):
        # Calculate total
        # Priority: CA1-4 if any are non-zero, otherwise Test1/2
        ca_total = self.ca1 + self.ca2 + self.ca3 + self.ca4
        if ca_total > 0:
            self.total = ca_total + self.exam
        else:
            self.total = self.test1 + self.test2 + self.exam
            
        self.grade = self.calculate_grade()
        self.remark = self.calculate_remark()
        super().save(*args, **kwargs)

    # Grade calculation based on the grading key
    def calculate_grade(self):
        if self.total >= 80:
            return "A"
        elif self.total >= 70:
            return "B"
        elif self.total >= 60:
            return "C"
        elif self.total >= 50:
            return "D"
        elif self.total >= 40:
            return "E"
        return "F"
    
    def calculate_remark(self):
        if self.total >= 80:
            return "Excellent"
        elif self.total >= 70:
            return "Very Good"
        elif self.total >= 60:
            return "Good"
        elif self.total >= 50:
            return "Pass"
        else:
            return "Fail"


# -------------------------
# Rating Choices for Traits
# -------------------------
RATING_CHOICES = (
    ("A", "A - Excellent"),
    ("B", "B - Very Good"),
    ("C", "C - Good"),
    ("D", "D - Pass"),
    ("E", "E - Fair"),
    ("F", "F - Fail"),
)


# -------------------------
# Student Attendance
# -------------------------
class StudentAttendance(models.Model):
    """Track student attendance per term"""
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE
    )
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    
    # Attendance counts
    times_present = models.PositiveIntegerField(default=0)
    times_school_opened = models.PositiveIntegerField(default=0)
    
    class Meta:
        unique_together = (
            "student",
            "school_class",
            "academic_session",
            "term",
        )
    
    def __str__(self):
        return f"{self.student} - {self.term} ({self.times_present}/{self.times_school_opened})"
    
    @property
    def attendance_percentage(self):
        if self.times_school_opened > 0:
            return round((self.times_present / self.times_school_opened) * 100, 1)
        return 0


# -------------------------
# Student Affective Traits
# -------------------------
class StudentAffectiveTraits(models.Model):
    """
    Affective traits assessment for student behavior
    Form teacher rates each trait from A to F
    """
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="affective_traits"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE
    )
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    
    # 9 Affective Traits
    punctuality = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    mental_alertness = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    respect = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    neatness = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    honesty = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    politeness = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    relationship_with_peers = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    willingness_to_learn = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    spirit_of_teamwork = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    
    class Meta:
        unique_together = (
            "student",
            "school_class",
            "academic_session",
            "term",
        )
        verbose_name_plural = "Student Affective Traits"
    
    def __str__(self):
        return f"{self.student} - Affective Traits ({self.term})"


# -------------------------
# Student Psychomotor Traits
# -------------------------
class StudentPsychomotorTraits(models.Model):
    """
    Psychomotor traits assessment for student skills
    Form teacher rates each trait from A to F
    """
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="psychomotor_traits"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE
    )
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    
    # 5 Psychomotor Traits
    games_and_sports = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    verbal_skills = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    artistic_creativity = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    musical_skills = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    dance_skills = models.CharField(
        max_length=1, choices=RATING_CHOICES, default="C"
    )
    
    class Meta:
        unique_together = (
            "student",
            "school_class",
            "academic_session",
            "term",
        )
        verbose_name_plural = "Student Psychomotor Traits"
    
    def __str__(self):
        return f"{self.student} - Psychomotor Traits ({self.term})"


# -------------------------
# Student Term Report (Comments & Promotion)
# -------------------------
class StudentTermReport(models.Model):
    """
    Term report card containing teacher comments, principal comments,
    promotion status, and next term information
    """
    student = models.ForeignKey(
        "students.Student",
        on_delete=models.CASCADE,
        related_name="term_reports"
    )
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE
    )
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    
    # Class Teacher Details
    class_teacher_comment = models.TextField(blank=True)
    class_teacher_name = models.CharField(max_length=200, blank=True)
    
    # Principal Details
    principal_comment = models.TextField(blank=True)
    
    # Next Term Information
    next_term_begins = models.DateField(null=True, blank=True)
    
    # Promotion Status
    PROMOTION_CHOICES = (
        ("PROMOTED", "Promoted"),
        ("REPEATED", "Repeated"),
        ("TRIAL", "Trial Promotion"),
        ("PENDING", "Pending"),
    )
    promotion_status = models.CharField(
        max_length=20,
        choices=PROMOTION_CHOICES,
        default="PENDING"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = (
            "student",
            "school_class",
            "academic_session",
            "term",
        )
        verbose_name = "Student Term Report"
        verbose_name_plural = "Student Term Reports"
    
    def __str__(self):
        return f"{self.student} - Term Report ({self.term})"


# -------------------------
# Class Population (for term)
# -------------------------
class ClassTermInfo(models.Model):
    """
    Store class-level information for a term
    Including class population and school-opened days
    """
    school_class = models.ForeignKey(
        SchoolClass,
        on_delete=models.CASCADE,
        related_name="term_info"
    )
    academic_session = models.ForeignKey(
        AcademicSession,
        on_delete=models.CASCADE
    )
    term = models.CharField(max_length=10, choices=TERM_CHOICES)
    
    # Class info
    class_population = models.PositiveIntegerField(default=0)
    times_school_opened = models.PositiveIntegerField(default=0)
    
    # Next term date (set by admin)
    next_term_begins = models.DateField(null=True, blank=True)
    
    class Meta:
        unique_together = (
            "school_class",
            "academic_session",
            "term",
        )
    
    def __str__(self):
        return f"{self.school_class} - {self.term} ({self.academic_session})"
