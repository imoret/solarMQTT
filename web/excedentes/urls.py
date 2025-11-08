from django.urls import path
from . import views

urlpatterns = [
    path('', views.dash_board, name='dash_board'),
    path('config', views.config, name='config'),
    path('nuevo_archivo', views.nuevo_archivo, name='nuevo_archivo'),
    path('get_data', views.get_data, name='get_data'),
    path('setManual/<str:nombre_dispositivo>/<str:onOff>/<int:horas>/<int:minutos>/', views.setManual, name='setManual'),
    path('set_onOff/<str:nombre_dispositivo>/<str:onOff>/', views.set_onOff, name='set_onOff'),
    path('instalacion', views.instalacion, name='instalacion'),
    path('dispositivo/<str:nombre_dispositivo>/', views.dispositivo, name='dispositivo'),
    path('reset_dispositivo/<int:dispositivo_id>/', views.reset_dispositivo, name='reset_dispositivo'),
    path('reboot_system/', views.reboot_system, name='reboot_system'),
    path('reboot_server/', views.reboot_server, name='reboot_server'),
    path('rebooting_now/', views.rebooting_now, name='rebooting_now'),
    path('rebooting_server_now/', views.rebooting_server_now, name='rebooting_server_now')
]