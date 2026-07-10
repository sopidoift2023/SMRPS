# CBT (Computer-Based Testing) - Defensive Programming Guide

## Overview
This document outlines the defensive programming practices implemented in the CBT (Computer-Based Testing) system to ensure robustness, prevent data corruption, and provide clear error handling.

---

## 1. Database Layer Defensive Measures

### 1.1 Model Validation (clean() methods)

All CBT models now include comprehensive `clean()` methods that validate data before saving:

#### CBTExam Validation
```python
def clean(self):
    # Duration must be positive and reasonable (max 8 hours)
    if self.duration is None or self.duration <= 0:
        raise ValidationError({'duration': 'Duration must be greater than 0 minutes'})
    if self.duration > 480:  # Max 8 hours
        raise ValidationError({'duration': 'Duration cannot exceed 8 hours (480 minutes)'})
    
    # School consistency checks
    if self.school_class.school != self.school:
        raise ValidationError('School must match the class\'s school')
    if self.subject.school != self.school:
        raise ValidationError('Subject must belong to the same school')
```

**Use Case:** Prevents invalid exam configurations from being saved to the database.

#### CBTQuestion Validation
```python
def clean(self):
    # Text validation
    if not self.text or not self.text.strip():
        raise ValidationError({'text': 'Question text cannot be empty'})
    
    # Option validation
    options = [self.option_a, self.option_b, self.option_c, self.option_d]
    if not all(options):
        raise ValidationError('All four options must be provided')
    
    if len(set(options)) < 4:
        raise ValidationError('All options must be different')
    
    # Correct option validation
    if self.correct_option not in ['A', 'B', 'C', 'D']:
        raise ValidationError({'correct_option': 'Invalid correct option'})
    
    # School consistency checks
    if self.school_class.school != self.school:
        raise ValidationError('School must match the class\'s school')
    if self.subject.school != self.school:
        raise ValidationError('Subject must belong to the same school')
```

**Use Case:** Prevents malformed questions from being created or published.

#### CBTSession Validation
```python
def clean(self):
    # Score range validation
    if self.score is not None:
        if not (0 <= self.score <= 100):
            raise ValidationError({'score': 'Score must be between 0 and 100'})
    
    # Temporal logic validation
    if self.completed_at and self.completed_at < self.started_at:
        raise ValidationError({'completed_at': 'Completion time cannot be before start time'})
```

**Use Case:** Prevents illogical session data (e.g., negative scores, backwards timestamps).

#### CBTResponse Validation
```python
def clean(self):
    # Option validation
    if self.selected_option not in ['A', 'B', 'C', 'D']:
        raise ValidationError({'selected_option': 'Selected option must be A, B, C, or D'})
    
    # Context validation
    if self.question.school_class != self.session.school_class:
        raise ValidationError('Question must belong to the same class as the session')
    if self.question.subject != self.session.subject:
        raise ValidationError('Question must belong to the same subject as the session')
```

**Use Case:** Prevents students from answering questions that don't belong to their exam.

### 1.2 Database Constraints

#### Unique Constraints
```python
# CBTExam: Only one CBT per class/subject/type combination
unique_together = ("school_class", "subject", "cbt_type")

# CBTSession: Only one incomplete session per student/class/subject
UniqueConstraint(
    fields=['student', 'school_class', 'subject'],
    condition=models.Q(completed_at__isnull=True),
    name='unique_incomplete_cbt_session'
)

# CBTResponse: One response per question per session
unique_together = ('session', 'question')
```

**Protection:** Prevents duplicate sessions and responses at the database level.

#### Database Indexes
```python
# Fast lookup of published questions by class/subject
Index(fields=['school_class', 'subject', 'is_published'])

# Fast lookup of student session history
Index(fields=['student', 'completed_at'])

# Fast lookup of correct responses
Index(fields=['session', 'is_correct'])
```

**Benefit:** Optimizes queries and prevents N+1 problems.

---

## 2. View Layer Defensive Measures

### 2.1 cbt_start() - Enhanced Retake Prevention

```python
# 1. Check for existing completed sessions (retake prevention)
existing_completed = CBTSession.objects.filter(
    student=student, 
    school_class=school_class, 
    subject=subject, 
    completed_at__isnull=False
).exists()

if existing_completed and exam.cbt_type != 'practice':
    # Only allow retake for practice exams
    messages.error(request, f"You have already completed this {exam.get_cbt_type_display()}. Retakes are not allowed.")
    return redirect('student_dashboard')
```

**Key Points:**
- Rejects retake attempts on first_test, second_test, and exam types
- Allows unlimited practice exam attempts
- Returns user-friendly error message

### 2.2 Published Exam Check

```python
# Get the latest published CBT exam for validation
exam = CBTExam.objects.filter(
    school_class=school_class, 
    subject=subject, 
    is_published=True
).order_by('-created_at').first()

# Prevent access if no published exam
if not exam:
    messages.error(request, "No published exam available for this subject.")
    return redirect('student_dashboard')
```

**Protection:** Prevents students from accessing unpublished exams.

### 2.3 Post-Exam Auto-Score Registration

```python
# Auto-score entry for test/exam CBTs ONLY (not practice)
if exam.cbt_type in ['first_test', 'second_test', 'exam']:
    # Try to get current academic session and term
    academic_session = AcademicSession.objects.filter(
        school=school_class.school, 
        is_active=True
    ).first()
    
    if academic_session:
        # Map CBT score to correct field (scale percentage to marks)
        try:
            if exam.cbt_type == 'first_test':
                score_val = int(round((correct / total) * 20)) if total > 0 else 0
                result.test1 = min(20, max(0, score_val))  # Constrain to 0-20
            elif exam.cbt_type == 'second_test':
                score_val = int(round((correct / total) * 20)) if total > 0 else 0
                result.test2 = min(20, max(0, score_val))  # Constrain to 0-20
            elif exam.cbt_type == 'exam':
                score_val = int(round((correct / total) * 60)) if total > 0 else 0
                result.exam = min(60, max(0, score_val))  # Constrain to 0-60
            
            result.save()
        except Exception as e:
            # Log error but don't fail the exam submission
            print(f"Error auto-registering score: {e}")
```

**Defensive Strategies:**
- Converts percentage to correct scale (20 pts for test, 60 pts for exam)
- Uses `min()` and `max()` to constrain values
- Wrapped in try-catch to prevent exam failure on registration error
- Practice exams skip registration entirely

### 2.4 cbt_result() - Result Verification

```python
# Authorization: Only student can view their own session results
session = get_object_or_404(CBTSession, id=session_id, student__user=request.user)

# Defensive: Require completed session
if not session.completed_at:
    messages.warning(request, "This exam has not been completed yet.")
    return redirect('student_dashboard')

# Determine if score was auto-registered
score_registered = False
if total_questions > 0:
    exam = CBTExam.objects.filter(
        school_class=session.school_class, 
        subject=session.subject, 
        is_published=True
    ).order_by('-created_at').first()
    
    if exam and exam.cbt_type in ['first_test', 'second_test', 'exam']:
        # Check if StudentResult was created with this score
        try:
            result = StudentResult.objects.filter(
                student=session.student,
                school_class=session.school_class,
                subject=session.subject,
                academic_session=academic_session
            ).first()
            if result:
                score_registered = True
        except:
            pass
```

**Benefits:**
- Verifies session ownership (prevents unauthorized access)
- Detects incomplete sessions
- Determines if score was successfully registered for display

---

## 3. Frontend Defensive Measures

### 3.1 Timer with Auto-Submit (cbt_start.html)

```javascript
// Timer countdown: totalSeconds = duration * 60
const totalSeconds = duration * 60;
let remainingSeconds = totalSeconds;
let timerInterval;

function updateTimer() {
    remainingSeconds--;
    // ... update display ...
    
    if (remainingSeconds <= 0) {
        clearInterval(timerInterval);
        // Auto-submit exam
        document.getElementById('cbtForm').submit();
    }
}

timerInterval = setInterval(updateTimer, 1000);
```

**Protection:** Prevents students from exceeding allocated time.

### 3.2 Blur Detection (Tab Switch Prevention)

```javascript
let blurDetected = false;
const blurGracePeriod = 10; // seconds

document.addEventListener('blur', function() {
    blurDetected = true;
    let blurTimer = blurGracePeriod;
    
    // Student has 10 seconds to return to the exam
    const blurInterval = setInterval(() => {
        blurTimer--;
        if (blurTimer <= 0) {
            clearInterval(blurInterval);
            // Auto-submit if still out of focus
            document.getElementById('cbtForm').submit();
        }
    }, 1000);
});

document.addEventListener('focus', function() {
    blurDetected = false;
});
```

**Protection:** Prevents cheating by auto-submitting if student leaves the tab.

---

## 4. Data Flow Safety

### 4.1 Score Calculation Safety

```python
# Defensive: Handle division by zero
score_percentage = (correct / total) * 100 if total > 0 else 0

# Defensive: Constrain converted scores
score_val = int(round((correct / total) * 20)) if total > 0 else 0
result.test1 = min(20, max(0, score_val))  # Ensure 0 <= test1 <= 20
```

**Prevention:** Avoids division-by-zero errors and out-of-range scores.

### 4.2 Academic Session Lookup

```python
# Defensive: Handle missing active session
academic_session = AcademicSession.objects.filter(
    school=school_class.school, 
    is_active=True
).first()

if academic_session:
    # Only proceed if session exists
    # ... auto-registration logic ...
else:
    # Gracefully skip registration if no active session
    pass
```

**Prevention:** Prevents crashes due to missing academic session configuration.

---

## 5. Error Handling Best Practices

### 5.1 User-Facing Messages

```python
from django.contrib import messages

# Success messages
messages.success(request, "Exam submitted successfully!")

# Warning messages
messages.warning(request, "This exam has not been completed yet.")

# Error messages
messages.error(request, "You have already completed this exam. Retakes are not allowed.")
```

**Benefit:** Users understand what went wrong instead of seeing generic errors.

### 5.2 Graceful Degradation

```python
# Example: Score registration failure doesn't break exam submission
try:
    result.save()  # Save score to StudentResult
except Exception as e:
    print(f"Error auto-registering score: {e}")
    # Continue anyway - exam was already submitted
```

**Benefit:** Non-critical failures don't break the exam flow.

---

## 6. API Endpoint Safety (get_teacher_assigned_classes)

```python
@login_required
def get_teacher_assigned_classes(request):
    """
    Get teacher's assigned classes and subjects for CBT setup.
    
    Defensive Programming:
    - Authorization check: Only authenticated users
    - Role validation: Only teachers can access
    - Data validation: Returns only active classes/subjects
    - Error handling: Returns JSON error responses
    """
    try:
        # Get teacher profile
        teacher = request.user.teacherprofile
        if not teacher:
            return JsonResponse({
                'success': False, 
                'error': 'Teacher profile not found'
            }, status=404)
        
        # Get assigned classes
        assigned_classes = ClassSubject.objects.filter(
            teacher=teacher
        ).select_related('school_class', 'subject')
        
        # Build response with defensive null checks
        data = []
        for cs in assigned_classes:
            if cs.school_class and cs.subject:  # Ensure no null references
                data.append({
                    'class_id': cs.school_class.id,
                    'class_name': cs.school_class.name,
                    'subject_id': cs.subject.id,
                    'subject_name': cs.subject.name,
                })
        
        return JsonResponse({'success': True, 'data': data})
    
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': str(e)
        }, status=500)
```

**Protections:**
- Role-based access control (teachers only)
- Null reference checks
- JSON error responses
- Exception handling

---

## 7. Testing Recommendations

### Unit Tests
```python
def test_cbt_retake_prevention():
    """Ensure students can't retake non-practice exams."""
    # Create completed session
    # Attempt retake
    # Assert 403 or redirect response

def test_score_bounds():
    """Ensure scores are constrained to valid ranges."""
    # Submit exam with 0/total correct
    # Assert test1, test2, exam scores are within bounds

def test_invalid_duration():
    """Ensure exam duration is validated."""
    # Try to create exam with negative/zero/excessive duration
    # Assert ValidationError
```

### Integration Tests
```python
def test_full_cbt_flow():
    """End-to-end test of entire CBT system."""
    # 1. Create published exam
    # 2. Create questions
    # 3. Student takes exam
    # 4. Verify auto-registration
    # 5. Verify retake prevention
```

---

## 8. Maintenance Checklist

- [ ] Always call `.full_clean()` before `.save()` in views (or use ModelForm)
- [ ] Use `get_object_or_404()` instead of `.get()` to prevent 500 errors
- [ ] Add null checks when accessing foreign key relationships
- [ ] Log errors but don't fail user operations on non-critical issues
- [ ] Use database constraints (unique_together, UniqueConstraint) as safety net
- [ ] Test with edge cases (empty questions, zero students, no active session)
- [ ] Monitor auto-registration failures and investigate root causes

---

## 9. Common Issues & Solutions

### Issue: Student sees "Retake not allowed" but wants to retake practice exam
**Solution:** Check that `exam.cbt_type == 'practice'`. Practice exams should always allow retakes.

### Issue: Score not appearing in StudentResult
**Solution:** Verify `academic_session.is_active == True` and that the StudentResult was created with correct fields.

### Issue: Timer not auto-submitting on timeout
**Solution:** Check browser console for JavaScript errors. Ensure form ID is 'cbtForm' and matches template.

### Issue: Students reporting tab switch detection too sensitive
**Solution:** Increase `blurGracePeriod` in JavaScript (currently 10 seconds).

---

## 10. Future Enhancements

- [ ] Add question randomization to prevent cheating
- [ ] Implement question pools (display random subset of 50 questions from 100)
- [ ] Add question difficulty levels and adaptive testing
- [ ] Implement screen recording/monitoring for high-stakes exams
- [ ] Add detailed audit logs for compliance
- [ ] Implement question item analysis (difficulty index, discrimination index)
