import os
import re

# 1. Update Teacher Main Dashboard
teacher_dash = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\dashboard_teacher.html'
with open(teacher_dash, 'r', encoding='utf-8') as f:
    content = f.read()

# Update coloring (Indigo)
content = content.replace('#1a56db', 'var(--primary-color)')
content = content.replace('#eef2fa', 'var(--primary-light)')
content = content.replace('text-primary', 'text-indigo-unique') # Temporary placeholder to avoid conflict if I replace later
content = content.replace('text-indigo-unique', 'style="color: var(--primary-color) !important;"') # Wait, better to use regex

# Update the "Welcome" badge
content = content.replace('style="background: #eef2fa; color: #1a56db;', 'style="background: var(--primary-light); color: var(--primary-color);')
# Update Stat card numbers
content = content.replace('style="color: #1a56db;"', 'style="color: var(--primary-color);"')
# Update Stat icons background
content = content.replace('color: #eef2fa;', 'color: var(--primary-light);')
# Update table badges and buttons
content = content.replace('color: #1a56db;', 'color: var(--primary-color);')

# Fix some specific hardcoded blues in the quicklinks
content = re.sub(r'text-primary', r'', content) # Remove bootstrap primary class
content = content.replace('<i class="fas fa-clipboard-list"></i>', '<i class="fas fa-clipboard-list" style="color: var(--primary-color);"></i>')

with open(teacher_dash, 'w', encoding='utf-8') as f:
    f.write(content)


# 2. Update Teacher Class Management Dashboard
class_dash = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\teacher_class_dashboard.html'
with open(class_dash, 'r', encoding='utf-8') as f:
    class_content = f.read()

# Apply HaDerech card styling
class_content = re.sub(r'<div class="card">', r'<div class="card border-0 shadow-sm" style="border-radius: 16px; margin-bottom: 24px;">', class_content)
class_content = re.sub(r'<div class="card mt-4">', r'<div class="card border-0 shadow-sm mt-4" style="border-radius: 16px; margin-bottom: 24px;">', class_content)

# Update headers
class_content = re.sub(r'<div class="card-header bg-primary text-white">', r'<div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0; padding-top: 1.25rem; border-bottom: 1px solid var(--border-color) !important;">', class_content)
class_content = class_content.replace('<h5 class="mb-0 text-white">', '<h5 class="mb-0 fw-bold" style="color: var(--text-dark);">')
# Match the pattern in teachers dashboard for headers
class_content = re.sub(r'<div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0; padding-top: 1.25rem; border-bottom: 1px solid var(--border-color) !important;">\s*<h5 class="mb-0">', r'<div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0; padding-top: 1.25rem; border-bottom: 1px solid var(--border-color) !important;">\n                    <h5 class="mb-0 fw-bold" style="color: var(--text-dark);">', class_content)

# Update page title back buttons
class_content = class_content.replace('btn-outline-primary', 'btn-light border shadow-sm')

with open(class_dash, 'w', encoding='utf-8') as f:
    f.write(class_content)

print("Teacher and Class Management dashboards unified with HaDerech Theme!")
