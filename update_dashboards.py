import os
import re

# 1. Update Student Dashboard
student_file = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\student_dashboard.html'
new_student_html = """{% extends 'portal/base.html' %}
{% load static %}

{% block title %}My Dashboard - SMRPS{% endblock %}

{% block sidebar %}
    <a href="{% url 'portal:student_dashboard' %}" class="nav-item active">
        <i class="fas fa-th-large"></i> Student Dashboard
    </a>
    <a href="#" class="nav-item">
        <i class="fas fa-laptop-code"></i> CBT Practice
    </a>
    <a href="#" class="nav-item">
        <i class="fas fa-file-alt"></i> Assignment Submission
    </a>
    
    <div class="menu-label mt-4">ACADEMICS</div>
    <a href="#" class="nav-item">
        <i class="fas fa-chart-line"></i> Performance
    </a>
    <a href="#" class="nav-item">
        <i class="fas fa-calendar-check"></i> Attendance
    </a>
{% endblock %}

{% block content %}
<div class="container-fluid py-0 px-2">

    <!-- Greeting Card -->
    <div class="card border-0 mb-4 py-2 shadow-sm" style="border-radius: 16px;">
        <div class="card-body d-flex justify-content-between align-items-center">
            <div>
                <div class="d-flex align-items-center gap-3 mb-2">
                    <h4 class="mb-0 fw-bold" style="font-family: 'Poppins', sans-serif;">Welcome {{ student.first_name|upper }}, {{ student.last_name|upper }}</h4>
                    <span class="badge" style="background: var(--primary-light); color: var(--primary-color); font-size: 0.8rem; font-weight: 600;">{{ student.admission_number }}</span>
                </div>
                <p class="text-muted mb-0" style="font-size: 0.95rem;">Easily view your results, CBTs, and academic performance</p>
            </div>
            <div class="d-none d-md-flex align-items-center justify-content-center" style="width: 80px; height: 80px; background: var(--bg-main); border-radius: 20px;">
                <div style="font-size: 2rem; font-weight: 800; color: var(--primary-color);">{{ student.first_name|first }}{{ student.last_name|first }}</div>
            </div>
        </div>
    </div>

    <!-- Quicklinks Card -->
    <div class="card border-0 mb-4 shadow-sm" style="border-radius: 16px;">
        <div class="card-body">
            <h5 class="fw-bold mb-4" style="color: var(--text-dark); font-family: 'Poppins', sans-serif;">Quick Actions</h5>
            
            <div class="d-flex flex-wrap gap-2">
                <a href="{% url 'portal:download_cumulative_result' %}" class="action-pill shadow-sm">
                    <i class="fas fa-download text-primary"></i> Download Cumulative
                </a>
                
                <form id="cbtStartForm" onsubmit="event.preventDefault(); startCBT();" class="d-inline-flex m-0 align-items-center">
                    <select id="cbt_subject" name="subject_id" class="form-select form-select-sm border-0 bg-light me-2 rounded-pill px-3 py-2" required style="width: 150px; font-weight: 600; font-size: 0.9rem;">
                        <option value="">-- CBT Subject --</option>
                        {% for subj in student.school_class.class_subjects.all %}
                            <option value="{{ subj.subject.id }}">{{ subj.subject.name }}</option>
                        {% endfor %}
                    </select>
                    <button type="submit" class="action-pill shadow-sm border-0 m-0" style="background: #10b981; color: white;">
                        <i class="fas fa-play" style="color: white;"></i> Start Mock CBT
                    </button>
                </form>
            </div>
        </div>
    </div>

    <!-- Stats Horizontal Row -->
    <div class="row mb-4 g-4">
        <div class="col-md-4">
            <div class="stat-card shadow-sm border-0" style="border-radius: 16px;">
                <div class="stat-content">
                    <h6 style="color: var(--text-muted); text-transform: none; font-weight: 500;">Current Class</h6>
                    <h4 class="mb-0 fw-bold" style="color: var(--primary-color);">{{ student.school_class.name }}</h4>
                </div>
                <div class="stat-icon" style="background: transparent;">
                    <i class="fas fa-building" style="font-size: 3rem; color: var(--primary-light);"></i>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-card shadow-sm border-0" style="border-radius: 16px;">
                <div class="stat-content">
                    <h6 style="color: var(--text-muted); text-transform: none; font-weight: 500;">Current Session</h6>
                    <h4 class="mb-0 fw-bold" style="color: var(--teal-accent);">{{ current_session.name|default:'N/A' }}</h4>
                </div>
                <div class="stat-icon" style="background: transparent;">
                    <i class="fas fa-calendar-alt" style="font-size: 3rem; color: #ccfbf1;"></i>
                </div>
            </div>
        </div>
        <div class="col-md-4">
            <div class="stat-card shadow-sm border-0" style="border-radius: 16px;">
                {% with latest=summaries.first %}
                <div class="stat-content">
                    <h6 style="color: var(--text-muted); text-transform: none; font-weight: 500;">Latest Position</h6>
                    {% if latest and latest.position %}
                        <h4 class="mb-0 fw-bold" style="color: var(--warning-color);">{{ latest.position }}{% if latest.position == 1 %}st{% elif latest.position == 2 %}nd{% elif latest.position == 3 %}rd{% else %}th{% endif %}</h4>
                    {% else %}
                        <h4 class="mb-0 fw-bold text-muted">N/A</h4>
                    {% endif %}
                </div>
                <div class="stat-icon" style="background: transparent;">
                    <i class="fas fa-trophy" style="font-size: 3rem; color: #fef3c7;"></i>
                </div>
                {% endwith %}
            </div>
        </div>
    </div>

    <!-- Results Table -->
    <div class="card border-0 shadow-sm" style="border-radius: 16px;">
        <div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0;">
            <h5 class="fw-bold mb-0" style="color: var(--text-dark); padding-top: 0.5rem;">Academic Results History</h5>
        </div>
        <div class="card-body p-0">
            <div class="table-responsive">
                <table class="table table-hover mb-0" style="min-width: 600px;">
                    <thead style="background: var(--bg-main);">
                        <tr>
                            <th style="padding-left: 2rem; border-bottom: 0;">Session & Term</th>
                            <th style="border-bottom: 0;">Class</th>
                            <th style="border-bottom: 0;">Average Score</th>
                            <th style="border-bottom: 0;">Position</th>
                            <th class="text-end" style="padding-right: 2rem; border-bottom: 0;">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for summary in summaries %}
                        <tr>
                            <td style="padding-left: 2rem; vertical-align: middle;">
                                <div class="fw-bold text-dark">{{ summary.academic_session.name }}</div>
                                <small class="text-muted">{{ summary.term }} Term</small>
                            </td>
                            <td style="vertical-align: middle;">
                                <span class="badge" style="background: var(--primary-light); color: var(--primary-color); font-weight: 600;">{{ summary.school_class.name }}</span>
                            </td>
                            <td style="vertical-align: middle;">
                                <div class="fw-bold" style="color: var(--success-color);">{{ summary.average|floatformat:2 }}%</div>
                            </td>
                            <td style="vertical-align: middle;">
                                {% if summary.position %}
                                <div class="fw-bold" style="color: var(--warning-color);">
                                    {{ summary.position }}<small class="text-muted fw-normal">{% if summary.position == 1 %}st{% elif summary.position == 2 %}nd{% elif summary.position == 3 %}rd{% else %}th{% endif %}</small>
                                </div>
                                {% else %}
                                -
                                {% endif %}
                            </td>
                            <td class="text-end" style="padding-right: 2rem; vertical-align: middle;">
                                <a href="{% url 'portal:download_cumulative_result' %}" class="btn btn-sm btn-light border shadow-sm rounded-pill px-3 fw-bold" style="color: var(--primary-color);">
                                    <i class="fas fa-download me-1"></i> PDF
                                </a>
                            </td>
                        </tr>
                        {% empty %}
                        <tr>
                            <td colspan="5" class="text-center p-5 text-muted border-0">
                                <i class="fas fa-folder-open fa-3x mb-3 opacity-25"></i>
                                <p class="mb-0">Your academic results have not been published yet.</p>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</div>

<script>
    function startCBT() {
        var subjectId = document.getElementById('cbt_subject').value;
        if(subjectId) {
            window.location.href = '/academics/cbt/start/' + subjectId + '/';
        }
    }
</script>
{% endblock %}
"""
with open(student_file, 'w', encoding='utf-8') as f:
    f.write(new_student_html)


# 2. Update Admin Dashboard
admin_file = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\dashboard_admin.html'
with open(admin_file, 'r', encoding='utf-8') as f:
    admin_content = f.read()

# Replace Header
old_admin_header = r"""    <div class="page-title row align-items-center w-100 m-0">
        <div class="col-12 col-md-1 text-center mb-3 mb-md-0">
            <i class="fas fa-school"></i>
        </div>
        <div class="col-12 col-md-7 text-center text-md-start">
            <h2 class="mb-1">School Administration</h2>
            <p class="text-muted mb-0" style="font-size:0.9rem;">{{ request.user.school.name }} | <span class="badge bg-info">{{ total_students }} Students</span></p>
        </div>
        <div class="col-12 col-md-4 text-center text-md-end mt-3 mt-md-0">
            <a href="{% url 'portal:dashboard' %}" class="btn btn-outline-primary shadow-sm" style="border-radius: 8px;">
                <i class="fas fa-home"></i> Back to Home
            </a>
        </div>
    </div>"""

new_admin_header = """    <!-- HaDerech Welcome Card -->
    <div class="card border-0 mb-4 py-2 shadow-sm" style="border-radius: 16px;">
        <div class="card-body d-flex justify-content-between align-items-center">
            <div>
                <div class="d-flex align-items-center gap-3 mb-2">
                    <h4 class="mb-0 fw-bold" style="font-family: 'Poppins', sans-serif;">School Administration</h4>
                    <span class="badge" style="background: var(--primary-light); color: var(--primary-color); font-size: 0.8rem; font-weight: 600;">{{ total_students }} Students</span>
                </div>
                <p class="text-muted mb-0" style="font-size: 0.95rem;">{{ request.user.school.name }}</p>
            </div>
            <div class="d-none d-md-flex align-items-center justify-content-center" style="width: 80px; height: 80px; background: var(--bg-main); border-radius: 20px;">
                <i class="fas fa-school" style="font-size: 2.5rem; color: var(--primary-color); opacity: 0.7;"></i>
            </div>
        </div>
    </div>"""

if old_admin_header in admin_content:
    admin_content = admin_content.replace(old_admin_header, new_admin_header)

# Make all cards beautifully rounded and borderless with shadow-sm (following HaDerech styling)
admin_content = re.sub(r'<div class="card">', r'<div class="card border-0 shadow-sm" style="border-radius: 16px; margin-bottom: 24px;">', admin_content)
# Unify card-headers inside admin
admin_content = re.sub(r'<div class="card-header bg-primary text-white">', r'<div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0; padding-top: 1.25rem; border-bottom: 1px solid var(--border-color) !important;">', admin_content)
# We need to change the white text since bg-white makes the text invisible if it was meant to be white. Wait, the inner elements were text-white? 
# Usually I can just regex `<h5 class="mb-0">` to adapt. The previous bg-primary made text white, so the text inside is just plain white. If I remove bg-primary, text becomes dark.
admin_content = admin_content.replace('text-white">', '">') # Remove generic text-white
admin_content = admin_content.replace('<h5 class="mb-0 text-white">', '<h5 class="mb-0 fw-bold" style="color: var(--text-dark);">')
admin_content = admin_content.replace('<div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0; padding-top: 1.25rem; border-bottom: 1px solid var(--border-color) !important;">\n                            <h5 class="mb-0">', '<div class="card-header border-0 bg-white" style="border-radius: 16px 16px 0 0; padding-top: 1.25rem; border-bottom: 1px solid var(--border-color) !important;">\n                            <h5 class="mb-0 fw-bold" style="color: var(--text-dark);">')

with open(admin_file, 'w', encoding='utf-8') as f:
    f.write(admin_content)

print("Dashboards updated with unified HaDerech Indigo Theme successfully!")
