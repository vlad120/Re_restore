# Generated by Django 2.2.2 on 2019-06-14 21:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0012_auto_20190614_2056'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(blank=True, max_length=10, null=True, unique=True),
        ),
    ]
