# Generated by Django 2.2.2 on 2019-06-12 14:53

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0008_auto_20190612_1309'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='profile',
            name='status',
        ),
    ]
