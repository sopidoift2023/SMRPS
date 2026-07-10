# SMRPS Security Action Plan (Immediate Fixes)

**Priority Level:** CRITICAL ⛔  
**Time to Complete:** 2-4 hours  
**Risk Level if Not Fixed:** Production data breach

---

## 🚨 STEP 1: SECURE EXPOSED SECRETS (DO THIS FIRST - 15 minutes)

### 1.1 Rotate All Credentials Immediately

```bash
# Step 1: Change Supabase password
# Go to: https://supabase.com/dashboard
# Project > Database > Password > Reset Password
# WARNING: This will disconnect all apps briefly

# Step 2: Revoke old API key and generate new one
# Go to https://platform.deepseek.com/api_keys
# Delete the old key: sk-22c3634e97cb48378bb31be6753acb24
# Create new API key, copy it

# Step 3: Generate new Django SECRET_KEY
python manage.py shell
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
# Copy the output

# Step 4: Create new .env file with SECURE values
# DO NOT commit this file!
```

### 1.2 Update .env with New Credentials

**File:** `.env`

```env
# NEW SECRET KEY (from step 3)
SECRET_KEY='<your-new-generated-key-here>'

# NEW DATABASE URL (with new password)
DATABASE_URL='postgresql://postgres.<user>:<NEW_PASSWORD>@aws-1-eu-west-2.pooler.supabase.com:6543/postgres'

# NEW API KEY (from step 2)
DEEPSEEK_API_KEY='sk-<your-new-api-key-here>'

# Keep these unchanged
DEBUG=False  # IMPORTANT: Set to False for production
ALLOWED_HOSTS='yourdomain.com,www.yourdomain.com'
```

### 1.3 Remove .env from Git History

```bash
cd C:\Users\User\PycharmProjects\SMRPS

# Remove .env from git tracking
git rm --cached .env

# Add .env to .gitignore (if not already)
echo ".env" >> .gitignore

# Commit the cleanup
git add .gitignore
git commit -m "Remove .env from version control - use environment variables"

# IMPORTANT: Previous commits still have the secret!
# Run this to rewrite history (ONLY if not pushed to shared repo)
git filter-branch --tree-filter 'rm -f .env' HEAD
```

---

## 🔒 STEP 2: IMPLEMENT RATE LIMITING (30 minutes)

### 2.1 Install Package

```bash
pip install django-ratelimit
pip freeze > requirements.txt
```

### 2.2 Update settings.py

```python
# In config/settings.py, add:

INSTALLED_APPS = [
    # ... existing apps
    'django_ratelimit',
]

# Ratelimit settings
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'  # Uses default cache or in-memory
```

### 2.3 Protect Login Views

**File:** `portal/urls.py`

```python
from django.contrib.auth import views as auth_views
from django_ratelimit.decorators import ratelimit

# BEFORE:
# path("login/", auth_views.LoginView.as_view(...), name="login")

# AFTER:
path(
    "login/", 
    ratelimit(key='ip', rate='10/m')(
        auth_views.LoginView.as_view(template_name="portal/login.html")
    ),
    name="login"
)
```

### 2.4 Test Rate Limiting

```bash
# In terminal, run 15+ rapid requests to login
for i in {1..15}; do curl -I http://localhost:8000/login/; done

# Should see 429 Too Many Requests after 10 requests
```

---

## 🔐 STEP 3: SECURE FILE UPLOADS (20 minutes)

### 3.1 Create File Validator

**File:** `academics/validators.py` (NEW FILE)

```python
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
import mimetypes

class ImageFileValidator:
    """Validate uploaded image files"""
    
    ALLOWED_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
    MAX_SIZE = 5 * 1024 * 1024  # 5MB
    
    def __call__(self, file: UploadedFile):
        # Check file size
        if file.size > self.MAX_SIZE:
            raise ValidationError(
                f"File size ({file.size / 1024 / 1024:.2f}MB) exceeds maximum of 5MB"
            )
        
        # Check MIME type (not just extension)
        mime_type, _ = mimetypes.guess_type(file.name)
        if mime_type not in self.ALLOWED_TYPES:
            raise ValidationError(
                f"File type {mime_type} not allowed. Use: JPEG, PNG, or WebP"
            )
        
        # Additional check: read magic bytes
        file.seek(0)
        header = file.read(12)
        
        # Check for JPEG signature
        if mime_type == 'image/jpeg':
            if header[:2] != b'\xff\xd8':
                raise ValidationError("Invalid JPEG file")
        
        # Check for PNG signature  
        elif mime_type == 'image/png':
            if header[:8] != b'\x89PNG\r\n\x1a\n':
                raise ValidationError("Invalid PNG file")
        
        file.seek(0)  # Reset file pointer


image_file_validator = ImageFileValidator()
```

### 3.2 Apply Validator to Models

**File:** `schools/models.py`

```python
from academics.validators import image_file_validator

class School(models.Model):
    # ... existing fields
    
    # UPDATE these fields:
    logo = models.ImageField(
        upload_to='school_logos/',
        null=True,
        blank=True,
        validators=[image_file_validator]  # ADD THIS
    )
    
    principal_signature = models.ImageField(
        upload_to='signatures/',
        null=True,
        blank=True,
        validators=[image_file_validator]  # ADD THIS
    )
    
    stamp = models.ImageField(
        upload_to='stamps/',
        null=True,
        blank=True,
        validators=[image_file_validator]  # ADD THIS
    )
```

### 3.3 Test File Upload

```bash
# Try uploading a text file or executable - should be rejected
# Try uploading a large image - should check file size
```

---

## 🎯 STEP 4: FIX DEFAULT PASSWORD SECURITY (15 minutes)

### 4.1 Update Student Creation

**File:** `students/models.py`

```python
# BEFORE:
import secrets
from django.contrib.auth import get_user_model

User = get_user_model()

# AFTER - Update save() or create method:

def create_student_with_secure_password(admission_number, first_name, last_name, school):
    """Create student with secure random password"""
    
    # Generate secure random password
    password = secrets.token_urlsafe(16)  # 128-bit random
    
    # Create user
    user = User.objects.create_user(
        username=admission_number,
        first_name=first_name,
        last_name=last_name,
        password=password,
        role=User.Role.STUDENT,
        school=school
    )
    
    # TODO: Send password to student/parent via email
    # For now, admin should provide password securely
    
    return user, password


# In students/admin.py, add custom action:
from django.contrib import admin
from students.models import Student

@admin.action(description="Generate secure passwords for selected students")
def generate_secure_passwords(modeladmin, request, queryset):
    for student in queryset:
        if not student.user:
            continue
        
        password = secrets.token_urlsafe(16)
        student.user.set_password(password)
        student.user.save()
        
        # Log or display the password for admin to share
        messages.info(request, f"Reset password for {student.user.username}. Share securely with student.")

class StudentAdmin(admin.ModelAdmin):
    actions = [generate_secure_passwords]
```

### 4.2 Add Force Password Change on First Login

**File:** `portal/views.py`

```python
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

@login_required
def check_first_login(request):
    """Check if user needs to change password on first login"""
    user = request.user
    
    # Add a field to User model: force_password_change (BooleanField, default=True)
    if hasattr(user, 'force_password_change') and user.force_password_change:
        return redirect('portal:force_change_password')
    
    return None

# Middleware to check
# In config/settings.py MIDDLEWARE:
# Add: 'portal.middleware.FirstLoginPasswordMiddleware'

# Create portal/middleware.py:
class FirstLoginPasswordMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        if request.user.is_authenticated and request.user.force_password_change:
            if not request.path.startswith('/portal/force-change-password'):
                return redirect('portal:force_change_password')
        
        response = self.get_response(request)
        return response
```

---

## 📊 STEP 5: ADD SECURITY HEADERS (10 minutes)

### 5.1 Update settings.py

**File:** `config/settings.py`

```python
# Add/update these security settings:

# Already set:
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

# ADD THESE:
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Content Security Policy (basic)
CSP_DEFAULT_SRC = ("'self'",)
CSP_SCRIPT_SRC = ("'self'", "'unsafe-inline'")  # Consider removing unsafe-inline
CSP_STYLE_SRC = ("'self'", "'unsafe-inline'")
CSP_IMG_SRC = ("'self'", "data:", "https:")

# X-Content-Type
X_CONTENT_TYPE_OPTIONS = 'nosniff'

# Referrer Policy
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Permissions Policy (formerly Feature Policy)
PERMISSIONS_POLICY = {
    'accelerometer': '()',
    'camera': '()',
    'geolocation': '()',
    'gyroscope': '()',
    'magnetometer': '()',
    'microphone': '()',
    'payment': '()',
    'usb': '()',
}
```

### 5.2 Install django-csp (optional but recommended)

```bash
pip install django-csp
```

---

## 📝 STEP 6: AUDIT LOGGING (30 minutes)

### 6.1 Create Audit Log Model

**File:** `accounts/models.py` (Add to existing file)

```python
import json
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class AuditLog(models.Model):
    """Track sensitive user actions"""
    
    ACTION_CHOICES = [
        ('LOGIN', 'Login'),
        ('LOGOUT', 'Logout'),
        ('PASSWORD_CHANGE', 'Password Change'),
        ('RESULT_ENTRY', 'Result Entry'),
        ('RESULT_DOWNLOAD', 'Result Download'),
        ('STUDENT_CREATE', 'Student Created'),
        ('STUDENT_DELETE', 'Student Deleted'),
        ('PERMISSION_CHANGE', 'Permission Changed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    resource_type = models.CharField(max_length=100, blank=True)  # e.g., "StudentResult"
    resource_id = models.IntegerField(null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    changes = models.JSONField(default=dict, blank=True)  # What changed
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['action', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"


# Utility function to log actions
def log_audit(request, action, resource_type='', resource_id=None, changes=None):
    """Log user action"""
    AuditLog.objects.create(
        user=request.user if request.user.is_authenticated else None,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=get_client_ip(request),
        user_agent=request.META.get('HTTP_USER_AGENT', ''),
        changes=changes or {}
    )

def get_client_ip(request):
    """Get client IP address"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
```

### 6.2 Use Audit Logging in Views

**File:** `portal/views.py`

```python
from accounts.models import log_audit

@login_required
def change_password(request):
    """Self-service password change for all users"""
    if request.method == 'POST':
        old_password = request.POST.get('old_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not all([old_password, new_password, confirm_password]):
            messages.error(request, "All fields are required.")
        elif new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
        elif not request.user.check_password(old_password):
            messages.error(request, "Incorrect old password.")
        else:
            request.user.set_password(new_password)
            request.user.save()
            update_session_auth_hash(request, request.user)
            
            # LOG THE ACTION
            log_audit(
                request,
                action='PASSWORD_CHANGE',
                changes={'password': 'changed'}
            )
            
            messages.success(request, "Password updated successfully!")
            return redirect('portal:dashboard')
    
    return render(request, "portal/change_password.html")
```

### 6.3 Run Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## ✅ VERIFICATION CHECKLIST

After completing all steps above, verify:

```bash
# 1. Check .env is not in git
git log --all -- .env  # Should show it was removed

# 2. Test rate limiting
curl -I http://localhost:8000/login/  # Repeat 15+ times

# 3. Test file upload validation
# Try uploading non-image file - should fail

# 4. Check security headers
curl -I http://localhost:8000/ | grep -i "strict\|content-type\|x-frame"

# 5. Verify audit logging
python manage.py shell
from accounts.models import AuditLog
print(AuditLog.objects.count())  # Should have entries

# 6. Check no sensitive data in error pages
# Set DEBUG=False temporarily and trigger error
```

---

## ⚠️ CRITICAL REMINDERS

1. **Never commit .env to git again**
   - Add to .gitignore
   - Use environment variables in CI/CD

2. **Secrets are NOW PUBLIC on GitHub**
   - Anyone can access your database
   - Anyone can use your API key
   - You MUST rotate credentials
   - If this is a real production system, treat as data breach

3. **Test in development first**
   - All changes should be tested locally
   - Use separate test database
   - Backup production before applying changes

4. **Monitor after changes**
   - Check application logs
   - Verify no broken functionality
   - Test all user roles (admin, teacher, student)

---

## 📞 SUPPORT

If you encounter issues:

1. **Server won't start:**
   ```bash
   python manage.py check
   ```

2. **Database errors:**
   ```bash
   python manage.py migrate
   ```

3. **Static files missing:**
   ```bash
   python manage.py collectstatic
   ```

4. **Reset everything:**
   ```bash
   python manage.py flush  # Deletes all data!
   python manage.py migrate
   python manage.py createsuperuser
   ```

---

**Time Estimate:** 2-4 hours  
**Difficulty:** Intermediate  
**Impact:** Critical security improvements

✅ Complete these steps before any production deployment!
