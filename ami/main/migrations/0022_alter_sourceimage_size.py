# Generated by Django 4.2.2 on 2023-08-18 20:17

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0021_deployment_data_source_last_checked_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sourceimage",
            name="size",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]
