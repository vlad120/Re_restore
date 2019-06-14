from django.http import JsonResponse
from datetime import datetime
import os
import logging
from PIL import Image


logger = logging.getLogger(__name__)

SITE_URL = 'https://new-store.ru/'

TOKEN_LEN = 70
LIMIT_PROFILE_PHOTO_SIZE = 10  # Мб, предельный размер загружаемого фото
MAX_PROFILE_PHOTO_SIZE = 1  # Мб, максимальный размер для хранения фото

# методы сортировки
ID_SORT = "ID"
DATA_SORT = "DATA"
NAME_SORT = "NAME"
PRICE_SORT = "PRICE"
POPULAR_SORT = "POPULAR"
NEW_SORT = "NEW"


# получение корректного пути
def to_path(*args, static=True):
    return os.path.join('static', *args) if static else os.path.join(*args)


# конвертирование корзины вида {'id1': n1, 'id2': n2} в строку
def basket_to_str(basket):
    return ';'.join(f'{product_id}*{basket[product_id]}' for product_id in basket) if basket else ''


# конвертирование строки вида 'id1*n1;id2*n2' в корзину
def str_to_basket(s):
    return dict([position.split('*') for position in s.split(';')]) if s else dict()


# конвертирование характеристики вида {'property1': value1, 'property2': value2} в строку
def characteristics_to_str(ch):
    return ';'.join(f'{prop}={ch[prop]}' for prop in ch) if ch else ''


# конвертирование строки вида 'property1=value1;property2=value2' в характеристики
def str_to_characteristics(s):
    return dict([prop.split('=') for prop in s.split(';')]) if s else dict()


# создание унифицированного ответа от API
def make_success(state=True, message='Ok', **kwargs):
    data = {'success': state}
    if message == 'Ok':
        message = 'Ok' if state else 'Unknown Error'
    data['message'] = message
    data.update(kwargs)
    return JsonResponse(data)


# генерация токена
def make_token():
    symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return "".join(list({i for i in symbols * 2})[:TOKEN_LEN])


# собрать полный url к ресурсу
def make_url(path: str):
    return SITE_URL + path.strip('/')


# сохранить объект вместе с датой изменения
def save_with_date(obj):
    try:
        obj.date_changes = datetime.now()
        obj.save()
        return True
    except Exception as e:
        logger.error(f"Save {obj} with date_changes error: {e}")
        return False


# сохранить фото из request.data
def save_photo(file, photo_path):
    with open(photo_path, 'wb+') as f:
        size = 0  # размер изображения в Мб
        for chunk in file.chunks():
            f.write(chunk)  # запись фото
            size += len(chunk) / 1024 / 1024
            # при превышении максимального размера загружаемого файла
            if size > LIMIT_PROFILE_PHOTO_SIZE:
                raise SizeError
        process_profile_photo(photo_path, size)  # обработка фото


# сжать фото до 1Мб и обрезать в квадрат
def process_profile_photo(photo_path, file_size):
    im = Image.open(photo_path)
    w, h = (int(val // file_size) for val in im.size)
    diff = abs(w - h) // 2
    # уменьшаем размер (по надобности)
    if file_size > MAX_PROFILE_PHOTO_SIZE:
        im = im.resize((w, h), Image.ANTIALIAS)
    # обрезаем до квадрата
    if w != h:
        im = im.crop((diff, 0, w - diff, h) if w > h else (0, diff, w, h - diff))
    # до полного квадрата
    w, h = im.size
    if w != h:
        diff = abs(w - h)
        im = im.crop((0, 0, w - diff, h) if w > h else (0, 0, w, h - diff))
    im.save(photo_path, 'PNG')


# получить ключ для сортировки найденных пользователей
def get_users_sort(sorting):
    if sorting == ID_SORT:
        return lambda profile: profile.user.id
    if sorting == NEW_SORT:
        return lambda profile: profile.user.date_joined
    if sorting == NAME_SORT:
        return lambda profile: (profile.user.first_name, profile.user.last_name)
    return lambda profile: profile.user.id  # по умолчанию


def optimize_phone(phone):
    return phone[phone.index('9'):] if '9' in phone else phone


def get_bool(val):
    a = val is True
    b = type(val) is str and val.lower() in {'true', 't', 'y', '+'}
    c = type(val) is str and val.isdigit() and int(val) > 0
    d = type(val) is int and val > 0
    if a or b or c or d:
        return True
    return False


class SizeError(Exception):
    pass


class ExtensionError(Exception):
    pass

