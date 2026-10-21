"""Mark accounts that existed before email verification was introduced as verified.

Migration 0007 added ``is_email_verified`` with a default of False, which locked every
existing account out of login. Users who joined before 0007 was applied never received
a verification email, so they are treated as verified. Accounts created afterwards are
left alone and still have to verify.
"""

from django.db import migrations
from django.db.migrations.recorder import MigrationRecorder


def mark_existing_users_verified(apps, schema_editor):
    User = apps.get_model("users", "User")
    recorder = MigrationRecorder(schema_editor.connection)
    record = recorder.migration_qs.filter(
        app="users",
        name="0007_user_is_email_verified",
    ).first()
    if record is None:
        return
    User.objects.filter(
        is_email_verified=False,
        date_joined__lt=record.applied,
    ).update(is_email_verified=True)


class Migration(migrations.Migration):
    dependencies = [
        ("users", "0007_user_is_email_verified"),
    ]

    operations = [
        migrations.RunPython(mark_existing_users_verified, migrations.RunPython.noop),
    ]
