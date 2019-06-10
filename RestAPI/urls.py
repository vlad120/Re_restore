from django.urls import path
from . import views

urlpatterns = [
    path('users/<req>', views.UserAPI.as_view()),
    # path('api/products/', views.ProductAPI.as_view()),
    # path('api/orders/', views.OrderAPI.as_view()),
    # path('api/basket/', views.BasketAPI.as_view()),
    # path('api/search/', views.SearchAPI.as_view()),
]
