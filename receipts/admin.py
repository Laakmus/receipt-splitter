from django.contrib import admin

from .models import LineItem, Person, Receipt

admin.site.register(Receipt)
admin.site.register(Person)
admin.site.register(LineItem)
