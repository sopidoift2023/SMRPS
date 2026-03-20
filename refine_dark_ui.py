import os

# New Dark Indigo colors
indigo_darkest = '#1e1b4b' # Indigo-950
indigo_deep = '#312e81'   # Indigo-900

# 1. Update Home
home_file = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\home.html'
with open(home_file, 'r', encoding='utf-8') as f:
    home_html = f.read()

# Replace Slate darks with Indigo darks
home_html = home_html.replace('#1e293b', indigo_deep)
home_html = home_html.replace('#0f172a', indigo_darkest)
home_html = home_html.replace('--primary-blue: #0f172a;', f'--primary-blue: {indigo_darkest};')

with open(home_file, 'w', encoding='utf-8') as f:
    f.write(home_html)

# 2. Update Login
login_file = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\login.html'
with open(login_file, 'r', encoding='utf-8') as f:
    login_html = f.read()

login_html = login_html.replace('#0f172a', indigo_darkest)
login_html = login_html.replace('#1e3a5f', indigo_deep)

with open(login_file, 'w', encoding='utf-8') as f:
    f.write(login_html)

print("Public pages refined with consistent Indigo dark themes!")
