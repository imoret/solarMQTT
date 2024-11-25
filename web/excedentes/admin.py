from django.contrib import admin
from .models import Instalaciones, Inversores, Actuadores, Dispositivos, Modos
# Register your models here.

admin.site.register(Instalaciones)
admin.site.register(Inversores)
admin.site.register(Actuadores)
admin.site.register(Dispositivos)
admin.site.register(Modos)
