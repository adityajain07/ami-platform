# Generated by Django 4.2.2 on 2023-07-28 18:15

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0007_alter_taxalist_options_alter_taxon_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="taxalist",
            name="taxa",
            field=models.ManyToManyField(related_name="lists", to="main.taxon"),
        ),
    ]
