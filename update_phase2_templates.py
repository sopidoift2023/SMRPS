import os
import re

def update_template(filepath, branding_name="HaDerech"):
    with open(filepath, 'r', encoding='utf-8') as f:
        html = f.read()

    # 1. Update Sidebar block to remove hardcoded old styles and rely on base.html
    # Some templates have a {% block sidebar %} that needs to be cleaned up or rebranded
    sidebar_pattern = re.compile(r'{% block sidebar %}.*?{% endblock %}', re.DOTALL)
    
    # Standard HaDerech Sidebar for result-related pages
    new_sidebar = """{% block sidebar %}
    <div class="menu-label">Main Menu</div>
    <a href="{% url 'portal:teacher_dashboard' %}" class="nav-item">
        <i class="fas fa-home"></i> Dashboard
    </a>
    <a href="{% url 'portal:teacher_result_entry' %}" class="nav-item active">
        <i class="fas fa-edit"></i> Enter Results
    </a>
    <div class="menu-label">Settings</div>
    <a href="{% url 'portal:change_password' %}" class="nav-item">
        <i class="fas fa-key"></i> Change Password
    </a>
{% endblock %}"""
    
    html = sidebar_pattern.sub(new_sidebar, html)

    # 2. Update page-title and card headers
    html = html.replace('bg-white border-bottom', 'card-header')
    html = html.replace('text-primary', 'primary-text') # We use primary-text for indigo in custom_theme usually or just rely on CSS
    
    # 3. Inject better score input styling if not present
    if '.score-input {' not in html:
        style_inject = """<style>
    .score-input {
        border: 1px solid var(--border-color) !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
        font-weight: 600 !important;
        transition: all 0.2s !important;
    }
    .score-input:focus {
        border-color: var(--primary-color) !important;
        box-shadow: 0 0 0 3px var(--primary-light) !important;
        outline: none !important;
    }
</style>"""
        html = html.replace('{% block content %}', '{% block content %}\n' + style_inject)

    # 4. Global Branding
    html = html.replace('SMRPS AI Assistant', f'{branding_name} AI Assistant')
    html = html.replace('SMRPS', branding_name)

    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(html)

# List of files to update
files_to_update = [
    r'portal\templates\portal\teacher_result_entry.html',
    r'portal\templates\portal\teacher_results_modern.html',
    r'portal\templates\portal\change_password.html',
    r'portal\templates\portal\unauthorized.html',
]

base_path = r'C:\Users\User\PycharmProjects\SMRPS'
for rel_path in files_to_update:
    abs_path = os.path.join(base_path, rel_path)
    if os.path.exists(abs_path):
        update_template(abs_path)
        print(f"Updated {rel_path}")

print("Phase 2 templates updated with HaDerech branding!")
