import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

def create_admin():
    username = os.environ.get('ADMIN_USERNAME')
    email = os.environ.get('ADMIN_EMAIL')
    password = os.environ.get('ADMIN_PASSWORD')
    
    if not username:
        raise ValueError("ADMIN_USERNAME environment variable is missing or empty.")
    if not email:
        raise ValueError("ADMIN_EMAIL environment variable is missing or empty.")
    if not password:
        raise ValueError("ADMIN_PASSWORD environment variable is missing or empty.")
    
    try:
        user = User.objects.get(username=username)
        print(f"Superuser {username} already exists. Updating password/email.")
        user.email = email
        user.set_password(password)
        user.is_superuser = True
        user.is_staff = True
        user.save()
        print("Superuser updated successfully!")
    except User.DoesNotExist:
        print(f"Creating superuser: {username}")
        User.objects.create_superuser(username=username, email=email, password=password)
        print("Superuser created successfully!")

if __name__ == "__main__":
    create_admin()
