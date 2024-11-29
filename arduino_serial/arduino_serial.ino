#include <ArduinoJson.h>
#include <avr/wdt.h>
#include "dispositivos.h"


const String nombre = "ard1";

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
    inputString.reserve(200);
    
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
        Serial.print("{\"canal\" : \"online\", \"destino\" : \"Arduinos\", \"nombre\":\"");
        Serial.print(nombre);
        Serial.println("\",\"mensaje\":\"true\"}");

        
        // Envio un status de los dispositivos
        sendStatus();

        // Envio un online de los dispositivos
        sendOnline();
    }

    if (stringComplete)
    {
        StaticJsonDocument<300> doc;
        deserializeJson(doc, inputString);
        String command = doc["command"];
        
        //Serial.println(inputString);
        
        if (command == "setup")
        {
            wdt_reset();
            String tipo = doc["tipo"];
            String nombre = doc["nombre"];
            int pin = doc["pin"];
            int pinPower = doc["pinPower"];

            dispositivos[pin] = new dispositivo(pin, pinPower, nombre);
            dispositivos[pin]->setPin("LOW");

            Serial.println("ok\n");
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
                    Serial.println("ok\n");
                    sendStatus(i);
                    break;
                }
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
       Serial.print("{\"canal\":\"status\", \"destino\":\"Dispositivos\", \"nombre\":\"");
       Serial.print(dispositivos[i]->nombre);
       Serial.print("\",\"mensaje\":{\"event\":\"status\",\"nombre\":\"");
       Serial.print(dispositivos[i]->nombre);
       Serial.print("\",\"estado\":");
       Serial.print(dispositivos[i]->estado);
       Serial.print(" ,\"consumo\":");
       Serial.print(dispositivos[i]->consumo());
       Serial.println("}}");
    }
}

void sendOnline(){
    for (int i =0 ; i<10; i++){
        wdt_reset();
        if (dispositivos[i] != NULL)
        {
            Serial.print("{\"canal\" : \"online\", \"destino\" : \"Dispositivos\", \"nombre\":\"");
            Serial.print(dispositivos[i]->nombre);
            Serial.print("\",\"mensaje\":");
            Serial.print(true);
            Serial.println("}");
        }
    }
}
