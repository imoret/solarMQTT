# Generated by Django 4.2.5 on 2024-11-25 17:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('excedentes', '0007_remove_dispositivos_mododia_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='dispositivos',
            name='tiempo_reaccion',
            field=models.FloatField(default=1),
        ),
    ]