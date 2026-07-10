# Defensive Programming Implementation - Quick Reference

## Summary for Developers

This guide shows how defensive programming was applied to the CBT module and how to apply similar patterns to other modules.

---

## Pattern 1: Model Validation with clean()

### Before (Vulnerable)
```python
class StudentResult(models.Model):
    test1 = models.PositiveIntegerField()  # No validation!
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
```

**Issues:** Can save invalid values (negative, >20, >60)

### After (Defensive)
```python
class StudentResult(models.Model):
    test1 = models.PositiveIntegerField()
    
    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate each field
        if self.test1 is not None and not (0 <= self.test1 <= 20):
            raise ValidationError({'test1': 'Test1 must be between 0 and 20'})
        
        if self.test2 is not None and not (0 <= self.test2 <= 20):
            raise ValidationError({'test2': 'Test2 must be between 0 and 20'})
        
        if self.exam is not None and not (0 <= self.exam <= 60):
            raise ValidationError({'exam': 'Exam must be between 0 and 60'})
    
    def save(self, *args, **kwargs):
        self.full_clean()  # Run validation before save
        super().save(*args, **kwargs)
```

**Benefits:** Validation at model layer, consistent across all save points

---

## Pattern 2: Database Constraints

### Level 1: Unique Constraints (Prevent Duplicates)
```python
class CBTExam(models.Model):
    school_class = models.ForeignKey(SchoolClass, ...)
    subject = models.ForeignKey(Subject, ...)
    cbt_type = models.CharField(...)
    
    class Meta:
        # Only one practice/test1/test2/exam per subject
        unique_together = ("school_class", "subject", "cbt_type")
```

### Level 2: Complex Constraints (Status-Based)
```python
class CBTSession(models.Model):
    student = models.ForeignKey(Student, ...)
    school_class = models.ForeignKey(SchoolClass, ...)
    subject = models.ForeignKey(Subject, ...)
    completed_at = models.DateTimeField(null=True)
    
    class Meta:
        constraints = [
            # Only one INCOMPLETE session per student per subject
            models.UniqueConstraint(
                fields=['student', 'school_class', 'subject'],
                condition=models.Q(completed_at__isnull=True),
                name='unique_incomplete_session'
            )
        ]
```

**Why It Works:** Database enforces constraint at INSERT time, impossible to create duplicates

### Level 3: Indexes (Performance + Safety)
```python
class CBTQuestion(models.Model):
    school_class = models.ForeignKey(SchoolClass, ...)
    subject = models.ForeignKey(Subject, ...)
    is_published = models.BooleanField()
    
    class Meta:
        indexes = [
            # Speed up: "get published questions for this class/subject"
            models.Index(fields=['school_class', 'subject', 'is_published']),
            
            # Speed up: "count questions per school"
            models.Index(fields=['school', 'is_published']),
        ]
```

**Triple Benefit:** Fast queries + Database optimization + Self-documenting

---

## Pattern 3: Authorization in Views

### Before (Vulnerable)
```python
def view_exam_results(request, session_id):
    session = CBTSession.objects.get(id=session_id)  # Anyone can view!
    return render(request, 'results.html', {'session': session})
```

**Issue:** Any authenticated user can access any session

### After (Defensive)
```python
def view_exam_results(request, session_id):
    # Combines authorization in the query itself
    session = get_object_or_404(
        CBTSession, 
        id=session_id,
        student__user=request.user  # ← Authorization filter
    )
    return render(request, 'results.html', {'session': session})
```

**Benefits:**
- 404 if student doesn't own session (not 403, so no information leakage)
- Single line handles authorization
- Works at database level

---

## Pattern 4: Safe Score Registration

### Before (Vulnerable)
```python
if exam.cbt_type == 'first_test':
    result.test1 = int((correct / total) * 20)  # Could be 21, 22, etc!
    result.save()
```

**Issues:** Rounding errors, negative values possible, no bounds

### After (Defensive)
```python
try:
    if exam.cbt_type == 'first_test':
        # 1. Calculate score with rounding
        score_val = int(round((correct / total) * 20)) if total > 0 else 0
        
        # 2. Constrain to valid range
        result.test1 = min(20, max(0, score_val))
        
        # 3. Recalculate dependent fields
        result.total = (result.test1 or 0) + (result.test2 or 0) + (result.exam or 0)
        result.grade = result.calculate_grade()
        
        # 4. Save
        result.save()
except Exception as e:
    # Log but don't fail
    logger.error(f"Score registration failed: {e}")
    # Exam was already submitted successfully
```

**Safety Layers:**
1. Division by zero prevention
2. Value bounds (min/max)
3. Rounding for predictability
4. Dependent field updates
5. Exception handling (failure doesn't crash exam)

---

## Pattern 5: Conditional Logic for Side Effects

### Before (Vulnerable)
```python
def submit_exam(request, session_id):
    session = get_object_or_404(CBTSession, id=session_id)
    # ... calculate score ...
    
    # Always register score
    result.test1 = score  # What if practice exam?
    result.save()
```

**Issue:** Registers scores for practice exams too

### After (Defensive)
```python
def submit_exam(request, session_id):
    session = get_object_or_404(CBTSession, id=session_id)
    
    # Get exam type first
    exam = CBTExam.objects.filter(
        school_class=session.school_class,
        subject=session.subject,
        is_published=True
    ).first()
    
    if not exam:
        messages.error(request, "Exam configuration missing")
        return redirect('dashboard')
    
    # ... calculate score ...
    
    # Only register for test/exam types (not practice)
    if exam.cbt_type in ['first_test', 'second_test', 'exam']:
        # Register score
        result.test1 = score
        result.save()
    else:
        # Practice exam - show score but don't register
        display_score_only(score)
```

**Benefits:** Exam type determines behavior, clear intent

---

## Pattern 6: Graceful Degradation

### Before (Fails Hard)
```python
def get_teacher_classes(request):
    teacher = request.user.teacherprofile  # Crashes if no profile!
    classes = ClassSubject.objects.filter(teacher=teacher)
    return JsonResponse({'classes': classes})
```

### After (Resilient)
```python
def get_teacher_classes(request):
    try:
        # Check authorization
        teacher = request.user.teacherprofile
        if not teacher:
            return JsonResponse({'error': 'Teacher profile not found'}, status=404)
        
        # Get classes
        classes = ClassSubject.objects.filter(teacher=teacher)
        
        # Validate data
        data = []
        for cs in classes:
            if cs.school_class and cs.subject:  # Null checks
                data.append({
                    'class_id': cs.school_class.id,
                    'subject_id': cs.subject.id
                })
        
        return JsonResponse({'success': True, 'data': data})
    
    except Exception as e:
        logger.error(f"Error fetching teacher classes: {e}")
        return JsonResponse({'error': str(e)}, status=500)
```

**Layers:**
1. Try-catch outer wrapper
2. Profile existence check
3. Data validation (null checks)
4. Error responses
5. Logging for debugging

---

## Pattern 7: Temporal Logic Validation

### Before (Vulnerable)
```python
session = CBTSession.objects.create(
    student=student,
    started_at=datetime.now(),
    completed_at=past_datetime  # What if backwards?
)
```

### After (Defensive)
```python
class CBTSession(models.Model):
    def clean(self):
        # Validate temporal ordering
        if self.completed_at and self.completed_at < self.started_at:
            raise ValidationError(
                'Completion time cannot be before start time'
            )
```

**Why Matters:** Prevents illogical data in reports

---

## Pattern 8: API Response Safety

### Before (Vulnerable)
```python
@login_required
def api_get_data(request):
    data = {'result': fetch_result()}  # Could be None!
    return JsonResponse(data)
```

**Issue:** JSON might have null/error values without clear status

### After (Defensive)
```python
@login_required
def api_get_data(request):
    try:
        result = fetch_result()
        
        if not result:
            return JsonResponse({
                'success': False,
                'error': 'No data found'
            }, status=404)
        
        return JsonResponse({
            'success': True,
            'data': result
        }, status=200)
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
```

**Benefits:**
- Every response has explicit success field
- Clear error messages
- HTTP status codes reflect outcome
- Consistent format for client code

---

## Implementation Checklist

For each module/feature:

- [ ] Add `clean()` methods to all models
- [ ] Add database constraints (unique, check, etc.)
- [ ] Add indexes on query fields
- [ ] Use `get_object_or_404()` in views
- [ ] Add try-catch to critical operations
- [ ] Validate authorization in queries
- [ ] Handle null foreign keys
- [ ] Constrain numeric values (min/max)
- [ ] Handle zero divisors
- [ ] Log errors without crashing
- [ ] Return user-friendly error messages
- [ ] Document error scenarios
- [ ] Add temporal validation
- [ ] Test edge cases

---

## Code Review Questions

When reviewing defensive programming:

1. **Can this crash with null/missing data?** → Add null checks
2. **Can this create invalid data?** → Add validation
3. **Can unauthorized user see this?** → Add authorization check
4. **What if the database is corrupted?** → Add constraints
5. **What if calculation fails?** → Add try-catch
6. **Is the error message helpful?** → Improve messaging
7. **What happens in edge cases?** → Test and document
8. **Is this query slow?** → Add indexes
9. **Can this cause data inconsistency?** → Add constraints
10. **Is this testable?** → Document assumptions

---

## File Locations - CBT Module Reference

- **Models with defensive patterns**: [academics/models.py](academics/models.py) (CBTExam, CBTQuestion, CBTSession, CBTResponse)
- **Views with authorization**: [academics/views.py](academics/views.py) (cbt_start, cbt_result)
- **Database constraints**: [academics/migrations/0015_*.py](academics/migrations/0015_alter_cbtresponse_unique_together_and_more.py)
- **Complete documentation**: [CBT_DEFENSIVE_PROGRAMMING_GUIDE.md](CBT_DEFENSIVE_PROGRAMMING_GUIDE.md)
- **Technical reference**: [CBT_TECHNICAL_REFERENCE.md](CBT_TECHNICAL_REFERENCE.md)

---

## Key Takeaway

**Defensive programming is about:**
1. Preventing bad data from entering the system (Model validation)
2. Preventing bad data from being duplicated (Constraints)
3. Preventing unauthorized access (Authorization)
4. Preventing crashes from edge cases (Try-catch, null checks)
5. Helping developers understand what went wrong (Error messages, logging)

**It's not paranoia — it's professionalism.**
