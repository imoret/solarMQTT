import serial
import serial.tools.list_ports

def encontrar_arduino():
    # Obtiene todos los puertos COM / tty disponibles
    puertos = serial.tools.list_ports.comports()
    
    for puerto in puertos:
        print(f"Probando puerto: {puerto.device}")
        try:
            # Intenta conectar al puerto (velocidad de baudios estándar: 9600)
            # Ajusta el timeout según lo rápido que responda tu Arduino
            conexion = serial.Serial(puerto.device, 9600, timeout=1)
            
            # Opcional: Envía un comando a Arduino para que confirme que es el dispositivo correcto
            # (Modifica el programa de tu Arduino para que responda a este texto)
            conexion.write(b"IDENTIFICAR\n")
            
            # Lee la respuesta del Arduino
            respuesta = conexion.readline().decode('utf-8').strip()
            
            if "ARDUINO" in respuesta.upper():
                print(f"¡Arduino detectado exitosamente en: {puerto.device}!")
                conexion.close()
                return puerto.device
                
            conexion.close()
            
        except (serial.SerialException, IndexError):
            # Ignora los puertos que no responden o están ocupados
            continue
            
    print("No se ha encontrado ningún Arduino conectado.")
    return None

# Ejecutar la función
puerto_detectado = encontrar_arduino()



###############################
import serial
import time

for puerto in puertos:
    print(puerto.device)
    conexion = serial.Serial(puerto.device, 9600, timeout=1)
    conexion.close()
    conexion.open()
    conexion.setDTR(True)   
    time.sleep(0.3) 
    conexion.setDTR(False)
    time.sleep(1)
    conexion.setDTR(True)
    conexion.dtr = False
    time.sleep(0.1)
    conexion.dtr = True
    time.sleep(0.5)
    conexion.dtr = False
    time.sleep(0.5)
    conexion.close()
