# Generated by Django 2.2.2 on 2019-06-10 09:46

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0003_auto_20190610_0825'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='active',
            field=models.BooleanField(default=False),
        ),
    ]