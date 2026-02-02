import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User
for user in User.objects.all():
    print(f"Username: {user.username}, Role: {user.role}")
