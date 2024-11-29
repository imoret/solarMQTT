from django.shortcuts import render
from django.http import JsonResponse
from django.core import serializers
from excedentes.models import *

# Create your views here.
def dash_board(request):
    return render(request, 'excedentes/dash_board.html', {})

def config(request):
    instalaciones = Instalaciones.objects.all()
    inversores = Inversores.objects.all()
    actuadores = Actuadores.objects.all()
    dispositivos = Dispositivos.objects.all()
    modos = Modos.objects.all()
    return render(request, 'excedentes/config.html', {'instalaciones':instalaciones, 'inversores':inversores, 'actuadores':actuadores, 'dispositivos':dispositivos, 'modos':modos})

def nuevo_archivo(request):
    instalaciones = Instalaciones.objects.all()
    inversores = Inversores.objects.all()
    a_serial = Actuadores.objects.filter(tipo=1)
    a_MQTT = Actuadores.objects.filter(tipo=2)
    sh = Actuadores.objects.filter(tipo=3)
    dispositivos = Dispositivos.objects.all()
    capacitativos = Dispositivos.objects.filter(tipo=2)

    conf = {}
    data = {'maxRed':instalaciones[0].maxred, 'localIP':instalaciones[0].localIP, "broker_address": instalaciones[0].broker_address, "lat" : instalaciones[0].lat, "lon" : instalaciones[0].lon, "lcd" : instalaciones[0].lcd}
    inv = []
    arduinos_serial = []
    arduinos_MQTT = []
    shellys = []
    disp =[]


    for i in inversores:
        inv.append({'nombre':i.nombre,'ip':i.ip})

    for a_s in a_serial:
        arduinos_serial.append({'tipo':'arduinos_serial', 'nombre':a_s.nombre, 'puerto':a_s.puerto})

    for a_M in a_MQTT:
        arduinos_MQTT.append({'tipo':'Arduinos_MQTT', 'nombre':a_M.nombre, 'puerto':a_M.puerto})

    for s in sh:
        shellys.append({'tipo':'Shellys', 'nombre':s.nombre, 'puerto':s.puerto})

    for d in dispositivos:
        tipo = d.get_tipo()
        print('##')
        print(tipo)
        print('##')
        modo_lunes = Modos.objects.filter(nombre=d.modoLunes)[0]
        modo_martes = Modos.objects.filter(nombre=d.modoMartes)[0]
        modo_miercoles = Modos.objects.filter(nombre=d.modoMiercoles)[0]
        modo_jueves = Modos.objects.filter(nombre=d.modoJueves)[0]
        modo_viernes = Modos.objects.filter(nombre=d.modoViernes)[0]
        modo_sabado = Modos.objects.filter(nombre=d.modoSabado)[0]
        modo_domingo = Modos.objects.filter(nombre=d.modoDomingo)[0]
        modos = {}
        for m in (modo_lunes, modo_martes, modo_miercoles, modo_jueves, modo_viernes, modo_sabado, modo_domingo):
            modos[m.nombre]={'timeOn':m.timeOn, 'timeOff':m.timeOff, 'consumirExcedente':m.consumirExcedente, 'tiempoAldia':m.tiempoAldia, 'tiempoMaximo':m.tiempoMaximo, 'tiempoSeguido':m.tiempoSeguido, 'horaCorte':m.horaCorte}
        disp.append({'tipo':tipo, 'nombre':d.nombre, 'power':d.power, 'ardu':d.ardu.nombre, 'pin':d.pin, 'pinPower':d.pinPower, 'minPower':d.minPower, 'tiempo_reaccion':d.tiempo_reaccion, 'modos':modos, 'modoDia':[modo_lunes.nombre, modo_martes.nombre, modo_miercoles.nombre, modo_jueves.nombre, modo_viernes.nombre, modo_sabado.nombre, modo_domingo.nombre]})
    conf = {'data':data, 'inversores':inv, 'arduinos_serial':arduinos_serial, 'arduinos_MQTT':arduinos_MQTT,'shellys':shellys, 'dispositivos':disp}
    with open('../excedentes/excedentes.conf', 'w') as f:
        json.dump(conf, f, indent=4)
    print(conf)
    return render(request, 'excedentes/dash_board.html', {'data':data})
