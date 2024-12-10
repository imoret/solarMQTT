from django.urls import path
from . import views

urlpatterns = [
    path('', views.dash_board, name='dash_board'),
    path('config', views.config, name='config'),
    path('nuevo_archivo', views.nuevo_archivo, name='nuevo_archivo'),
    path('get_data', views.get_data, name='get_data')
]