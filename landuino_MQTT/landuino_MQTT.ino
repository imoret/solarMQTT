#include <ArduinoJson.h>
#include <Ethernet2.h>
#include <EthernetUdp2.h>
#include <ArduinoMqttClient.h>
#include <string.h>
#include <avr/wdt.h>
#include "dispositivos.h"

const char ardName[] = "ard0/";
const char topicBase[] = "Arduino/";
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED}; // Ponemos la dirección MAC de la Ethernet Shield
IPAddress ip(192, 168, 2, 177);                    // Asignamos  la IP al Arduino
EthernetClient client;

MqttClient mqttClient(client);
const char broker[] = "192.168.2.105";
int port = 1883;

const char topic0[sizeof(topicBase) + sizeof(ardName)];
const char topicOnline[sizeof(topic0) + 6];
const char topicCommand[sizeof(topic0) + 7];
const char topicEvent[sizeof(topic0) + 5];

// set interval for sending messages (milliseconds)
const int interval = 8000;
unsigned long previousMillis = 0;


dispositivo *dispositivos[10];

void setup()
{
    wdt_disable();
    Serial.begin(115200);
    Serial.println(F("Ini"));
    for (int i = 0; i < 10; i++)
    {
        pinMode(i, OUTPUT);
        digitalWrite(i, LOW);
    }

    wdt_enable(WDTO_8S);

    Ethernet.begin(mac, ip);
    sprintf(topic0, "%s%s", topicBase, ardName);
    sprintf(topicOnline, "%s%s", topic0, "online");
    sprintf(topicCommand, "%s%s", topic0, "command");
    sprintf(topicEvent, "%s%s", topic0, "event");

    // Configuro un "Last Will and Testamet" (LTW)
    String willPayload = "false";
    bool willRetain = true;
    int willQos = 1;
    mqttClient.beginWill(topicOnline, willPayload.length(), willRetain, willQos);
    mqttClient.print(willPayload);
    mqttClient.endWill();

    while (!mqttClient.connect(broker, port))
    {
        delay(100);
    }
    mqttClient.onMessage(onMqttMessage);
    mqttClient.subscribe(topicCommand);

    // Solicito configuracion
    String eventMessage = "{'event':'init'}";
    bool retained = false;
    int qos = 1;
    bool dup = false;
    mqttClient.beginMessage(topicEvent, eventMessage.length(), retained, qos, dup);
    mqttClient.print(eventMessage);
    mqttClient.endMessage();

    wdt_reset();
}

void loop()
{
    wdt_reset();
    mqttClient.poll();
    digitalWrite(13, HIGH);

    unsigned long currentMillis = millis();

    if (currentMillis - previousMillis >= interval)
    {
        // save the last time a message was sent
        previousMillis = currentMillis;

        // Envio un true a online
        String message = "true";
        bool retained = true;
        int qos = 1;
        bool dup = false;
        mqttClient.beginMessage(topicOnline, message.length(), retained, qos, dup);
        mqttClient.print(F("true"));
        mqttClient.endMessage();

        // Envio un status
        sendStatus();
    }
}

void onMqttMessage(int messageSize)
{
    char message[messageSize];
    int i = 0;
    while (mqttClient.available())
    {
        message[i] = (char)mqttClient.read();
        i++;
    }

    Serial.println(message);
    StaticJsonDocument<200> doc;
    deserializeJson(doc, message);
    String command = doc["command"];

    // ######## setup
    // Los dispositvos llegaran de uno en uno. Ej: {"command":"setup", "tipo":"capacitativo","nombre":"pozo", "pin":5, "pinPower":2}
    if (command == "setup")
    {
        wdt_reset();
        String tipo = doc["tipo"];
        String nombre = doc["nombre"];
        int pin = doc["pin"];
        int pinPower = doc["pinPower"];

        dispositivos[pin] = new dispositivo(pin, pinPower, nombre);
        dispositivos[pin]->setPin("LOW");
        sendStatus(pin);
        /*
                if (tipo == "capacitativo")
                {
                    dispositivos[pin] = new capacitativo(pin, pinPower, nombre);
                }
                if (tipo == "resistivo")
                {
                    dispositivos[pin] = new resistivo(pin, pinPower, nombre);
                }
        */
    }

    // ####### setPin
    // Ej: {"command":"setPin", "dispositivo":"pozo", "valor":"HIGH"}
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
            String message = "{'event':'status',";
            message.concat(dispositivos[i]->status());
            message.concat("}");
            bool retained = false;
            int qos = 1;
            bool dup = false;
            mqttClient.beginMessage(topic0+dispositivos[i]->nombre, message.length(), retained, qos, dup);
            mqttClient.print(message);
            mqttClient.endMessage();
        }
}