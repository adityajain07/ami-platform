# Generated by Django 4.2.2 on 2023-08-24 03:12

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0029_remove_sourceimage_unique_deployment_timestamp_and_more"),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name="sourceimage",
            name="main_source_event_i_6ca966_idx",
        ),
        migrations.AddIndex(
            model_name="sourceimage",
            index=models.Index(fields=["deployment", "timestamp"], name="main_source_deploym_2887d6_idx"),
        ),
        migrations.AddIndex(
            model_name="sourceimage",
            index=models.Index(fields=["event", "timestamp"], name="main_source_event_i_ab7d5d_idx"),
        ),
    ]
