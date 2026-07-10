# SMRPS Screen Recording & Demo Guide

## Application URL
**Development Server:** http://localhost:8000

---

## Demo Test Accounts

### Test Credentials (Use in Screen Recording)

#### 1. Super Admin Account
- **Username:** admin
- **Password:** (Check database or use: `python manage.py shell` → `from django.contrib.auth import get_user_model; User = get_user_model(); u = User.objects.get(username='admin'); print(u.username)`)

#### 2. School Admin Account  
- **Username:** school_admin
- **Password:** schoolpass123
- **School:** Sample School
- **Role:** School Administrator

#### 3. Teacher Account
- **Username:** teacher1
- **Password:** teacherpass123
- **School:** Sample School
- **Class:** JSS1A
- **Subject:** English, Mathematics

#### 4. Student Account
- **Username:** student1
- **Password:** student_admission_001  
- **School:** Sample School
- **Class:** JSS1A

---

## Demo Flow (7-10 minutes)

### SEGMENT 1: Application Overview (1 min)

**What to Show:**
- Title screen / home page
- Brief intro: "This is SMRPS - a school management system"

**Script:**
> "Welcome to SMRPS, the Student Management and Results Processing System. This application helps schools manage students, teachers, classes, and academic results in one unified platform."

**Steps:**
1. Navigate to http://localhost:8000
2. Show home page
3. Point out "Login" button

---

### SEGMENT 2: School Admin Dashboard (2 mins)

**Login as:** School Admin  
**Expected View:** School Admin Dashboard

**What to Show:**
1. **Dashboard Overview**
   - School name and session
   - Quick stats (total students, classes, teachers)
   - Key metrics cards

2. **Navigation Menu** - Point out main sections:
   - 📊 Dashboard
   - 👥 Students Management
   - 👨‍🏫 Teachers Management  
   - 📚 Classes & Subjects
   - 📋 Academic Sessions
   - 📄 Reports

**Script:**
> "As a school admin, you get a comprehensive dashboard showing your school's overview. You can see total students, teachers, classes, and latest academic session. From the menu on the left, you can manage all aspects of your school."

---

### SEGMENT 3: Student Management (1.5 mins)

**Navigate to:** Students → View All Students (or similar)

**What to Show:**
1. **Student List**
   - Table with student names, admission numbers, classes
   - Filter/search functionality
   - Pagination

2. **Student Details** (Click on one student)
   - Personal info (name, gender, DOB)
   - Class assignment
   - Contact information
   - Student photo (if available)

3. **Add New Student** (Optional - if time allows)
   - Show form with fields
   - Highlight validation

**Script:**
> "Here's the student management section. You can view all students enrolled in your school, their admission numbers, and assigned classes. Clicking on a student shows their complete profile including personal details and current class assignment. Admins can also add new students or import them in bulk."

---

### SEGMENT 4: Academic Setup (1 min)

**Navigate to:** Classes & Subjects (or Academics section)

**What to Show:**
1. **School Classes** 
   - List of classes (JSS1, JSS2, JSS3, SS1, SS2, SS3)
   - Form teacher assignment
   - Student count per class

2. **Subjects Management**
   - Available subjects (English, Mathematics, etc.)
   - Assign subjects to classes
   - Teacher-subject allocation

**Script:**
> "In the academics section, you organize your school structure. You can create and manage classes, assign form teachers, and define subjects. The system maintains relationships between classes, subjects, and teachers."

---

### SEGMENT 5: Teacher Dashboard (1.5 mins)

**Logout from School Admin, Login as: Teacher**  
**Expected View:** Teacher Dashboard

**What to Show:**
1. **Teacher Dashboard Overview**
   - Classes assigned to teacher
   - Number of students per class
   - Recent activities

2. **Result Entry Interface**
   - Select class and subject
   - Enter student test scores
   - Show score range validation (e.g., test: 0-20, exam: 0-60)
   - Auto-calculated total and grade

3. **Review Entries**
   - View entered results
   - Edit capability
   - Confirmation before submission

**Script:**
> "Teachers have their own dashboard. They can see the classes and subjects they're assigned to. The main feature is result entry - teachers can enter test scores, exam scores, and the system automatically calculates totals and grades based on predefined rules. Results are saved securely and can be reviewed or edited."

**Demonstration:**
- Click on a class
- Show student list with score entry fields
- Enter a few sample scores
- Point out auto-calculation of totals
- Show grade assignment (A, B, C, D, E, F)

---

### SEGMENT 6: Result Processing (1.5 mins)

**Navigate to:** Results / Term Results (Admin or Teacher view)

**What to Show:**
1. **Term Results Summary**
   - List of students with totals, averages
   - Class positions
   - Subject-wise performance

2. **Generate Reports**
   - Show "Generate Term Report" button
   - Explain report includes:
     - Subject-wise results
     - Totals and grades
     - Class rankings

3. **Download Results** (Optional)
   - Show PDF download functionality
   - Display sample PDF (cumulative results slip)
   - Show details: student name, class, all terms, grades

**Script:**
> "Once teachers enter all results, school admins can view consolidated term results. The system automatically ranks students within each class. You can generate individual student reports as PDFs, which include their performance across all subjects and terms. Reports can be downloaded individually or in bulk."

---

### SEGMENT 7: Student Portal (1.5 mins)

**Logout from Teacher, Login as: Student**  
**Expected View:** Student Dashboard

**What to Show:**
1. **Student Dashboard**
   - Student name and class
   - Current academic session
   - Available actions

2. **View Personal Results**
   - Tabs for different terms (First, Second, Third Term)
   - Subject-wise scores and grades
   - Total score and position in class
   - Highlight any improvement across terms

3. **Download Result Slip**
   - Show "Download Cumulative Result" button
   - Generate PDF
   - Show formatted result slip with:
     - School name and logo
     - Student details
     - All terms' results
     - Overall performance

4. **Additional Features** (if time allows)
   - Attendance records (if available)
   - Account settings
   - Password change

**Script:**
> "Students can access their personal results portal. They see all their scores across subjects and terms, their class position, and any grades. They can download a formal result slip in PDF format for their records. This gives students transparency about their academic performance."

---

### SEGMENT 8: Advanced Features (1 min)

**Navigate back to Admin view if time allows**

**What to Show:**
1. **Multi-Tenant Support** (Explain, don't demo)
   - "This system supports multiple schools"
   - Each school has isolated data
   - Admins only see their school

2. **Report Generation** (if available)
   - Class performance reports
   - Subject analysis
   - Grade distribution charts

3. **Responsive Design**
   - Show the app works on tablet/mobile
   - Menu collapses on smaller screens
   - Touch-friendly interface

**Script:**
> "SMRPS is built for modern education management. It supports multiple schools within a single platform, with complete data isolation. The interface is responsive and works on phones, tablets, and desktops. Teachers can enter results from anywhere, and students can check their performance anytime."

---

## Screen Recording Technical Setup

### Before Recording:

1. **Clear Browser Cache**
   ```bash
   # Or just use incognito mode
   ```

2. **Zoom/Resolution**
   - Set display to 1920x1080 or higher
   - Zoom UI to 125% if text is too small
   - Test microphone and speaker

3. **Disable Notifications**
   - Close Slack, Teams, Discord
   - Silence phone notifications

4. **Prepare Test Data** (Create if needed)
   ```bash
   cd C:\Users\User\PycharmProjects\SMRPS
   python manage.py shell
   
   # Create test school if not exists
   from schools.models import School
   school = School.objects.get_or_create(
       name='Sample School',
       defaults={'code': 'SS001', 'address': 'Sample Address'}
   )[0]
   
   # Create test admin user
   from accounts.models import User
   User.objects.create_superuser(
       username='admin',
       email='admin@school.com',
       password='admin123',
       school=None
   )
   ```

### Recording Tool Options:

**Option 1: Windows Built-in (Free)**
- **Xbox Game Bar:** Win + G
- Works great for 1080p
- Built-in audio capture

**Option 2: OBS Studio (Free, Advanced)**
```bash
# Download from https://obsproject.com
# More control over quality, bitrate, output format
```

**Option 3: Camtasia (Paid, Professional)**
- Best for editing
- Built-in zoom/pan effects
- Great for tutorials

**Option 4: ScreenFlow/Quicktime (Mac)**
- If testing on macOS

---

## Recording Script Template

```
[INTRO - 15 seconds]
"Welcome to SMRPS Demo. This is a comprehensive school management system that helps schools organize students, teachers, classes, and academic results. Let me walk you through the key features."

[DEMO FLOW]
- Follow segments above
- Maintain steady pace
- Pause briefly on key screens
- Use cursor highlighting to point out features

[CONCLUSION - 10 seconds]
"SMRPS simplifies school administration, making result management efficient and transparent. Thank you for watching!"
```

---

## Keyboard Shortcuts for Demo

| Action | Shortcut |
|--------|----------|
| Open Developer Tools | F12 |
| Open Links in New Tab | Ctrl + Click |
| Fullscreen Browser | F11 |
| Zoom In | Ctrl + + |
| Zoom Out | Ctrl + - |
| Normal Zoom | Ctrl + 0 |

---

## Common Issues & Solutions

### Issue: Server not running
**Solution:**
```bash
cd C:\Users\User\PycharmProjects\SMRPS
python manage.py runserver 0.0.0.0:8000
```

### Issue: Login credentials not working
**Solution:**
```bash
python manage.py shell
from accounts.models import User
# List all users
User.objects.all().values_list('username', flat=True)

# Reset password if needed
u = User.objects.get(username='admin')
u.set_password('newpass123')
u.save()
```

### Issue: Page styling looks broken
**Solution:**
```bash
python manage.py collectstatic --noinput
```

### Issue: No students showing up
**Solution:**
```bash
python manage.py shell
from students.models import Student
from schools.models import School
school = School.objects.first()
# Check if students exist
print(Student.objects.filter(school=school).count())
```

---

## Final Checklist Before Recording

- [ ] Server is running (`python manage.py runserver`)
- [ ] Browser can access http://localhost:8000
- [ ] All test accounts created and passwords known
- [ ] Test data populated (students, classes, results)
- [ ] Audio input working (microphone test)
- [ ] Recording software open and configured
- [ ] Desktop notifications disabled
- [ ] 30+ minutes of free time (don't rush)
- [ ] Window focused, nothing else visible
- [ ] Fullscreen or maximized window

---

## Post-Recording

1. **Review:** Watch first 1 minute to check quality
2. **Edit:** Remove long pauses, add captions if desired
3. **Upload:** Choose platform (YouTube, Vimeo, etc.)
4. **Share:** Get feedback before final distribution

---

**Estimated Total Recording Time:** 10-15 minutes (including natural pauses and mistakes)  
**Estimated Editing Time:** 30 minutes - 1 hour (if adding effects)

Good luck with your demo! 🎥
