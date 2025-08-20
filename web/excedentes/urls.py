from django.urls import path
from . import views

urlpatterns = [
    path('', views.dash_board, name='dash_board'),
    path('config', views.config, name='config'),
    path('nuevo_archivo', views.nuevo_archivo, name='nuevo_archivo'),
    path('get_data', views.get_data, name='get_data'),
    path('setManual/<str:nombre_dispositivo>/<str:onOff>/', views.setManual, name='setManual'),
    path('set_onOff/<str:nombre_dispositivo>/<str:onOff>/', views.set_onOff, name='set_onOff'),
    path('instalacion', views.instalacion, name='instalacion'),
    path('dispositivo/<str:nombre_dispositivo>/', views.dispositivo, name='dispositivo'),
    path('reset_dispositivo/<int:dispositivo_id>/', views.reset_dispositivo, name='reset_dispositivo')
]