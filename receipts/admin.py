from django.contrib import admin
from .models import Receipt, Person, LineItem

admin.site.register(Receipt)
admin.site.register(Person)
admin.site.register(LineItem)
