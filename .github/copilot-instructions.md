# SMRPS Codebase Guide for AI Agents

## Project Overview
**SMRPS** (Student Management and Results Processing System) is a Django 6.0 application for managing schools, teachers, students, and academic results. It uses a multi-tenant architecture where **`School` is the root entity** — all data belongs to a specific school.

## Architecture & Data Flow

### Core Domain Model
- **Users** (`accounts.User`): Custom AbstractUser with roles (SUPER_ADMIN, SCHOOL_ADMIN, TEACHER, STUDENT)
- **School**: Root multi-tenant entity. Non-super users must have `school != null`
- **Academic Structure**: `School` → `SchoolClass` (JSS1, SS3) → `Student` → `StudentResult` (per subject/term)
- **Teachers**: `TeacherProfile` (1-to-1 with User) assigned to `ClassSubject` (class + subject pair)
- **Results**: `StudentResult` (test1=0-20, test2=0-20, exam=0-60, auto-calculated total & grade)
- **Summaries**: `TermResultSummary` (per student per term - total, average, class position)

### Key Files & Their Responsibilities
- [accounts/models.py](accounts/models.py): User model with role-based access control and school validation
- [academics/models.py](academics/models.py): Core academic data (classes, subjects, results, term summaries)
- [academics/services.py](academics/services.py): Business logic for computing term results and class positions (handles ties correctly)
- [schools/models.py](schools/models.py): School, subscription, and academic session management
- [portal/views.py](portal/views.py): Role-based dashboard routing and teacher result entry UI
- [config/settings.py](config/settings.py): App load order matters (base infrastructure before features)

## Developer Workflows

### Running the Development Server
```bash
python manage.py runserver
```

### Database Operations
```bash
python manage.py makemigrations <app_name>
python manage.py migrate
```

### Creating a User with Role Validation
```python
# For non-super users: school is required
user = User.objects.create_user(
    username='john', 
    password='pass', 
    role=User.Role.TEACHER,
    school=school_instance
)
```

### Computing Term Results
```python
from academics.services import compute_term_results
compute_term_results(school_class, academic_session, term='First')
# Result: TermResultSummary records with position = class rank
```

## Critical Patterns & Conventions

### 1. Multi-Tenant Enforcement
- Always filter querysets by `school__isnull=False` for non-super data
- Use `select_related('school')` to avoid N+1 queries
- Validate that assigned teacher's school matches the class's school (see `ClassSubject.clean()`)

### 2. Data Validation
- **Model-Level**: Use `clean()` methods for business logic; call `full_clean()` before save
- **User Model**: Allows `role=null` only during `createsuperuser`; skip validation with `skip_clean=True` when programmatically updating
- **StudentResult**: Auto-calculates `total` and `grade` in `save()`. Validators prevent invalid scores (test1/test2 ≤20, exam ≤60)

### 3. Avoiding Circular Imports
- Student references use `"students.Student"` string reference (see `StudentResult.student` ForeignKey)
- This is intentional — don't change it to direct import

### 4. Result Calculation Logic
- Grade mapping: A (80+), B (70+), C (60+), D (50+), E (40+), F (<40)
- Term summaries sort by average descending; position handles ties (students with same average get same rank)
- See [academics/services.py](academics/services.py#L48-L62) for tie-handling algorithm

### 5. Role-Based Views
- Use `@login_required` on portal views
- Check `request.user.role` to determine dashboard type (see [portal/views.py](portal/views.py#L7-L20))
- Return `unauthorized.html` template if role doesn't match expected permission

## Common Tasks

### Adding a New Subject to a School
```python
from academics.models import Subject
subject = Subject.objects.create(
    school=school_instance,
    name='Physics',
    code='PHY101'
)
```

### Assigning a Teacher to a Class Subject
```python
from academics.models import ClassSubject
ClassSubject.objects.create(
    school_class=jsclass,
    subject=physics,
    teacher=teacher_profile  # validation ensures teacher.school == jsclass.school
)
```

### Recording Student Results
```python
from academics.models import StudentResult
result = StudentResult(
    student=student,
    school_class=jsclass,
    subject=physics,
    academic_session=session,
    term='First',
    test1=15,
    test2=18,
    exam=55
)
result.save()  # Computes total=88, grade='A'
```

## Integration Points
- **Auth**: Uses Django's built-in auth with custom User model (see `AUTH_USER_MODEL` in [config/settings.py](config/settings.py#L121))
- **Templates**: Base templates in `templates/`, app-specific in `<app>/templates/<app>/`
- **Admin**: All models registered in `admin.py` per app
- **Media**: Student logos/uploads go to `MEDIA_ROOT` (SQLite in dev, no separate storage layer)

## Testing Approach
- Use Django TestCase for database transactions (auto-rollback)
- Test data validation with `.full_clean()` to catch ValidationError
- Mock school context for multi-tenant tests

## Known Constraints
- SQLite in development (db.sqlite3) — no concurrent writes in production
- DEBUG=True with hardcoded SECRET_KEY — requires config overrides for production
- No API layer yet (views render HTML templates only)
- Subscription model exists but not integrated into permission checks
