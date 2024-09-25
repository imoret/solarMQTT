#include <ArduinoMqttClient.h>
#include <Ethernet2.h>

class landuino
{
public:
    String nombre;

    landuino(String n);

protected:
    int *dispositivos;

    char *broker;
    int port;
};