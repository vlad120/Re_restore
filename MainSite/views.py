from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import FormView
from django.contrib.auth.models import User
from .models import Category, Product, Order
from os import listdir, path
from special import *


# главная страница
def main_page(request):
    # находим все слайды в папке (исключая скрытые файлы)
    slides = filter(lambda f: f[0] != '.' and f[:2] != '~$', listdir(to_path('main_slides')))
    slides = list(slides)
    # собираем пути к ним
    slides = list(map(lambda slide: to_path('main_slides', slide), slides))
    # преобразуем в вид (<номер>, <путь>)
    for i in range(len(slides)):
        slides[i] = (i, slides[i])

    return render(
        request, "main.html",
        {'menu_items': [c.to_dict('rus_name', 'link') for c in Category.objects.filter(is_active=True, parent=None)],
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
