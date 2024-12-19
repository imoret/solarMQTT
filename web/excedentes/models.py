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
        
void_list = list(())

class Modos(models.Model):
    nombre = models.CharField(max_length=200)
    timeOn = models.JSONField(null=False, default=void_list, blank=True )
    timeOff = models.JSONField(null=False, default=void_list, blank=True )
    #timeOn = models.CharField(max_length=200, null=True, blank=True)
    #timeOff = models.CharField(max_length=200, null=True, blank=True)
    consumirExcedente = models.BooleanField(default=True)
    tiempoAldia = models.IntegerField()
    tiempoMaximo = models.IntegerField()
    tiempoSeguido = models.IntegerField()
    horaCorte = models.IntegerField(default=24)

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
    tiempo_reaccion = models.FloatField(default=1)
    modoLunes = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="lunes", null=True)
    modoMartes = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="martes", null=True)
    modoMiercoles = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="miercoles", null=True)
    modoJueves = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="jueves", null=True)
    modoViernes = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="viernes", null=True)
    modoSabado = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="sabado", null=True)
    modoDomingo = models.ForeignKey(Modos, on_delete=models.RESTRICT, related_name="domingo", null=True)

    def __str__(self):
        return self.nombre
    '''
    def set_modoDia(self, modos):
        self.modoDia = json.dumps(modos)

    def get_modoDia(self):
        return json.loads(self.modoDia)
    '''    
    def get_tipo(self):
        return self.dispositivo_tipo[self.tipo-1][1]
    
    def power_max(self):
        return (int(self.power*1.2))

    def power_medio_alto(self):
        return(int(self.power*0.8))
    
    def power_medio(self):
        return(int(self.power*0.6))
    
    def power_min(self):
        return(int(self.power*0.2))
