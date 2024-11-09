import json
import logging
import threading
from RPLCD import i2c
import time
from datetime import datetime, timezone
from datetime import date
import pytz
from suntimes import SunTimes 

class lcd:
    def __init__(self, lat=0, lon=0):
        self.lcdLuz=True
        self.cols = 20
        self.rows = 4
        charmap = 'A00'
        i2c_expander = 'PCF8574'
        address = 0x27 
        port = 1
        self.lineas = ["","",""]
        self.latitud = lat
        self.longitud = lon
        self.semaforoLCD = threading.Semaphore(1)	#Semaforo

        try:
            self.lcd = i2c.CharLCD(i2c_expander, address, port=port, charmap=charmap,cols=self.cols, rows=self.rows)
            self.luz()
        except:
            return(None)
        
    def resetLCD(self):
        try:
            delattr(self,'lcd')
        except:
            pass
        self.__init__()

    def writeLine(self, datos, linea):
        datos_limpios = datos
        for i in range (len(datos), self.cols):
            datos_limpios += " "
        try:
            with self.semaforoLCD:
                self.lcd.cursor_pos = (linea, 0)
                self.lcd.write_string(str(datos_limpios))
        except:
            self.resetLCD()

    def muestraProduccion(self, p, e):
        c = p + e
        datos = "P:%s E:%s C:%s" %(p, e, c)
        self.writeLine(datos, 0)

    def crea_lineas_dispositivos(self, dispositivos):
        datos = ""
        size = 0
        for i in range(0,len(self.lineas)):
                self.lineas.pop(0)
        for d in dispositivos:
            datos_plus = d.nombre + ":"
            if d.tipo == 'capacitativo':              
                datos_plus += 'ON' if d.powerAct > 0 else 'OFF'
            if d.tipo == 'resistivo':
                datos_plus += str(int(d.powerAct * 0.392156863)) + "%"
            if len(datos)+len(datos_plus) == self.cols:
                datos += datos_plus
                self.lineas.append(datos)
                datos = ""
            if len(datos)+len(datos_plus) > self.cols:
                self.lineas.append(datos)
                datos = datos_plus
            else:
                datos_plus += ' '
                datos += datos_plus
        self.lineas.append(datos)
        for r in range(len(self.lineas),self.rows):
            datos=""
            for c in range(0,self.cols):
                datos += " "
            self.lineas.append(datos)

    def muestra_dispositivos(self,dispositivos):
        self.luz()
        self.crea_lineas_dispositivos(dispositivos)
        for i in range(1,self.rows):
                self.writeLine(self.lineas[i-1],i)


    def luz(self):
        zona_horaria = pytz.timezone("Europe/Madrid")
        hoy = datetime.today()
        sol = SunTimes(self.longitud,self.latitud)
        salidaSol = sol.riselocal(hoy)
        puestaSol = sol.setlocal(hoy)
        ahora = zona_horaria.localize(datetime.now().replace(tzinfo=None))
        self.lcdLuz = True if ahora > salidaSol and ahora < puestaSol else False
        try:
            self.lcd.backlight_enabled = self.lcdLuz
        except:
            pass
    
    def parada_emergencia(self):
        self.lcd.backlight_enabled = True
        self.lcdLuz=True
        self.lcd.clear()
        self.lcd.cursor_pos = (1,5)
        self.lcd.write_string("PARADA  DE")
        self.lcd.cursor_pos = (2,5)
        self.lcd.write_string("EMERGENCIA")
