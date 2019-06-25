# Generated by Django 2.2.2 on 2019-06-25 17:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('name', models.CharField(max_length=80, primary_key=True, serialize=False, unique=True)),
                ('rus_name', models.CharField(max_length=100)),
                ('characteristics', models.TextField(blank=True, max_length=3000, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('parent', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='MainSite.Category')),
            ],
            options={
                'verbose_name': 'Категория',
                'verbose_name_plural': 'Категории',
            },
        ),
        migrations.CreateModel(
            name='Characteristic',
            fields=[
                ('name', models.CharField(max_length=50, primary_key=True, serialize=False)),
                ('rus', models.CharField(max_length=50)),
                ('value_type', models.CharField(max_length=6)),
            ],
            options={
                'verbose_name': 'Характеристика',
                'verbose_name_plural': 'Характеристики',
            },
        ),
        migrations.CreateModel(
            name='OrderSpot',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('address', models.CharField(max_length=200)),
                ('description', models.CharField(max_length=300)),
                ('working_hours', models.CharField(max_length=200)),
                ('volume', models.PositiveSmallIntegerField()),
                ('curr_volume', models.PositiveSmallIntegerField()),
                ('state', models.CharField(default='active', max_length=10)),
            ],
            options={
                'verbose_name': 'Пункт выдачи',
                'verbose_name_plural': 'Пункты выдачи',
            },
        ),
        migrations.CreateModel(
            name='Producer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('phone', models.CharField(blank=True, max_length=12, null=True)),
                ('email', models.CharField(blank=True, max_length=254, null=True)),
                ('has_photo', models.BooleanField(default=False)),
            ],
            options={
                'verbose_name': 'Производитель',
                'verbose_name_plural': 'Производители',
            },
        ),
        migrations.CreateModel(
            name='Product',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('description', models.TextField(max_length=15000)),
                ('short_description', models.CharField(max_length=120)),
                ('characteristics', models.TextField(max_length=7000)),
                ('price', models.PositiveIntegerField()),
                ('count', models.PositiveIntegerField()),
                ('bought', models.PositiveIntegerField(default=0)),
                ('is_active', models.BooleanField(default=True)),
                ('len_photos', models.PositiveSmallIntegerField(default=0)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('date_changes', models.DateTimeField(auto_now=True)),
                ('category', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='MainSite.Category')),
                ('producer', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='MainSite.Producer')),
            ],
            options={
                'verbose_name': 'Товар',
                'verbose_name_plural': 'Товары',
            },
        ),
        migrations.CreateModel(
            name='Rate',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('general', models.PositiveSmallIntegerField()),
                ('content', models.CharField(blank=True, max_length=300, null=True)),
                ('len_photos', models.PositiveSmallIntegerField(blank=True, default=0)),
                ('status', models.CharField(default='MOD', max_length=3)),
                ('date_created', models.DateField(auto_now_add=True)),
                ('product', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='MainSite.Product')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Отзыв',
                'verbose_name_plural': 'Отзывы',
            },
        ),
        migrations.CreateModel(
            name='Profile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(blank=True, max_length=12, null=True, unique=True)),
                ('email_subscription', models.BooleanField(default=True)),
                ('has_photo', models.BooleanField(default=False)),
                ('basket', models.CharField(default='', max_length=2000)),
                ('date_changes', models.DateTimeField(auto_now_add=True)),
                ('token', models.CharField(blank=True, max_length=70, null=True)),
                ('is_users_editor', models.BooleanField(default=False)),
                ('is_goods_editor', models.BooleanField(default=False)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Профиль пользователя',
                'verbose_name_plural': 'Профили пользователей',
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('total', models.PositiveIntegerField()),
                ('products', models.CharField(max_length=2000)),
                ('status', models.CharField(default='processing', max_length=10)),
                ('date_created', models.DateTimeField(auto_now_add=True)),
                ('order_spot', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to='MainSite.OrderSpot')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Заказ',
                'verbose_name_plural': 'Заказы',
            },
        ),
    ]
