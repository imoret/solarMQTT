# Generated by Django 4.2.5 on 2024-11-12 18:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('excedentes', '0004_alter_instalaciones_lcd'),
    ]

    operations = [
        migrations.AlterField(
            model_name='actuadores',
            name='puerto',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AlterField(
            model_name='instalaciones',
            name='lcd',
            field=models.BooleanField(default=True),
        ),
    ]
