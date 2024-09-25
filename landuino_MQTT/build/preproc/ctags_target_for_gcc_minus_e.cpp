# 1 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
# 2 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2
# 3 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2
# 4 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2
# 5 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2
# 6 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2
# 7 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2
# 8 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 2

const char ardName[] = "ard0/";
const char topicBase[] = "Arduino/";
byte mac[] = {0xDE, 0xAD, 0xBE, 0xEF, 0xFE, 0xED}; // Ponemos la dirección MAC de la Ethernet Shield
IPAddress ip(192, 168, 2, 177); // Asignamos  la IP al Arduino
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
    Serial.println((reinterpret_cast<const __FlashStringHelper *>(
# 35 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
                  (__extension__({static const char __c[] __attribute__((__progmem__)) = (
# 35 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                  "Ini"
# 35 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
                  ); &__c[0];}))
# 35 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                  )));
    for (int i = 0; i < 10; i++)
    {
        pinMode(i, 0x1);
        digitalWrite(i, 0x0);
    }

    wdt_enable(
# 42 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
              9
# 42 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                     );

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

    
# 74 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
   __asm__ __volatile__ ("wdr")
# 74 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
              ;
}

void loop()
{
    
# 79 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
   __asm__ __volatile__ ("wdr")
# 79 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
              ;
    mqttClient.poll();
    digitalWrite(13, 0x1);

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
        mqttClient.print((reinterpret_cast<const __FlashStringHelper *>(
# 96 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
                        (__extension__({static const char __c[] __attribute__((__progmem__)) = (
# 96 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                        "true"
# 96 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
                        ); &__c[0];}))
# 96 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                        )));
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
        
# 123 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
       __asm__ __volatile__ ("wdr")
# 123 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                  ;
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
        
# 148 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
       __asm__ __volatile__ ("wdr")
# 148 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                  ;
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
    
# 173 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
   __asm__ __volatile__ ("wdr")
# 173 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
              ;

    for (int i = 0; i < 10; i++)
    {
        sendStatus(i);
    }
}

void sendStatus(int i)
{
    
# 183 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3
   __asm__ __volatile__ ("wdr")
# 183 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
              ;
        if (dispositivos[i] != 
# 184 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino" 3 4
                              __null
# 184 "/home/moret/nextcloud/documentos/Solar/consumoExcedentes/sketchs/landuino_MQTT/landuino_MQTT.ino"
                                  )
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
