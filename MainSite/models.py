from django.db import models
from json import loads
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


# пути к фотографиям по умолчанию
NO_GOODS_PHOTO = '/static/goods/NoPhoto.jpg'
NO_PROFILE_PHOTO = '/static/profiles/NoPhoto.jpg'


class Category(models.Model):
    name = models.CharField(max_length=80, primary_key=True)
    rus_name = models.CharField(max_length=100)
    parent = models.OneToOneField('Category', on_delete=models.PROTECT, null=True)
    active = models.BooleanField(default=False)

    def __repr__(self):
        return '<Category {}>'.format(self.name)

    def __str__(self):
        return f'Category {self.name}'

    def to_dict(self, name_req=True, rus_name_req=True,
                link_req=True, active_req=False):
        d = dict()
        if name_req:
            d['name'] = self.name
        if rus_name_req:
            d['rus_name'] = self.rus_name
        if link_req:
            link = [self.name]
            curr = self
            while curr.parent:  # собираем родительские категории
                curr = curr.parent
                link.append(curr.name)
            # переворачиваем полученные категории и собираем ссылку
            d['link'] = '/' + '/'.join(reversed(link))
        if active_req:
            d['active'] = self.active
        return d

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Product(models.Model):
    name = models.CharField(max_length=80)
    description = models.CharField(max_length=15000)
    short_description = models.CharField(max_length=120)
    characteristics = models.CharField(max_length=7000)
    price = models.PositiveIntegerField()
    count = models.PositiveIntegerField()
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    len_photos = models.PositiveSmallIntegerField(default=0)  # количество фото
    date_added = models.DateField(auto_now_add=True)
    date_changes = models.DateField(auto_now_add=True)

    def __repr__(self):
        return '<Product {} {} {} * {}rub>'.format(self.id, self.name, self.count, self.price)

    def __str__(self):
        return f'Product {self.name}'

    def to_dict(self, id_req=True, name_req=True, description_req=False,
                short_description_req=False, characteristics_req=False,
                price_req=True, count_req=True, category_name_req=True,
                category_req=False, full_link_req=False,
                photo_req=False, photos_req=False, all_req=False):
        if all_req:
            (id_req, name_req, description_req, short_description_req, characteristics_req,
             price_req, count_req, category_name_req, category_req, full_link_req,
             photo_req, photos_req) = (True for _ in range(12))
        d = dict()
        if id_req:
            d['id'] = self.id
        if name_req:
            d['name'] = self.name
        if description_req:
            d['description'] = self.description
        if short_description_req:
            d['short_description'] = self.short_description
        if characteristics_req:
            d['characteristics'] = loads(self.characteristics)
        if price_req:
            d['price'] = self.price
        if count_req:
            d['count'] = self.count
        if category_name_req:
            d['category_name'] = self.category.name
        if category_req:
            d['category'] = self.category.to_dict()
        if full_link_req:
            d['full_link'] = f'/{self.category.name}/{self.id}'
        if photo_req:
            if self.len_photos:
                d['photo'] = f'/static/goods/{self.id}/1.png'
            else:
                d['photo'] = NO_GOODS_PHOTO
        if photos_req:
            if self.len_photos:
                folder = f'/static/goods/{self.id}'
                d['photos'] = [folder + f'/{i}.png?{self.date_changes}'
                               for i in range(1, self.len_photos + 1)]
            else:
                d['photos'] = [NO_GOODS_PHOTO]
        return d

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"


class Order(models.Model):
    total = models.PositiveIntegerField()
    goods = models.CharField(max_length=2000)
    status = models.CharField(max_length=10, default="processing")
    user = models.ForeignKey('Profile', on_delete=models.SET_NULL, null=True)

    def __repr__(self):
        return '<Order {} {} {}rub>'.format(self.id, self.status, self.total)

    def __str__(self):
        return f'Order {self.id}'

    def to_dict(self, id_req=True, total_req=True, goods_req=True,
                status_req=True, user_req=True):
        d = dict()
        if id_req:
            d['id'] = self.id
        if total_req:
            d['total'] = self.total
        if goods_req:
            d['goods'] = loads(self.goods)
        if status_req:
            d['status'] = self.status
        if user_req:
            d['user'] = self.user.to_dict(login_req=True, phone_req=True)
        return d

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=12, unique=True)
    subscription = models.BooleanField(default=True)
    photo = models.BooleanField(default=False)  # есть ли фото
    basket = models.CharField(max_length=2000, default='{"basket": []}')
    date_created = models.DateField(auto_now_add=True)
    date_changes = models.DateField(auto_now_add=True)

    def __repr__(self):
        return '<UserProfile {} {}>'.format(self.user.id, self.user.username)

    def __str__(self):
        return f'User {self.user.id}'

    def to_dict(self, id_req=True, name_req=False, surname_req=False,
                phone_req=False, email_req=False, login_req=False,
                photo_req=False, subscr_req=False, all_req=False):
        if all_req:
            (id_req, name_req, surname_req, email_req,
             phone_req, login_req, photo_req, subscr_req) = (True for _ in range(8))
        d = dict()
        if id_req:
            d['id'] = self.user.id
        if name_req:
            d['name'] = self.user.first_name
        if surname_req:
            d['surname'] = self.user.last_name
        if phone_req:
            d['phone'] = self.phone
        if email_req:
            d['email'] = self.user.email
        if login_req:
            d['login'] = self.user.username
        if subscr_req:
            d['subscription'] = self.subscription
        if photo_req:
            if self.photo:
                d['photo'] = '/static/profiles/{}.png?{}'.format(self.id, self.date_changes)
            else:
                d['photo'] = NO_PROFILE_PHOTO
        return d

    class Meta:
        verbose_name = "Профиль пользователя"
        verbose_name_plural = "Профили пользователей"


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()
