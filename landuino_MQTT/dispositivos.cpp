#include <Arduino.h>
#include "dispositivos.h"

dispositivo::dispositivo(int p, int pPower, String n)
{
    nombre = n;
    pin = p;
    pinPower = pPower;
}

String dispositivo::status()
{
    String status = "'nombre':'" + nombre + "','estado':'" + estado + "','consumo':" + consumo();
    return (status);
}

float dispositivo::consumo()
{
    if (pinPower >= 0)
    {
        float voltajeSensor;
        float corriente = 0;
        long tiempo = millis();
        float Imax = 0;
        float Imin = 0;
        float Ip = 0;
        float Irms = 0;
        float P = 0;

        while (millis() - tiempo < 500) // realizamos mediciones durante 0.5 segundos
        {
            voltajeSensor = analogRead(pinPower) * (5.0 / 1023.0);                        // lectura del sensor
            corriente = 0.9 * corriente + 0.1 * ((voltajeSensor - 2.527) / Sensibilidad); // Ecuación  para obtener la corriente
            if (corriente > Imax)
                Imax = corriente;
            if (corriente < Imin)
                Imin = corriente;
        }
        Ip = (((Imax - Imin) / 2) - offset); // corriente pico
        Irms = Ip * 0.707;                   // Intensidad RMS = Ipico/(2^1/2)
        P = Irms * 230.0;                    // P=IV watts
        return (P);
    }
    else
    {
        return (0);
    }
}

void dispositivo::setPin(String v)
{
    if (v == "True")
    {
        digitalWrite(pin, HIGH);
        estado = 255;
    }else if (v == "False")
    {
        digitalWrite(pin, LOW);
        estado = 0;
    }else{
        analogWrite(pin, v.toInt());
        estado = v.toInt();
    }
}

