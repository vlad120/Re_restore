from rest_framework.response import Response
import os


# получение корректного пути
def to_path(*args):
    return os.path.join(*args)


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
    return Response(data)
