# Generated by Django 2.2.2 on 2019-06-25 17:52

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('MainSite', '0002_auto_20190625_1750'),
    ]

    operations = [
        migrations.AlterField(
            model_name='characteristic',
            name='group',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='MainSite.CharacteristicGroup'),
        ),
    ]
