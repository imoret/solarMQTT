class dispositivo
{
public:
    String nombre;
    String topicOnline;
    String topicStatus;
    int estado;
    

    dispositivo(int p, int pPower, String n);
    String status();
    void setPin(String b);
    float consumo();

protected:
    int pin;
    int pinPower;
    

    

private:
    // ###################################
    // ##### ACS712 Sensor de corriente ##
    // ###################################
    float Sensibilidad = 0.100; //  Sensibilidad en V/A para nuestro sensor
    float offset = 0.100;       //  Equivale a la amplitud del ruido

    
};
