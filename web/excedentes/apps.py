from django.apps import AppConfig


class ExcedentesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'excedentes'

    def ready(self):
        from . import mqtt
        mqtt.client.loop_start()
        return super().ready()
    
