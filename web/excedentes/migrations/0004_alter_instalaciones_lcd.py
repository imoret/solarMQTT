# Generated by Django 4.2.5 on 2024-11-12 18:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('excedentes', '0003_modos_dispositivos'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instalaciones',
            name='lcd',
            field=models.BooleanField(blank=True, default=True),
        ),
    ]
