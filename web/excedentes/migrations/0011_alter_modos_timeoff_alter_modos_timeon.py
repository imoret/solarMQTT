# Generated by Django 4.2.5 on 2024-11-25 18:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('excedentes', '0010_alter_modos_timeoff_alter_modos_timeon'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modos',
            name='timeOff',
            field=models.JSONField(blank=True, default=[], null=True),
        ),
        migrations.AlterField(
            model_name='modos',
            name='timeOn',
            field=models.JSONField(blank=True, default=[], null=True),
        ),
    ]
