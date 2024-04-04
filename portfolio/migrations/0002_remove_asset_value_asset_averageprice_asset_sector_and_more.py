# Generated by Django 5.0.1 on 2024-01-22 13:56

import django.db.models.deletion
import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("portfolio", "0001_initial"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="asset",
            name="value",
        ),
        migrations.AddField(
            model_name="asset",
            name="averagePrice",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="asset",
            name="sector",
            field=models.CharField(default="Others", max_length=50),
        ),
        migrations.AddField(
            model_name="asset",
            name="ticker",
            field=models.CharField(default="btc", max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="asset",
            name="type",
            field=models.CharField(default="Others", max_length=50),
        ),
        migrations.AddField(
            model_name="asset",
            name="units",
            field=models.DecimalField(decimal_places=5, default=0, max_digits=20),
        ),
        migrations.AddField(
            model_name="portfolio",
            name="remarks",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.CreateModel(
            name="Transaction",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[("buy", "Buy"), ("sell", "Sell")], max_length=10
                    ),
                ),
                ("units", models.DecimalField(decimal_places=5, max_digits=20)),
                ("price", models.DecimalField(decimal_places=2, max_digits=12)),
                (
                    "fee",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
                (
                    "transaction_date",
                    models.DateTimeField(default=django.utils.timezone.now),
                ),
                (
                    "asset",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to="portfolio.asset",
                    ),
                ),
                (
                    "portfolio",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="portfolio.portfolio",
                    ),
                ),
            ],
        ),
    ]
