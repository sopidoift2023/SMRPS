import os
import re

# Colors
indigo = '#4f46e5'
teal = '#0d9488'
purple_soft = '#8b5cf6' # Keeping some purple for gradients but shifting towards the primary indigo

# 1. Update Login
login_file = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\login.html'
with open(login_file, 'r', encoding='utf-8') as f:
    login_html = f.read()

# Replace primary blue with indigo
login_html = login_html.replace('#3b82f6', indigo)
# Replace gradient companion if needed, or just let it be indigo-purple
login_html = login_html.replace('#06b6d4', teal) # Teal instead of cyan

with open(login_file, 'w', encoding='utf-8') as f:
    f.write(login_html)

# 2. Update Home
home_file = r'C:\Users\User\PycharmProjects\SMRPS\portal\templates\portal\home.html'
with open(home_file, 'r', encoding='utf-8') as f:
    home_html = f.read()

# Replace accent blue with indigo
home_html = home_html.replace('#3b82f6', indigo)
# Replace secondary cyan/teal etc
home_html = home_html.replace('--accent-blue: #3b82f6;', f'--accent-blue: {indigo};')
home_html = home_html.replace('--accent-purple: #8b5cf6;', f'--accent-teal: {teal};')
# Update gradients
home_html = home_html.replace('var(--accent-purple)', 'var(--accent-teal)')

with open(home_file, 'w', encoding='utf-8') as f:
    f.write(home_html)

print("Public pages updated with HaDerech Indigo/Teal theme!")
