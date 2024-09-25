#include <Arduino.h>
#include "landuino.h"
#include "dispositivos.h"
#include <ArduinoMqttClient.h>
#include <Ethernet2.h>

landuino::landuino(String n){
    nombre = n;

}