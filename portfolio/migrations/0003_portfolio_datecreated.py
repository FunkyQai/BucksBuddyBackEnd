# Generated by Django 5.0.1 on 2024-01-24 10:20

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        (
            "portfolio",
            "0002_remove_asset_value_asset_averageprice_asset_sector_and_more",
        ),
    ]

    operations = [
        migrations.AddField(
            model_name="portfolio",
            name="dateCreated",
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
    ]