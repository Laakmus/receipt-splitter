from django.urls import path
from . import views

urlpatterns = [
    path('', views.receipt_upload, name='receipt-upload'),
]