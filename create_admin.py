import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from accounts.models import User

def create_admin():
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    password = os.environ.get('ADMIN_PASSWORD', 'adminpassword123')
    
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
