# Generated by Django 5.0.1 on 2024-01-11 20:09

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="useraccount",
            name="is_staff",
        ),
    ]
