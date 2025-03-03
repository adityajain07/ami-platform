# Generated by Django 4.2.2 on 2023-07-28 20:00

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0008_taxalist_taxa"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="taxon",
            options={"ordering": ["ordering", "name"], "verbose_name_plural": "Taxa"},
        ),
        migrations.AddField(
            model_name="taxon",
            name="active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="taxon",
            name="synonym_of",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="synonyms",
                to="main.taxon",
            ),
        ),
        migrations.AlterField(
            model_name="taxon",
            name="name",
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
