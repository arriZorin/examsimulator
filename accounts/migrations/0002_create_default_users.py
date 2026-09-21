from django.contrib.auth.hashers import make_password
from django.db import migrations


def create_default_users(apps, schema_editor):
    User = apps.get_model("auth", "User")
    StudentProfile = apps.get_model("accounts", "StudentProfile")

    admin, _ = User.objects.get_or_create(username="admin")
    admin.password = make_password("admin123")
    admin.is_active = True
    admin.is_staff = True
    admin.is_superuser = True
    admin.save(update_fields=["password", "is_active", "is_staff", "is_superuser"])

    user, _ = User.objects.get_or_create(username="user")
    user.password = make_password("user123")
    user.is_active = True
    user.is_staff = False
    user.is_superuser = False
    user.save(update_fields=["password", "is_active", "is_staff", "is_superuser"])
    StudentProfile.objects.get_or_create(user=user, defaults={"full_name": "User"})


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(create_default_users, migrations.RunPython.noop),
    ]
