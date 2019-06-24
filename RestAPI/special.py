from django.http import JsonResponse
from MainSite.models import Category, Product, Order, Profile
from django.contrib.auth.models import User
from special import *


# создание унифицированного ответа
def make_success(state=True, message='Ok', **kwargs):
    data = {'success': state}
    if message == 'Ok':
        message = 'Ok' if state else 'Unknown Error'
    data['message'] = message
    data.update(kwargs)
    return JsonResponse(data)


# получить булевое значение из запроса
def get_bool(val):
    a = val is True
    b = type(val) is str and val.lower() in {'true', 't', 'y', '+'}
    c = type(val) is str and val.isdigit() and int(val) > 0
    d = type(val) is int and val > 0
    if a or b or c or d:
        return True
    return False


def check_token(params):
    if not params.get('token'):
        return False, "token missed"
    try:
        profile = Profile.objects.get(token=params.pop('token'))
        if profile.user.is_active:
            return True, profile.user
        return False, "User was deleted"
    except Profile.DoesNotExist:
        return False, "token is wrong"


# когда у параметра много значений (список) изменяем ключи
# (добовляем '__in' для QuerySet)
def optimize_params_keys(param):
    key, val = param
    return (key + '__in', val) if type(val) is list else param


def find_user(params):
    keys = ['id', 'username', 'email', 'phone', 'user_token']
    k = None
    for k in keys:
        if k in params:
            params = {k: params[k]}
            keys = None  # индикатор, что нужный ключ нашёлся
            break
    if keys:
        return False, f"{'/'.join(keys)} missed"
    try:
        # поиск в моделе профиля
        if k in {'phone', 'user_token'}:
            if k == 'phone':
                params[k] = optimize_phone(params[k])
            if k == 'user_token':
                params['token'] = params.pop('user_token')
            profile = Profile.objects.get(**params)
            if profile.user.is_superuser:
                raise User.DoesNotExist
            return True, profile.user
        # пользователя
        return True, User.objects.get(is_superuser=False, **params)
    except User.DoesNotExist:
        return False, f"User {k}={params[k]} does not exist"
    except ValueError:
        return False, "Incorrect params"
    except TypeError:
        return False, "Incorrect params"


def find_product(params):
    keys = ['id', 'name']
    k = ''
    for k in keys:
        if k in params:
            params = {k: params[k]}
            keys = None  # индикатор, что нужный ключ нашёлся
            break
    if keys:
        return False, f"{'/ '.join(keys)} missed"
    try:
        return True, Product.objects.get(**params)
    except Product.DoesNotExist:
        return False, f"Product {k}='{params[k]}' does not exist"
