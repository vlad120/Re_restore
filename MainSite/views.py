from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import FormView


# главная страница
def main_page(request):
    return render(
        request, "main.html",
        {'menu_items': [{'name': 'asds', 'rus_name': 'sdx', 'link': '/'}],
         'len_basket': 0,
         'basket': [],
         'errors': {'authorization': {'password': None,
                                      'login': None,
                                      'other': None,
                                      'any': False}},
         'last': {'authorization': {'password': '',
                                    'login': ''}},
         'slides': ['static/main_slides/1'],
         'len_slides': [1]
         }
    )
