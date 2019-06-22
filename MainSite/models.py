from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from special import *


# пути к фотографиям по умолчанию
NO_GOODS_PHOTO = to_path('goods', 'NoPhoto.jpg')
NO_PROFILE_PHOTO = to_path('profiles', 'NoPhoto.jpg')


def is_need_field(f, all_req, fields, kwargs):
    """ Основа функции для проверки на необходимость включения парметра
    в ответ от метода to_dict конкретной модели:
        если поле есть в fields или необходимы все поля (all_req),
    но при том поля нет в исключениях (f=False/f=None в kwargs)
    """
    if f in fields or (all_req and kwargs.get(f, True)):
        return True
    return False


class Category(models.Model):
    name = models.CharField(max_length=80, primary_key=True, unique=True)
    rus_name = models.CharField(max_length=100)
    parent = models.OneToOneField('Category', on_delete=models.PROTECT, blank=True, null=True)
    characteristics = models.CharField(max_length=3000)
    en_rus_characteristics = models.CharField(max_length=3000)
    is_active = models.BooleanField(default=True)

    def __repr__(self):
        return '<Category {}>'.format(self.name)

    def __str__(self):
        return f'Category {self.name}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('name'):
            d['name'] = self.name
        if is_need('rus_name'):
            d['rus_name'] = self.rus_name
        if is_need('link'):
            link = [self.name]
            curr = self
            while curr.parent:  # собираем родительские категории
                curr = curr.parent
                link.append(curr.name)
            # переворачиваем полученные категории и собираем ссылку
            if api:
                d['link'] = make_abs_url('/'.join(reversed(link)))
            else:
                d['link'] = '/'.join(reversed(link))
        if is_need('all_links'):
            categories = [self]
            curr = self
            while curr.parent:  # собираем родительские категории
                curr = curr.parent
                categories.append(curr)
            # переворачиваем полученные категории и преобразуем в ссылки
            d['link'] = [c.to_dict('link',  api=api).get('link') for c in reversed(categories)]
        if is_need('characteristics'):
            d['en_rus_characteristics'] = str_to_properties(self.en_rus_characteristics)
            d['characteristics'] = str_to_properties(self.characteristics)
        if is_need('active'):
            d['active'] = self.is_active
        return d

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"


class Producer(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=10, blank=True, null=True)
    email = models.CharField(max_length=254, blank=True, null=True)

    def __repr__(self):
        return '<Producer #{} {}>'.format(self.id, self.name)

    def __str__(self):
        return f'Producer #{self.id}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        # api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('name'):
            d['name'] = self.name
        if is_need('phone'):
            d['phone'] = self.phone
        if is_need('email'):
            d['email'] = self.email

    class Meta:
        verbose_name = "Производитель"
        verbose_name_plural = "Производители"


class Product(models.Model):
    name = models.CharField(max_length=80)
    producer = models.ForeignKey('Producer', on_delete=models.PROTECT)
    description = models.CharField(max_length=15000)
    short_description = models.CharField(max_length=120)
    characteristics = models.CharField(max_length=7000)
    price = models.PositiveIntegerField()
    count = models.PositiveIntegerField()
    bought = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    len_photos = models.PositiveSmallIntegerField(default=0)  # количество фото
    date_created = models.DateField(auto_now_add=True)
    date_changes = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return '<Product #{} {} {} * {}rub>'.format(self.id, self.name, self.count, self.price)

    def __str__(self):
        return f'Product #{self.id}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('name'):
            d['name'] = self.name
        if is_need('producer'):
            d['producer'] = self.producer.name
        if is_need('description'):
            d['description'] = self.description
        if is_need('short_description'):
            d['short_description'] = self.short_description
        if is_need('characteristics'):
            d['characteristics'] = str_to_properties(self.characteristics)
        if is_need('price'):
            d['price'] = self.price
        if is_need('count'):
            d['count'] = self.count
        if is_need('bought'):
            d['bought'] = self.bought
        if is_need('active'):
            d['is_active'] = self.is_active
        if is_need('category_name'):
            d['category_name'] = self.category.name
        if is_need('category'):
            d['category'] = self.category.to_dict(all=True, characteristics=False)
        if is_need('link'):
            d['link'] = f'{self.category.name}/{self.id}'
            if api:
                d['full_link'] = make_abs_url(d['full_link'])
        if is_need('photo'):
            if self.len_photos:
                d['photo'] = to_path('goods', self.id, '1.png')
            else:
                d['photo'] = NO_GOODS_PHOTO
            if api:
                d['photo'] = make_abs_url(d['photo'])
        if is_need('photos'):
            if self.len_photos:
                folder = to_path('goods', str(self.id))
                if api:
                    d['photos'] = [make_abs_url(f'{folder}/{i}.png?{self.date_changes}')
                                   for i in range(1, self.len_photos + 1)]
                else:
                    d['photos'] = [f'{folder}/{i}.png?{self.date_changes}'
                                   for i in range(1, self.len_photos + 1)]
            else:
                d['photos'] = [make_abs_url(NO_GOODS_PHOTO) if api else NO_GOODS_PHOTO]
        if is_need('date_created'):
            d['date_created'] = str(self.date_created)
        return d

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"


class Rate(models.Model):
    general = models.PositiveSmallIntegerField(max_length=10)
    content = models.CharField(max_length=300, blank=True, null=True)
    len_photos = models.PositiveSmallIntegerField(max_length=5, default=0, blank=True)
    product = models.OneToOneField(Product, on_delete=models.CASCADE)
    status = models.CharField(max_length=3, default="MOD")  # MOD (moderate) / REF (refused) / OK
    user = models.ForeignKey('User', on_delete=models.SET_NULL)
    date_created = models.DateField(auto_now_add=True)

    def __repr__(self):
        return '<Rate #{} {} from user #{}>'.format(self.id, '*' * self.general, self.user_id)

    def __str__(self):
        return f'Rate #{self.id}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('general'):
            d['general'] = self.general
        if is_need('content'):
            d['content'] = self.content
        if is_need('photos'):
            if not self.len_photos:
                d['photos'] = []
            else:
                photos = []
                if api:
                    for i in range(self.len_photos):
                        photos.append(make_abs_url(to_path('rates', f'{self.id}.png')))  # абсолютный путь
                else:
                    for i in range(self.len_photos):
                        photos.append(to_path('rates', f'{self.id}.png'))
                d['photos'] = photos
        if is_need('product'):
            d['product'] = self.product.to_dict('name', 'link', api=api)
        if is_need('status'):
            d['status'] = self.status
        if is_need('user'):
            d['user'] = self.user.profile.to_dict('username')
        if is_need('date_created'):
            d['date_created'] = str(self.date_created)
        return d

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"


class Order(models.Model):
    total = models.PositiveIntegerField()
    products = models.CharField(max_length=2000)
    status = models.CharField(max_length=10, default="processing")
    user = models.ForeignKey('User', on_delete=models.SET_NULL, blank=True, null=True)
    order_spot = models.ForeignKey('OrderSpot', on_delete=models.PROTECT, blank=True, null=True)
    date_created = models.DateTimeField(auto_now_add=True)

    def __repr__(self):
        return '<Order #{} {} {}rub>'.format(self.id, self.status, self.total)

    def __str__(self):
        return f'Order #{self.id}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('total'):
            d['total'] = self.total
        if is_need('products'):
            d['products'] = str_to_basket(self.products)
        if is_need('status'):
            d['status'] = self.status
        if is_need('user'):
            d['user'] = self.user.profile.to_dict('username', 'phone', 'email')
        if is_need('order_sport'):
            d['order_spot'] = self.order_spot.to_dict(all=True, volume=False)
        if is_need('date_created'):
            d['date_created'] = str(self.date_created)
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
    curr_volume = models.PositiveSmallIntegerField()
    state = models.CharField(max_length=10, default='active')

    def __repr__(self):
        return '<OrderSpot #{} {} {}>'.format(self.id, self.name, self.state)

    def __str__(self):
        return f'OrderSpot #{self.id}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('name'):
            d['name'] = self.name
        if is_need('address'):
            d['address'] = self.address
        if is_need('description'):
            d['description'] = self.description
        if is_need('working_ours'):
            d['working_ours'] = self.working_hours
        if is_need('volume'):
            d['volume'] = self.volume
        if is_need('curr_volume'):
            d['curr_volume'] = self.curr_volume
        if is_need('state'):
            d['state'] = self.state
        return d

    class Meta:
        verbose_name = "Пункт выдачи"
        verbose_name_plural = "Пункты выдачи"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    phone = models.CharField(max_length=10, unique=True, blank=True, null=True)
    email_subscription = models.BooleanField(default=True)
    has_photo = models.BooleanField(default=False)  # есть ли фото
    basket = models.CharField(max_length=2000, default='')
    date_changes = models.DateTimeField(auto_now_add=True)
    token = models.CharField(max_length=TOKEN_LEN, blank=True, null=True)
    is_users_editor = models.BooleanField(default=False)
    is_goods_editor = models.BooleanField(default=False)

    def __repr__(self):
        return '<UserProfile #{} {}>'.format(self.user.id, self.user.username)

    def __str__(self):
        return f'User profile #{self.user.id}'

    def to_dict(self, *fields, **kwargs):
        d = {'id': self.id}
        all_req = kwargs.pop('all', False)
        api = kwargs.pop('api', False)
        is_need = lambda f: is_need_field(f, all_req, fields, kwargs)

        if is_need('first_name'):
            d['first_name'] = self.user.first_name
        if is_need('last_name'):
            d['last_name'] = self.user.last_name
        if is_need('phone'):
            d['phone'] = '+7' + self.phone
        if is_need('email'):
            d['email'] = self.user.email
        if is_need('username'):
            d['username'] = self.user.username
        if is_need('email_subscription'):
            d['email_subscription'] = self.email_subscription
        if is_need('basket'):
            d['basket'] = str_to_basket(self.basket)
        if is_need('token'):
            d['token'] = self.token
        if is_need('status'):
            d['status'] = {'staff': self.user.is_staff,
                           'goods_editor': self.is_goods_editor,
                           'users_editor': self.is_users_editor}
        if is_need('last_login'):
            d['last_login'] = str(self.user.last_login)
        if is_need('photo'):
            if self.has_photo:
                if api:
                    # абсолютный путь
                    d['photo'] = make_abs_url(to_path('profiles', f'{self.id}.png?{self.date_changes}'))
                else:
                    d['photo'] = to_path('profiles', f'{self.id}.png?{self.date_changes}')
            else:
                if api:
                    # абсолютный путь
                    d['photo'] = make_abs_url(NO_PROFILE_PHOTO)
                else:
                    d['photo'] = NO_PROFILE_PHOTO
        if is_need('date_joined'):
            d['date_joined'] = str(self.user.date_joined)
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
