# Generated by Django 2.2.2 on 2019-06-15 15:34

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0013_auto_20190614_2132'),
    ]

    operations = [
        migrations.RenameField(
            model_name='profile',
            old_name='subscription',
            new_name='email_subscription',
        ),
    ]