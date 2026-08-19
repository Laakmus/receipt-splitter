from django.urls import path
from . import views

urlpatterns = [
    path('', views.receipt_upload, name='receipt-upload'),
    path('<int:pk>/', views.receipt_preview, name='receipt-preview'),
]