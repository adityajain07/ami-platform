# Generated by Django 4.2.2 on 2023-08-18 00:54

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0018_rename_source_sourceimage_public_url"),
    ]

    operations = [
        migrations.RenameField(
            model_name="sourceimage",
            old_name="public_url",
            new_name="public_base_url",
        ),
    ]
