class dispositivo
{
public:
    String nombre;

    dispositivo(int p, int pPower, String n);
    String status();
    void setPin(String b);

protected:
    int pin;
    int pinPower;
    int estado;

    

private:
    // ###################################
    // ##### ACS712 Sensor de corriente ##
    // ###################################
    float Sensibilidad = 0.100; //  Sensibilidad en V/A para nuestro sensor
    float offset = 0.100;       //  Equivale a la amplitud del ruido

    float consumo();
};
