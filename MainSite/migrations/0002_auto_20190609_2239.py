# Generated by Django 2.2.2 on 2019-06-09 22:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='profile',
            options={'verbose_name': 'Профиль пользователя', 'verbose_name_plural': 'Профили пользователей'},
        ),
    ]