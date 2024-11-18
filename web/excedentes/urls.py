from django.urls import path
from . import views

urlpatterns = [
    path('', views.dash_board, name='dash_board'),
]