#line 1 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino.cpp"
#include <Arduino.h>
#include "landuino.h"
#include "dispositivos.h"
#include <ArduinoMqttClient.h>
#include <Ethernet2.h>

landuino::landuino(String n){
    nombre = n;

}