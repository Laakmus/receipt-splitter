from django.urls import path

from . import views

urlpatterns = [
    path('', views.receipt_upload, name='receipt-upload'),
    path('lista/', views.receipt_list, name='receipt-list'),
    path('<int:pk>/', views.receipt_preview, name='receipt-preview'),
    path('<int:pk>/usun/', views.receipt_delete, name='receipt-delete'),
]
