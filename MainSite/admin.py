from django.contrib import admin
from .models import Category, Product, Order, Profile, OrderSpot, Producer, Rate

admin.site.register([
    Category, Product, Order,
    Profile, OrderSpot, Producer, Rate
])

