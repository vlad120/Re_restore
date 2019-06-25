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

BASE_CHARACTERISTICS = [
    'weight', 'made_in',
    'warranty', 'color'
]


# получение корректного пути
def to_path(*args, static=True):
    return os.path.join('static', *args) if static else os.path.join(*args)


# конвертирование корзины вида {'id1': n1, 'id2': n2}
# в строку (для Profile)
def basket_to_str(basket):
    return ';'.join(f'{product_id}*{basket[product_id]}' for product_id in basket) if basket else ''


# конвертирование строки вида 'id1*n1;id2*n2'
# в корзину (для Profile)
def str_to_basket(s):
    return dict([position.split('*') for position in s.split(';')]) if s else dict()


# конвертирование характеристики вида {'property1': value1, 'property2': value2}
# в строку (для Product)
def properties_to_str(ch):
    return ';'.join(f'{prop.strip()}={ch[prop].strip()}' for prop in ch) if ch else ''


# конвертирование строки вида 'property1=value1;property2=value2'
# в характеристики (для Product)
def str_to_properties(s):
    d = dict()
    for prop in s.split(';'):
        key, val = tuple(prop.split('='))
        d[key.strip()] = val.strip()
    return d


def split_values_from_str(s, char=';'):
    return [val.strip() for val in s.split(char)]


def join_values_to_str(s, char=';'):
    return char.join([val.strip() for val in s])


# генерация токена
def make_token():
    symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    return "".join(list({i for i in symbols * 2})[:TOKEN_LEN])


# собрать полный url к ресурсу
def make_abs_url(path: str):
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


# оптимизация переданных в запросе параметров {'param': ['e']} -> {'param': 'e'};
# {'param': ['e1', 'e2', 'e3']}
# strict=True -> {'param': 'e1'};
# strict=False  -> {'param': ['e1', 'e2', 'e3']}
def get_params(request, strict=True, find_complex=False):
    params = dict(request.query_params)
    for arg in params:
        if type(params[arg]) is list and \
                (strict or (not strict and len(params[arg]) == 1)):
            params[arg] = params[arg][0]
        # если надо найти несколько аргументов в одном параметре
        if find_complex and ',' in params[arg]:
            param = [i.strip() for i in params[arg].split(',')]
            for i in range(len(param)):
                for param_type in {int, float}:
                    try:
                        param[i] = param_type(param[i])
                        break
                    except ValueError:
                        continue
            params[arg] = param
    return params


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
        return lambda user: user.id
    if sorting == NEW_SORT:
        return lambda user: user.date_joined
    if sorting == NAME_SORT:
        return lambda user: (user.first_name, user.last_name)
    return lambda user: user.id  # по умолчанию


# получить ключ для сортировки найденных пользователей
def get_products_sort(sorting):
    if sorting == ID_SORT:
        return lambda product: product.id
    if sorting == NEW_SORT:
        return lambda product: product.date_joined
    if sorting == NAME_SORT:
        return lambda product: product.name
    if sorting == PRICE_SORT:
        return lambda product: product.price
    if sorting == POPULAR_SORT:
        return lambda product: -product.bought
    return lambda product: product.id  # по умолчанию


def optimize_phone(phone):
    phone = str(phone).strip()
    plus = phone[0] == '+'
    phone = phone.lstrip('+')
    if phone.isdigit():
        if phone[0] == '7' or (phone[0] == '8' and not plus):
            if len(phone) == 11:
                return '+7' + phone[1:]
        elif phone[0] == '9' and not plus:
            if len(phone) == 10:
                return '+7' + phone
    raise ValueError


def transliterate_to_en(rus):
    d = {
        'А': 'A',
        'Б': 'B',
        'В': 'V',
        'Г': 'G',
        'Д': 'D',
        'Е': 'E',
        'Ё': 'YO',
        'Ж': 'ZH',
        'З': 'Z',
        'И': 'I',
        'Й': 'Y',
        'К': 'K',
        'Л': 'L',
        'М': 'M',
        'Н': 'N',
        'О': 'O',
        'П': 'P',
        'Р': 'R',
        'С': 'S',
        'Т': 'T',
        'У': 'U',
        'Ф': 'F',
        'Х': 'KH',
        'Ц': 'TS',
        'Ч': 'CH',
        'Ш': 'SH',
        'Щ': 'SCH',
        'Ъ': '',
        'Ы': 'Y',
        'Ь': '',
        'Э': 'E',
        'Ю': 'YU',
        'Я': 'YA',
        ' ': '_'
    }
    en = ""
    for i in rus.strip():
        if i in d:
            en += d[i]
    return en


class Characteristic:
    def __init__(self, kind, *args):
        self.kind = kind
        if kind == 'RANGE':
            self.start = args[0]
            self.end = args[1]
        elif kind == 'CHOOSE':
            self.options = list(args)


class SizeError(Exception):
    pass


class ExtensionError(Exception):
    pass

