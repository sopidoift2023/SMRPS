import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

superusers = User.objects.filter(is_superuser=True)
if superusers.exists():
    print(" Superuser(s) found:")
    for user in superusers:
        print(f"   - {user.username}")
else:
    print(" No superusers found. Create one with: python manage.py createsuperuser")
