from django.db import models
from django.conf import settings
from django.utils import timezone
import json
# Create your models here.


class Instalaciones(models.Model):
    maxred = models.IntegerField()
    localIP = models.GenericIPAddressField()
    broker_address = models.GenericIPAddressField()
    lat = models.FloatField()
    lon = models.FloatField()
    lcd = models.BooleanField(default=True)
    
class Inversores(models.Model):
    nombre = models.CharField(max_length=200)
    ip = models.GenericIPAddressField()

    def __str__(self):
        return self.nombre

class Actuadores(models.Model):
    actuador_tipo=(
        (1, "Arduinos_serial"),
        (2, "Arduinos_MQTT"),
        (3, "Shellys")
    )
    tipo = models.IntegerField(choices=actuador_tipo, default=1)
    nombre = models.CharField(max_length=200)
    puerto = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return self.nombre

class Dispositivos(models.Model):
    dispositivo_tipo = (
        (1, "resistivo"),
        (2, "capacitativo")
        )
    
    tipo = models.IntegerField(choices=dispositivo_tipo, default=1)
    nombre = models.CharField(max_length=200)
    power = models.IntegerField()
    ardu = models.ForeignKey(Actuadores,on_delete=models.CASCADE)
    pin = models.IntegerField()
    pinPower = models.IntegerField()
    minPower = models.IntegerField()
    tiempo_reaccion = models.IntegerField()
    modoDia = models.CharField(max_length=200)

    def __str__(self):
        return self.nombre

    def set_modoDia(self, modos):
        self.modoDia = json.dumps(modos)

    def get_modoDia(self):
        return json.loads(self.modoDia)

class Modos(models.Model):
    dispositivos = models.ManyToManyField(Dispositivos)
    nombre = models.CharField(max_length=200)
    timeOn = models.CharField(max_length=200, null=True, blank=True)
    timeOff = models.CharField(max_length=200, null=True, blank=True)
    consumirExcedente = models.BooleanField(default=True)
    tiempoAldia = models.IntegerField()
    tiempoMaximo = models.IntegerField()
    tiempoSeguido = models.IntegerField()
    horaCorte = models.IntegerField()

    def __str__(self):
        return self.nombre

    def set_timeOn(self, horas):
        self.timeOn = json.dumps(horas)

    def get_timeOn(self):
        return json.loads(self.timeOn)
    
    def set_timeOff(self, horas):
        self.timeOff = json.dumps(horas)

    def get_timeOff(self):
        return json.loads(self.timeOff)