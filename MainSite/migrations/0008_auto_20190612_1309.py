# Generated by Django 2.2.2 on 2019-06-12 13:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0007_auto_20190612_1305'),
    ]

    operations = [
        migrations.AlterField(
            model_name='profile',
            name='phone',
            field=models.CharField(max_length=12, null=True, unique=True),
        ),
    ]
