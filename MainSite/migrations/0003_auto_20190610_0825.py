# Generated by Django 2.2.2 on 2019-06-10 08:25

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0002_auto_20190609_2239'),
    ]

    operations = [
        migrations.AlterField(
            model_name='order',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
        migrations.AlterField(
            model_name='product',
            name='id',
            field=models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]
