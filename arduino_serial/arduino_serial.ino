#include <ArduinoJson.h>
#include <avr/wdt.h>
#include "dispositivos.h"


const String nombre = "ard0";

String inputString = "";
bool stringComplete = false;

// set interval for sending messages (milliseconds)
const int interval = 8000;
unsigned long previousMillis = 0;

dispositivo *dispositivos[10];

void setup()
{
    wdt_disable();
    for (int i = 0; i < 10; i++)
    {
        pinMode(i, OUTPUT);
        digitalWrite(i, LOW);
    }

    wdt_enable(WDTO_8S);
    Serial.begin(9600);
    Serial.println("");
    Serial.println("{\"canal\" : \"event\", \"destino\" : \"Arduinos\", \"nombre\":\"" + nombre + "\",\"mensaje\": {\"event\":\"init\"}}");
    wdt_reset();
}

void loop()
{
    wdt_reset();
    unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval)
    {
        // save the last time a message was sent
        previousMillis = currentMillis;

        // Envio un true a online
        String message = "{\"canal\" : \"online\", \"destino\" : \"Arduinos\", \"nombre\":\"" + nombre + "\",\"mensaje\":\"true\"}";
        Serial.println(message);
        
        // Envio un status de los dispositivos
        sendStatus();

        // Envio un online de los dispositivos
        sendOnline();
    }

    if (stringComplete)
    {
        Serial.println(inputString);
        StaticJsonDocument<300> doc;
        deserializeJson(doc, inputString);
        String command = doc["command"];

        if (command == "setup")
        {
            wdt_reset();
            String tipo = doc["tipo"];
            String nombre = doc["nombre"];
            int pin = doc["pin"];
            int pinPower = doc["pinPower"];

            dispositivos[pin] = new dispositivo(pin, pinPower, nombre);
            dispositivos[pin]->setPin("LOW");

            Serial.println("ok");
            sendStatus(pin);
        }

        if (command == "setPin")
        {
            wdt_reset();
            String disp = doc["dispositivo"];
            for (int i = 0; i < 10; i++)
            {
                if (dispositivos[i]->nombre == disp)
                {
                    String v = doc["valor"];
                    dispositivos[i]->setPin(v);
                    Serial.println("ok");
                    Serial.print("");
                    sendStatus(i);
                    break;
                }
                Serial.print("ko");
                Serial.print("");
            }
        }

            // ######  RESET
        if (command == "reset")
        {
          while (1)
          {
          }
        }
        inputString = "";
        stringComplete = false;
    }
}

void serialEvent()
{
    while (Serial.available())
    {
        char inChar = (char)Serial.read();
        
        if (inChar == '\n')
        {
            stringComplete = true;
        }else{
          inputString += inChar;
        }
    }
}

void sendStatus()
{
    wdt_reset();

    for (int i = 0; i < 10; i++)
    {
        sendStatus(i);
    }
}

void sendStatus(int i)
{
    wdt_reset();
    if (dispositivos[i] != NULL)
    {
        String message = "{\"canal\" : \"status\", \"destino\" : \"Dispositivos\", \"nombre\":\"" + dispositivos[i]->nombre + "\",\"mensaje\":" + dispositivos[i]->status() + "}";
        Serial.println(message);
        Serial.print("");
    }
}

void sendOnline(){
    for (int i =0 ; i<10; i++){
        wdt_reset();
        if (dispositivos[i] != NULL)
        {
            String message = "{\"canal\" : \"online\", \"destino\" : \"Dispositivos\", \"nombre\":\"" + dispositivos[i]->nombre + "\",\"mensaje\":" + true + "}";
            Serial.println(message);
            Serial.print("");
        }
    }
}
