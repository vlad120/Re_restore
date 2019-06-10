from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import FormView
from .models import Category, Product, Order
from os import listdir, path

LOCAL_STATIC = 'MainSite/static'


# главная страница
def main_page(request):
    # находим все слайды в папке (исключая скрытые файлы)
    slides = filter(lambda f: f[0] != '.' and f[:2] != '~$',
                    listdir(path.join(LOCAL_STATIC, 'main_slides')))
    # собираем пути к ним
    slides = list(map(lambda slide: path.join('static', 'main_slides', slide), slides))
    # преобразуем в вид (<номер>, <путь>)
    for i in range(len(slides)):
        slides[i] = (i, slides[i])

    return render(
        request, "main.html",
        {'menu_items': [c.to_dict() for c in Category.objects.filter(active=True)],
         'len_basket': 0,
         'basket': [],
         'errors': {'authorization': {'password': None,
                                      'login': None,
                                      'other': None,
                                      'any': False}},
         'last': {'authorization': {'password': '',
                                    'login': ''}},
         'slides': slides,
         }
    )
