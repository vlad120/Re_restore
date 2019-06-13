from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from special import *


# пути к фотографиям по умолчанию
NO_GOODS_PHOTO = to_path('goods', 'NoPhoto.jpg')
NO_PROFILE_PHOTO = to_path('profiles', 'NoPhoto.jpg')


class Category(models.Model):
    name = models.CharField(max_length=80, primary_key=True)
    rus_name = models.CharField(max_length=100)
    parent = models.OneToOneField('Category', on_delete=models.PROTECT, blank=True, null=True)
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
    date_changes = models.DateTimeField(auto_now_add=True)

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
            d['characteristics'] = str_to_characteristics(self.characteristics)
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
                d['photo'] = to_path('goods', self.id, '1.png')
            else:
                d['photo'] = NO_GOODS_PHOTO
        if photos_req:
            if self.len_photos:
                folder = to_path('goods', str(self.id))
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
    user = models.ForeignKey('Profile', on_delete=models.SET_NULL, blank=True, null=True)
    order_spot = models.ForeignKey('OrderSpot', on_delete=models.PROTECT, blank=True, null=True)

    def __repr__(self):
        return '<Order {} {} {}rub>'.format(self.id, self.status, self.total)

    def __str__(self):
        return f'Order {self.id}'

    def to_dict(self, id_req=True, total_req=True, goods_req=True,
                status_req=True, user_req=True, order_spot_req=True):
        d = dict()
        if id_req:
            d['id'] = self.id
        if total_req:
            d['total'] = self.total
        if goods_req:
            d['goods'] = str_to_basket(self.goods)
        if status_req:
            d['status'] = self.status
        if user_req:
            d['user'] = self.user.profile.to_dict(username_req=True, phone_req=True)
        if order_spot_req:
            d['order_spot'] = self.order_spot.to_dict()
        return d

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"


class OrderSpot(models.Model):
    name = models.CharField(max_length=100)
    address = models.CharField(max_length=200)
    description = models.CharField(max_length=300)
    working_hours = models.CharField(max_length=200)
    volume = models.PositiveSmallIntegerField()  # количество мест для заказов
    state = models.CharField(max_length=10, default='active')

    def __repr__(self):
        return '<OrderSpot {} {} {}>'.format(self.id, self.name, self.state)

    def __str__(self):
        return f'OrderSpot {self.id}'

    def to_dict(self, id_req=True, name_req=True, address_req=False,
                description_req=False, working_hours_req=False,
                volume_req=False, state_req=True, all_req=False):
        if all_req:
            (id_req, name_req, address_req, description_req,
             working_hours_req, volume_req, state_req) = (True for _ in range(8))
        d = dict()
        if id_req:
            d['id'] = self.id
        if name_req:
            d['name'] = self.name
        if address_req:
            d['address'] = self.address
        if description_req:
            d['description'] = self.description
        if working_hours_req:
            d['working_ours'] = self.working_hours
        if volume_req:
            d['volume'] = self.volume
        if state_req:
            d['state'] = self.state
        return d

    class Meta:
        verbose_name = "Пункт выдачи"
        verbose_name_plural = "Пункты выдачи"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=12, unique=True, blank=True, null=True)
    subscription = models.BooleanField(default=True)
    photo = models.BooleanField(default=False)  # есть ли фото
    basket = models.CharField(max_length=2000, default='')
    date_changes = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=TOKEN_LEN, blank=True, null=True)
    is_users_editor = models.BooleanField(default=False)
    is_goods_editor = models.BooleanField(default=False)

    def __repr__(self):
        return '<UserProfile {} {}>'.format(self.user.id, self.user.username)

    def __str__(self):
        return f'User profile {self.user.id}'

    def to_dict(self, id_req=True, first_name_req=False, last_name_req=False,
                phone_req=False, email_req=False, username_req=True,
                photo_req=False, subscr_req=False, basket_req=False,
                token_req=False, status_req=False, all_req=False):
        if all_req:
            (id_req, first_name_req, last_name_req,
             email_req, phone_req, login_req,
             photo_req, subscr_req, basket_req,
             token_req, status_req) = (True for _ in range(11))
        d = dict()
        if id_req:
            d['id'] = self.user.id
        if first_name_req:
            d['first_name'] = self.user.first_name
        if last_name_req:
            d['last_name'] = self.user.last_name
        if phone_req:
            d['phone'] = self.phone
        if email_req:
            d['email'] = self.user.email
        if username_req:
            d['username'] = self.user.username
        if subscr_req:
            d['subscription'] = self.subscription
        if basket_req:
            d['basket'] = str_to_basket(self.basket)
        if token_req:
            d['token'] = self.token
        if status_req:
            d['status'] = {'staff': self.user.is_staff,
                           'goods_editor': self.is_goods_editor,
                           'users_editor': self.is_users_editor}
        if photo_req:
            if self.photo:
                d['photo'] = to_path('profiles', f'{self.id}.png?{self.date_changes}')
            else:
                d['photo'] = NO_PROFILE_PHOTO
        return d

    # получить названия полей в таблице
    def get_all_fields(self=None):
        return ('phone', 'subscription', 'photo',
                'basket', 'date_changes', 'tokens')

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
