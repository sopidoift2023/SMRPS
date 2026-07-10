# CBT System - Complete Technical Reference

## System Architecture Overview

```
TEACHER WORKFLOW                    STUDENT WORKFLOW
└─ Dashboard Modal                  └─ Student Dashboard
   ├─ Select Class                     ├─ View Published Exams
   ├─ Select Subject                   ├─ Click "Start Exam"
   ├─ View/Add Questions               ├─ Timer Starts (duration minutes)
   ├─ Set Exam Type                    ├─ Answer Questions (A/B/C/D)
   ├─ Set Duration                     ├─ Auto-Submit on Timeout
   └─ Publish Exam                     ├─ View Results
                                       └─ Score Auto-Registered (if not practice)
```

---

## 1. Database Schema

### CBTExam Model
**Purpose:** Represents a published exam for a specific class/subject

```
CBTExam
├─ school (FK → School)
├─ school_class (FK → SchoolClass)
├─ subject (FK → Subject)
├─ duration (PositiveInt) [minutes]
├─ is_published (Boolean) [only published exams shown to students]
├─ cbt_type (CharField) [practice|first_test|second_test|exam]
└─ created_at (DateTime)

UNIQUE CONSTRAINT: (school_class, subject, cbt_type)
└─ Prevents multiple exams of same type for same class/subject
```

**Score Registration Rules by cbt_type:**
| Type | Destination | Scale | Retake Allowed |
|------|-------------|-------|---|
| practice | None (display only) | N/A | Yes |
| first_test | StudentResult.test1 | 0-20 | No |
| second_test | StudentResult.test2 | 0-20 | No |
| exam | StudentResult.exam | 0-60 | No |

### CBTQuestion Model
**Purpose:** Individual multiple-choice questions

```
CBTQuestion
├─ school (FK → School)
├─ school_class (FK → SchoolClass)
├─ subject (FK → Subject)
├─ teacher (FK → TeacherProfile, nullable)
├─ text (TextField) [question content]
├─ option_a, option_b, option_c, option_d (CharField)
├─ correct_option (CharField) [A|B|C|D]
├─ is_published (Boolean) [only published questions shown]
└─ created_at (DateTime)

INDEXES:
├─ (school_class, subject, is_published)
└─ (school, is_published)
```

### CBTSession Model
**Purpose:** Student exam attempt/session

```
CBTSession
├─ student (FK → Student)
├─ school_class (FK → SchoolClass)
├─ subject (FK → Subject)
├─ started_at (DateTime) [auto-set on creation]
├─ completed_at (DateTime) [null until submission]
└─ score (Float) [0-100, percentage]

UNIQUE CONSTRAINT: (student, school_class, subject, completed_at=NULL)
└─ Only one incomplete session per student per subject
└─ Completed sessions don't interfere with new attempts

INDEXES:
├─ (student, completed_at)
└─ (school_class, subject, completed_at)
```

### CBTResponse Model
**Purpose:** Student's answer to a specific question

```
CBTResponse
├─ session (FK → CBTSession)
├─ question (FK → CBTQuestion)
├─ selected_option (CharField) [A|B|C|D]
└─ is_correct (Boolean) [True if selected == question.correct_option]

UNIQUE CONSTRAINT: (session, question)
└─ One response per question per session

INDEX:
└─ (session, is_correct) [for quick score calculation]
```

---

## 2. View Layer - Request Handlers

### URL Routing (academics/urls.py)

```python
path('cbt/review/<int:class_id>/<int:subject_id>/', 
     teacher_review_cbt_questions)
# → Teacher sees/creates/edits questions for class/subject

path('cbt/add/', teacher_add_cbt_question)
# → Teacher adds single question

path('cbt/edit/<int:question_id>/', teacher_edit_cbt_question)
# → Teacher edits existing question

path('cbt/delete/<int:question_id>/', teacher_delete_cbt_question)
# → Teacher deletes question

path('cbt/generate/<int:class_id>/<int:subject_id>/', 
     teacher_generate_cbt_questions)
# → AI-assisted question generation

path('cbt/start/<int:subject_id>/', cbt_start)
# → Student takes exam

path('cbt/result/<int:session_id>/', cbt_result)
# → Display exam results

path('api/teacher/classes/', get_teacher_assigned_classes)
# → API: Get teacher's assigned classes (for modal)
```

### cbt_start() View - Main Exam Interface

**Flow:**
1. Verify student profile exists
2. Check published exam exists
3. Prevent retakes (if not practice)
4. Get/create exam session
5. On POST: Save responses → Calculate score → Auto-register → Redirect to results

**Key Defensive Points:**
```python
# 1. Authorization
student = get_object_or_404(Student, user=request.user)

# 2. Prevent unpublished exam access
exam = CBTExam.objects.filter(
    ..., is_published=True
).first()
if not exam:
    messages.error(request, "No published exam available")
    return redirect('student_dashboard')

# 3. Prevent non-practice retakes
existing_completed = CBTSession.objects.filter(
    student=student, ..., completed_at__isnull=False
).exists()
if existing_completed and exam.cbt_type != 'practice':
    messages.error(request, "Retakes are not allowed")
    return redirect('student_dashboard')

# 4. Auto-register score (bounded and safe)
if exam.cbt_type == 'first_test':
    score_val = int(round((correct / total) * 20)) if total > 0 else 0
    result.test1 = min(20, max(0, score_val))  # Constrain: 0 ≤ test1 ≤ 20
```

### cbt_result() View - Results Display

**Responsibilities:**
1. Authorize (only student can see their results)
2. Verify session is completed
3. Analyze responses (count correct/incorrect)
4. Detect if score was auto-registered
5. Render results page with messaging

---

## 3. Frontend - Exam Interface (cbt_start.html)

### Timer Implementation

```javascript
// Duration passed from view in minutes
const duration = {{ duration }};  // e.g., 30 (minutes)
const totalSeconds = duration * 60;  // Convert to seconds
let remainingSeconds = totalSeconds;

// Update every second
setInterval(() => {
    remainingSeconds--;
    displayMinutesSeconds(remainingSeconds);
    
    // Auto-submit when time expires
    if (remainingSeconds <= 0) {
        document.getElementById('cbtForm').submit();
    }
}, 1000);
```

**Protection:** Prevents time-limit circumvention.

### Tab Switch Detection

```javascript
// Detect when student switches tabs
document.addEventListener('blur', () => {
    let gracePeriod = 10;  // 10 seconds to return
    
    const interval = setInterval(() => {
        gracePeriod--;
        if (gracePeriod <= 0) {
            // Auto-submit if still away
            document.getElementById('cbtForm').submit();
        }
    }, 1000);
});

document.addEventListener('focus', () => {
    // Cancel timer if student returns
});
```

**Protection:** Prevents cheating via alt-tab.

### Form Structure

```html
<form method="POST" id="cbtForm">
    {% csrf_token %}
    
    {% for question in questions %}
    <div class="question">
        <h3>{{ question.text }}</h3>
        
        <label>
            <input type="radio" name="question_{{ question.id }}" value="A">
            {{ question.option_a }}
        </label>
        <!-- ... B, C, D options ... -->
    </div>
    {% endfor %}
    
    <button type="submit" onclick="return confirm('Submit exam?')">
        Submit Exam
    </button>
</form>
```

---

## 4. Score Calculation & Auto-Registration

### Score Calculation Logic

```python
# Count correct responses
total_questions = questions.count()
correct_responses = CBTResponse.objects.filter(
    session=session, 
    is_correct=True
).count()

# Calculate percentage
percentage = (correct_responses / total_questions * 100) if total_questions > 0 else 0
session.score = percentage
session.save()
```

### Score Conversion & Registration

| CBT Type | Conversion | Database Field | Example |
|----------|-----------|---|---|
| first_test | `percentage × 20 / 100` | StudentResult.test1 | 85% → 17 |
| second_test | `percentage × 20 / 100` | StudentResult.test2 | 75% → 15 |
| exam | `percentage × 60 / 100` | StudentResult.exam | 90% → 54 |
| practice | None | (not registered) | N/A |

### Implementation

```python
# Defensive: Handle zero questions
if exam.cbt_type == 'first_test' and total > 0:
    score_val = int(round((correct / total) * 20))
    result.test1 = min(20, max(0, score_val))  # Constrain to 0-20

# Recalculate total and grade
result.total = (result.test1 or 0) + (result.test2 or 0) + (result.exam or 0)
result.grade = result.calculate_grade()
result.remark = result.calculate_remark()
result.save()
```

---

## 5. Teacher Workflow - Setting Up Exams

### Step 1: Access Modal (portal/dashboard_teacher.html)

```html
<button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#cbtModal">
    Generate Questions
</button>

<div class="modal" id="cbtModal">
    <select id="cbtClassSelect" onchange="loadSubjects()">
        <option value="">Select Class</option>
        <!-- Populated by API -->
    </select>
    
    <select id="cbtSubjectSelect">
        <option value="">Select Subject</option>
        <!-- Populated by loadSubjects() -->
    </select>
    
    <button onclick="handleContinueClick()" class="btn btn-primary">
        Continue
    </button>
</div>
```

**Step 1 Defensive Measures:**
- API validation on server (authorization check)
- JavaScript null checks before enabling button
- Dependent dropdown prevents invalid class/subject combinations

### Step 2: Teacher Review Page (academics/cbt_review.html)

Teacher sees:
- List of existing questions (if any)
- "Add New Question" button
- "Generate with AI" button
- Exam configuration (duration, type)
- Publish button

### Step 3: Create Questions

**Option A: Manual Entry**
1. Click "Add New Question"
2. Fill in question text, 4 options, correct answer
3. Save (validates in clean())
4. Question unpublished by default

**Option B: AI Generation**
1. Click "Generate with AI"
2. Specify topic, level (easy/medium/hard), count
3. AI generates questions
4. Teacher reviews and edits as needed

### Step 4: Configure Exam

1. Set duration (minutes)
2. Set exam type:
   - **practice**: Score displayed but not recorded
   - **first_test**: Score → test1 field
   - **second_test**: Score → test2 field
   - **exam**: Score → exam field
3. Publish exam

**Publish Requirements:**
- ✅ At least 1 question
- ✅ All questions published
- ✅ Duration set
- ✅ CBT type selected

---

## 6. Student Workflow - Taking Exam

### Step 1: Dashboard View

Student sees published exams for their class/subjects.

```python
# View renders:
published_exams = CBTExam.objects.filter(
    school_class=student.school_class,
    is_published=True
)
```

### Step 2: Click "Start Exam"

1. cbt_start view checks:
   - ✅ Published exam exists
   - ✅ No completed session (unless practice)
   - ✅ Questions available
2. Creates new CBTSession
3. Renders exam interface with timer

### Step 3: Answer Questions

- JavaScript prevents unintended form submission
- Timer displays remaining time
- Tab switch detection active

### Step 4: Submit (Manual or Auto)

**Manual Submission:**
- Student clicks "Submit" button
- Confirmation dialog

**Automatic Submission:**
- Timer reaches 0:00
- Student's tab loses focus for >10 seconds
- Auto-submit without confirmation

### Step 5: Score Calculation & Registration

```python
# Calculate percentage
correct = count of is_correct=True responses
percentage = (correct / total) * 100

# Register to StudentResult (if not practice)
if exam.cbt_type == 'first_test':
    result.test1 = int(round(percentage * 20 / 100))
    # ... also updates total and grade ...
    result.save()

# Redirect to results page
redirect('cbt_result', session_id=session.id)
```

### Step 6: View Results

- Displays percentage, correct/incorrect counts
- Shows each question with student's answer vs correct answer
- **For practice exams:** "This was a practice exam. Score not recorded."
- **For test/exam types:** "Your exam score has been recorded and will be reflected in your academic results."

---

## 7. Error Handling & Edge Cases

### Edge Case: Zero Questions
```python
if total_questions == 0:
    percentage = 0  # Not an error, just 0%
    session.score = 0
```

### Edge Case: No Active Academic Session
```python
academic_session = AcademicSession.objects.filter(
    school=school_class.school,
    is_active=True
).first()

if not academic_session:
    # Skip auto-registration, log warning
    print(f"Warning: No active academic session for {school}")
else:
    # Proceed with registration
```

### Edge Case: Multiple Completed Sessions (Should Not Happen)
```python
# Unique constraint prevents this:
UniqueConstraint(
    fields=['student', 'school_class', 'subject'],
    condition=models.Q(completed_at__isnull=True)
)
# Ensures only ONE incomplete session per student per subject
```

### Edge Case: Browser Closes During Exam
```python
# CBTSession has completed_at=NULL
# Student can restart from where they left off
# OR start fresh (depending on implementation)
```

---

## 8. Monitoring & Debugging

### Key Queries for Monitoring

```python
# Find exams with few/no questions
CBTExam.objects.filter(
    is_published=True,
    cbtquestion=None  # No questions
)

# Find sessions not auto-registered
CBTSession.objects.filter(
    completed_at__isnull=False,
    cbtexam__cbt_type__in=['first_test', 'exam']
).exclude(
    cbtresponse__isnull=False  # Has responses but no StudentResult?
)

# Find students who took exam twice (error)
from django.db.models import Count
CBTSession.objects.values(
    'student', 'school_class', 'subject'
).annotate(
    attempt_count=Count('id')
).filter(
    attempt_count__gt=1,
    completed_at__isnull=False
)
```

### Logging Points

```python
# Log score registration attempts
print(f"Auto-registering {exam.cbt_type} for {student}: {score_val} points")

# Log retake prevention
print(f"Retake prevented for {student} on {subject}")

# Log auto-submit events
print(f"Auto-submit triggered for {student}: timeout={timeout_flag}")
```

---

## 9. Performance Considerations

### Database Query Optimization

```python
# ❌ N+1 queries:
for session in CBTSession.objects.all():
    exam = CBTExam.objects.get(...)  # Query in loop!

# ✅ Optimized with select_related:
sessions = CBTSession.objects.select_related(
    'student__school_class',
    'subject'
).all()

# ✅ Optimized with prefetch_related:
sessions = CBTSession.objects.prefetch_related(
    'responses__question'
).all()
```

### Index Usage

```python
# These queries use indexes efficiently:
CBTQuestion.objects.filter(
    school_class=class,
    subject=subject,
    is_published=True
)  # Uses index: (school_class, subject, is_published)

CBTSession.objects.filter(
    student=student,
    completed_at__isnull=False
)  # Uses index: (student, completed_at)
```

---

## 10. Security Considerations

### Authorization Checks

```python
# ✅ Always verify user owns the resource:
session = get_object_or_404(CBTSession, id=session_id, student__user=request.user)
# This rejects access if session doesn't belong to logged-in user

# ✅ Always verify teacher assignment:
teacher = request.user.teacherprofile
assigned_classes = ClassSubject.objects.filter(teacher=teacher)
```

### CSRF Protection

```html
<!-- Always include CSRF token in forms -->
<form method="POST">
    {% csrf_token %}
    <!-- form fields -->
</form>
```

### Input Validation

```python
# ✅ Validate on model (clean() method)
# ✅ Validate on form
# ✅ Validate on view (defensive check)

if not isinstance(question_id, int) or question_id <= 0:
    return JsonResponse({'error': 'Invalid question_id'}, status=400)
```

---

## 11. Deployment Checklist

- [ ] Create migration files (`makemigrations`)
- [ ] Apply migrations (`migrate`)
- [ ] Test retake prevention
- [ ] Test auto-registration with all exam types
- [ ] Test timer with various durations
- [ ] Test with zero questions
- [ ] Test with no active academic session
- [ ] Monitor first day of live usage
- [ ] Check logs for any exception errors

---

## 12. Common Commands

```bash
# Create new migration after model changes
python manage.py makemigrations academics

# Apply migrations
python manage.py migrate academics

# List all migrations
python manage.py showmigrations academics

# Roll back migration
python manage.py migrate academics 0014

# Run tests
python manage.py test academics.tests.CBTTests

# Debug specific session
from academics.models import CBTSession
s = CBTSession.objects.get(id=123)
print(f"Score: {s.score}, Correct: {s.responses.filter(is_correct=True).count()}")
```
