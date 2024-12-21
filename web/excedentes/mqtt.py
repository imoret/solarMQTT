import json
import paho.mqtt.client as mqtt
from django.conf import settings
import time
from excedentes.models import *
from collections import defaultdict

def on_connect(mqtt_client, userdata, flags, rc):
    if rc == 0:
        print('MQTT Connected successfully')
        mqtt_client.subscribe('Instalacion/status')
        mqtt_client.subscribe('Instalacion/historicos')
        time.sleep(15)

        dispositivos = Dispositivos.objects.all()
        for d in dispositivos:
            settings.ESTADO['dispositivos'][d.nombre]={'consumo':0, 'horas':0, 'min':0, 'seg':0, 'manual':False}
            actuador = Actuadores.objects.filter(nombre=d.ardu)[0]
            mqtt_client.subscribe('Dispositivos/%s/activity' % d.nombre)            
            if actuador.tipo == 1 or actuador.tipo == 2:
               mqtt_client.subscribe('Dispositivos/%s/status' % d.nombre)
            if actuador.tipo == 3:
                mqtt_client.subscribe('Shellys/%s/status/switch:0' % d.nombre)
    else:
        print('MQTT Bad connection. Code:', rc)


def on_message(mqtt_client, userdata, message):
    #print(f'Received message on topic: {message.topic} with payload: -{message.payload}-')
    data = json.loads(message.payload)
    #decoded_message=str(message.payload.decode("utf-8"))
    destino = message.topic.split('/')[0]
    if destino == 'Instalacion':
        canal=message.topic.split('/')[1]
        #print(data['produccion'])
        if canal == 'status':
            settings.ESTADO['instalacion']['produccion'] = data['produccion']
            settings.ESTADO['instalacion']['excedente'] = data['excedente']
        if canal == 'historicos':
            settings.ESTADO['historicos'] = data         
    elif destino == 'Shellys':
        nombre=message.topic.split('/')[1]
        canal=message.topic.split('/')[2]
        if canal == 'status':
            settings.ESTADO['dispositivos'][nombre]['consumo'] = data['apower']
    elif destino == 'Dispositivos':
        nombre=message.topic.split('/')[1]
        canal=message.topic.split('/')[2]
        if canal == 'status':
            settings.ESTADO['dispositivos'][nombre]['consumo'] = data['consumo']
        
        if canal == 'activity':
            th = -data['tiempo_hoy']
            horas = int(th/-3600)
            secsRemaining = abs(th)%3600
            min = int(secsRemaining/60)
            seg = int(secsRemaining%60)
            settings.ESTADO['dispositivos'][nombre]['tiempoHoy'] = th
            settings.ESTADO['dispositivos'][nombre]['horas'] = horas
            settings.ESTADO['dispositivos'][nombre]['min'] = min
            settings.ESTADO['dispositivos'][nombre]['seg'] = seg
            settings.ESTADO['dispositivos'][nombre]['manual'] = data['manual']
            settings.ESTADO['dispositivos'][nombre]['powerAct'] = data['powerAct']
    #print(settings.ESTADO)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.username_pw_set(settings.MQTT_USER, settings.MQTT_PASSWORD)
client.connect(
    host=settings.MQTT_SERVER,
    port=settings.MQTT_PORT,
    keepalive=settings.MQTT_KEEPALIVE
)

