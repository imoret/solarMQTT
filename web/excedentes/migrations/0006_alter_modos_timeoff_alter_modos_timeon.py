# Generated by Django 4.2.5 on 2024-11-12 19:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('excedentes', '0005_alter_actuadores_puerto_alter_instalaciones_lcd'),
    ]

    operations = [
        migrations.AlterField(
            model_name='modos',
            name='timeOff',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='modos',
            name='timeOn',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
    ]