import json
import logging
import threading
from dispositivo import dispositivo
from arduino import arduino_serial, arduino_MQTT, shelly
from inversor import fronius
from signal import signal, SIGINT
from sys import exit
from filelock import Timeout, FileLock
import serial,time, sched
from datetime import datetime
import paho.mqtt.client as mqtt #import the client1
from RPLCD import i2c

class instalacion:
    def __init__(self):
        global kill_threads
        
        self.inversores = []
        self.arduinos = []
        self.dispositivos = []
        
        self.produccion = 0
        self.excedente = 0
        
        #Creo la LCD
        self.lcdLuz=True
        self.creaLCD() 
        
		#Creo el logger del domus
        self.logger = logging.getLogger('domus')
        self.logger.setLevel(logging.DEBUG)
        fhd = logging.FileHandler('excedentes.log')
        fhd.setLevel(logging.DEBUG)
        self.logger.addHandler(fhd)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        fhd.setFormatter(formatter)
        self.logger.addHandler(fhd)
        
        lock = FileLock("excedentes.conf.lock")
        with lock:
            with open('excedentes.conf') as fileConf:
                conf = json.load(fileConf)
                self.nuevaConf = conf['nuevaConf']
                self.maxRed = conf['data']['maxRed']
                self.localIP = conf['data']['localIP']
				
                #Preparo el MQTT
                self.broker_address = conf['data']['broker_address']
                self.mqtt_client = mqtt.Client("solarOptimum")
                self.mqtt_client.on_message = self.on_message 
                self.mqtt_client.on_connect = self.on_connect
                self.mqtt_client.on_disconnect = self.on_disconnect
                self.mqtt_client.on_subscribe = self.on_subscribe
                self.mqtt_client.on_unsubscribe = self.on_unsubscribe
                self.logger.info("Inicio conexion al servidor MQTT")
                self.mqtt_client.connect(self.broker_address)
                
                for i in conf['inversores']:				#Lo recorro pero se que solo hay uno
                    aux = fronius(i['nombre'],i['ip'])
                    self.inversores[i['nombre']] = aux
                    
                for a in conf['arduinos_serial']:
                    aux=arduino_serial(a['nombre'],a['puerto'])
                    self.arduinos[a['nombre']]=aux
                    
                for l in conf['arduinos_MQTT']:
                    aux=arduino_MQTT(l['nombre'],self.broker_address)
                    self.arduinos[l['nombre']]=aux
                    self.arduinos[l['nombre']].subscribe(self.mqtt_client)
                    
                for s in conf['shellys']:
                    aux=shelly(s['nombre'],self.broker_address)
                    self.arduinos[s['nombre']]=aux
                    self.arduinos[l['nombre']].subscribe(self.mqtt_client)
                
                for d in conf['dispositivos']:
                    tipo = d['tipo']
                    nombre = d['nombre']
                    power = d['power']
                    pinPower = d['pinToGetPower']
                    t_on = d["modos"][d['modoDia'][datetime.today().weekday()]]["timeOn"]
                    t_off = d["modos"][d['modoDia'][datetime.today().weekday()]]["timeOff"]
                    consumirE = d["modos"][d['modoDia'][datetime.today().weekday()]]["consumirExcedente"]
                    tiempo_al_dia = d["modos"][d['modoDia'][datetime.today().weekday()]]["tiempoAldia"]
                    tiempo_maximo = d["modos"][d['modoDia'][datetime.today().weekday()]]["tiempoMaximo"]
                    tiempo_seguido = d["modos"][d['modoDia'][datetime.today().weekday()]]["tiempoSeguido"]
                    hora_corte = d["modos"][d['modoDia'][datetime.today().weekday()]]["horaCorte"]
                    minPo = d['minPo']
                    aux = dispositivo(tipo, nombre, power, pinPower, t_on, t_off, consumirE, tiempo_al_dia, tiempo_maximo, tiempo_seguido, hora_corte, minPo)
                    self.dispositivos[d['nombre']] = aux
                    self.dispositivos[d['nombre']].subscribe(self.mqtt_client)
                    
        #Creo un hilo que gestiona las conexiones MQTT.
        self.mqtt_control = threading.Thread(target=self.thread_mqtt)
        self.mqtt_control.setDaemon(True)
        self.mqtt_control.start()
        
    def creaLCD(self):
		#Creo la LCD
		# constants to initialise the LCD
        lcdmode = 'i2c'
        cols = 20
        rows = 4
        charmap = 'A00'
        i2c_expander = 'PCF8574'

		# Generally 27 is the address;Find yours using: i2cdetect -y 1 
        address = 0x27 
        port = 1 # 0 on an older Raspberry Pi

		# Initialise the LCD
        try:
            self.lcd = i2c.CharLCD(i2c_expander, address, port=port, charmap=charmap,cols=cols, rows=rows)
            self.lcd.backlight_enabled = self.lcdLuz
        except:
            pass
        
    def thread_mqtt(self):
        while not kill_threads:
            self.logger.info("Inicio el loop_forever MQTT")
            self.mqtt_client.loop_forever()
            self.logger.error("Cliente MQTT desconectado!!!")
            time.sleep(4)
  
    ################ Al conectar MQTT #################
    def on_connect(self, client, userdata, flags, rc):
        resultado = ['Connection successful', 'Connection refused - incorrect protocol version', 'Connection refused - invalid client identifier', 'Connection refused - server unavailable', 'Connection refused - bad username or password', 'Connection refused - not authorised']
        self.logger.info("Resultado de la conexion MQTT: "+resultado[rc])
	
	############### Subscipciones/ unsubscripciones ###
    def on_subscribe(self,client, userdata, mid, granted_qos):
        self.logger.info("Suscripcion "+str(mid)+": "+str(granted_qos))
		
    def on_unsubscribe(self, client, userdata, mid):
        self.logger.info("Cagon to!!! --->  Desuscripcion a topic MQTT  <----: "+str(mid));
        
    def on_disconnect(self,client, userdata, rc):
        if rc != 0:
            print("Unexpected MQTT disconnection. Will auto-reconnect")
   
    ############ MESSAGE MQTT ###################
    def on_message(self,client, userdata, message):
        decoded_message=str(message.payload.decode("utf-8"))
        destino = message.topic.split('/')[0]
        nombre=message.topic.split('/')[1]
        canal=message.topic.split('/')[2]
		
        #Si recibo un online
        if canal == "online":
            if destino == "Shellys" or destino == "Arduinos":
                self.arduinos[nombre].online = True if decoded_message == 'true' else False
            if destino == "Dispositivos":
                self.dispositivos[nombre].online = True if decoded_message == 'true' else False
                
        #Si recibo un evento
        if canal == "event":
            if destino == "Shellys":
                pass
            if destino == "Arduinos":
                msg=json.loads(decoded_message)
                if msg['event'] == 'init':
                    for d in self.dispositivos:
                        if d.nombre == nombre:
                            d.setup()
            if destino == "Dispositivos":
                pass
        
        #Si recibo un status    
        if canal == "status":
            if destino == "Shellys":
                msg=json.loads(decoded_message)
                for d in self.dispositivos:
                    if d.ard == nombre:
                        d.powerAct = True if str(msg["output"]) == 'True' else False
                        d.consumo = msg["apower"]
                        if (msg["source"] != 'init' and msg["source"] != 'MQTT' and d.modoManual == False):
                            d.logger.info("Puesto en modo manual");
                            d.modoManual = True
                        if ((msg["source"] == 'init' or msg["source"] == 'MQTT') and d.modoManual == True): 
                            d.logger.info("Puesto en modo automatico");
                            d.modoManual = False 
            if destino == "dispositivos":
                self.dispositivos[nombre].setStatus(msg['estado'], msg['consumo'])
            if destino == "Arduinos":
                pass
    
    def update(self):
        e = 0
        p = 0
        for i in self.inversores:
            e += i.getExcedente()
            p += i.getProduccion()
        self.excedente = e
        self.produccion = p
        
        try:
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string("                    ")
            self.lcd.cursor_pos = (0, 0)
            self.lcd.write_string("P:%s E:%s C:%s" % (str(int(self.inversor.produccion)),str(int(self.inversor.excedente)),str(int(self.inversor.produccion+self.inversor.excedente))))
        except:
            self.resetLCD()

        if (self.inversor.produccion>100 and self.lcdLuz == False):
            self.lcd.backlight_enabled = True
            self.lcdLuz=True
            self.logger.info("Las placas empiezan a producir. Encender LCD")
        if (self.inversor.produccion<=0 and self.lcdLuz == True):
            self.lcd.backlight_enabled = False
            self.lcdLuz=False
            self.logger.info("Las placas dejan de producir. Apagar LCD")
        
    def disponible_dispositivos(self, i):
        t=int(time.time())
        hora=datetime.now().hour
        tiempo = datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second
        disp = 0
        for d in range(i, len(self.dispositivos)):
            if d.pinPower >= 0 and d.powerAct > 0 and not d.modoManual and hora not in d.horasOn and not (d.tiempoHoy+tiempo >= d.horaCorte and tiempo < d.horaCorte) and (d.horaEncendido + d.minTiempoSeguido < t):
                disp += d.consumo
        return(disp)
        
    def repartir(self):
        algunCambio = 0
        lcdLin=1
        lcdPos=0
        self.update()
        self.dispositivos.sort(key=get_tiempo_hoy, reverse=True) if self.excedente < 0 else self.capacitativos.sort(key=get_tiempo_hoy, reverse=False) #Reordeno los capacitativos para que se encienda/apague el que lleve menos/mas tiempo
        i = 0
        for d in self.dispositivos:
            ''' 
			Si hay varios dispositivos encendidos "cediendo" su consumo el disponible puede ser positivo cuando en realidad estoy consumiendo
			Si el dispositivo esta apagado intentara "robar" a los de menos prioridad.
			'''
            disponible = self.excedente - self.disponible_dispositivos(i) if d.powerAct == 0 else self.excedente
            i+=1
            t=int(time.time())
            th = (d.tiempoHoy - t + d.horaEncendido) if d.encendido else d.tiempoHoy
            hora=datetime.now().hour
            tiempo = datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second  #segundos trascurridos hoy
            
            if hora in d.horasOn:											#Si es hora de estar encendido lo enciendo
                E = 255
            elif hora in d.horasOff:
                E = 0
            elif (d.tiempoMaximo != 0) and (d.get_tiempo_hoy()<0): #Si tiempoMaximo es distinto de 0 y ha pasado ese tiempo encendido, lo apago.
                E = 0
            elif (d.tiempoHoy+tiempo >= d.horaCorte and tiempo < d.horaCorte):	#Si se acaba el tiempo para la programacion diaria
                E = 255
            elif (d.consumirExcedente) or (d.tiempoHoy > 0):											#Si hay que consumir escedentes
                if disponible <= -(d.power-(d.minP/2)) :		#Si hay disponible suficiente enciendo 
                    E = 255
                elif (disponible <= d.minP and d.powerAct > 0): #Si consumo por debajo del minimo y ya estoy encendido sigo encendido
                    E = 255
                else:												#Si estoy consumiendo paro
                    E = 0
            else:
                E = 0									#Si no hay que repartir execentes, paro
            
            if d.tipo == "capacitativo" and d.powerAct != E and d.setPower(E):              # Si es un capacitativo
                #Lo muestro en la LCD                                                       # La potencia cambia
                lcdDatos=str(d.nombre+":"+str("ON" if d.powerAct != 0 else "OFF")+" ")      # Y se realiza el cambio
                if (lcdLin<=3):                                                             # Lo muestro en la LCD y termino
                    try:
                        self.lcd.cursor_pos = (lcdLin, lcdPos)
                        self.lcd.write_string(lcdDatos)
                    except:
                        self.resetLCD()
                if lcdPos==10: lcdLin+=1
                lcdPos = 0 if (lcdPos==10) else 10
                
                time.sleep(0.5)
                break

            if d.tipo == "resistivo":
                if (d.consumirExcedente) or (d.tiempoHoy > 0):
                    if disponible < -(d.power) :					#Si voy sobrado me pongo a tope
                        E = 255
                    elif disponible <= -(d.minP/2):					#Si me sobra por encima de minimo, sumo un 20% del sobrante
                        E = d.powerAct+int(-disponible*2/100)
                        if E<50:E=50											#Me aseguro de empezar por encima del minimo
                    elif -(d.minP/4) > disponible > -(d.minP/2):  				#Si me sobra entre minP y minP/2 sumo 1
                        E = d.powerAct+1
                    elif 0 >= disponible >= -(d.minP/4):					#Si sobra entre 0 y minP/4 inyecto el excedente a la red
                        E = d.powerAct
                    elif d.power > disponible > 0:				#Si estoy consumiendo bajo el cosumo
                        E = d.power-int(disponible*2/100)
                    else:														# En otro caso (Consumo mas del maximo) pongo a 0
                        E=0
                else:															#Si no es la hora y no hay que consumir me pongo a 0
                    E = 0
                
                #Corrijo maximos y minimos
                if p>255: p=255			#Si paso el maximo limito
                if p<50: p=0			#Si no llego al minimo apago
                
                if d.powerAct != E and d.setPower(E):   # Si hay cambio y se produce el cambio
                    #Lo muestro en la LCD	
                    lcdDatos=str(d.nombre+":"+str(int(p*0.392156863))+"% ") #Multiplico para calcular el %
                    if (lcdLin<=3):
                        try:
                            self.lcd.cursor_pos = (lcdLin, lcdPos)
                            self.lcd.write_string(lcdDatos)
                        except:
                            self.resetLCD()
                    if lcdPos==10: lcdLin+=1
                    lcdPos = 0 if (lcdPos==10) else 10
                    
                    time.sleep(0.5)
                    break
            
            self.update()
            
    def paradaEmergencia(self, logText = "PARADA DE EMERGENCIA Superado maximo KWs permitidos ", espera=60):
        self.logger.warning(str(logText)+" "+str(int(self.inversor.excedente))+" de "+str(int(self.maxRed)))
        while True:	#do while bucle
            for d in self.dispositivos:
                d.emergencia = True
                d.setPower(0)
            try:
                self.lcd.backlight_enabled = True
                self.lcdLuz=True
                self.lcd.clear()
                self.lcd.cursor_pos = (1,5)
                self.lcd.write_string("PARADA  DE")
                self.lcd.cursor_pos = (2,5)
                self.lcd.write_string("EMERGENCIA")
            except:
                self.resetLCD()
            time.sleep(10)
            self.update()			
            if self.excedente < self.maxRed: #¢ondicion de salida
                break
				
        for i in range(1, espera+1):
            try:
                self.lcd.clear()
                self.lcd.cursor_pos = (0,0)
                self.lcd.write_string("PARADA DE EMERGENCIA")
                self.lcd.cursor_pos = (1,0)
                self.lcd.write_string("Reactivacion en ")
                self.lcd.cursor_pos = (2,5)
                self.lcd.write_string(str(espera+1-i)+" segundos")
            except:
                self.resetLCD()
            time.sleep(1)
        for d in self.dispositivos:
            d.emergencia = False
        self.update()
        self.logger.warning("PARADA DE EMERGENCIA TERMINADA: "+str(int(self.inversor.excedente))+" de "+str(int(self.maxRed)))      
        
########### ctrl+c cierra el programa ############	
def salidaAlegre(signal_received, frame):
	global kill_threads
	kill_threads = True
	time.sleep(5)
	print('SIGINT o CTRL-C detectado. Saliendo alegremente')
	logger = logging.getLogger('main')
	logger.setLevel(logging.DEBUG)
	fh = logging.FileHandler('excedentes.log')
	fh.setLevel(logging.DEBUG)
	logger.addHandler(fh)
	formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	logger.addHandler(fh)
	logger.info('Salida alegre solicitada......bye bye')
	exit(0)

########### MAIN ############
def principal():
	# Tell Python to run the handler() function when SIGINT is recieved
    signal(SIGINT, salidaAlegre)
    global kill_threads
	
    logger = logging.getLogger('main')
    logger.setLevel(logging.DEBUG)
    fh = logging.FileHandler('excedentes.log')
    fh.setLevel(logging.DEBUG)
    logger.addHandler(fh)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    logger.info('Inciando programa')
	
	# nuevaConf = False 
    casa = instalacion()
    while not kill_threads:
        if casa.excedente > casa.maxRed:
            casa.paradaEmergencia()
        else:
            casa.repartir()
    '''            
		lock = FileLock("excedentes.conf.lock")
		with lock:
			with open('excedentes.conf') as fileConf:
				conf = json.load(fileConf)
				nuevaConf = conf['nuevaConf']
		if nuevaConf:
			for r in casa.resistivos:
				r.nuevaConf()
			for c in casa.capacitativos:
				c.nuevaConf()
			with lock:
				with open('excedentes.conf','w') as fileConf:
					conf['nuevaConf'] = False
					json.dump(conf, fileConf, indent=4)
    '''
    casa.mqtt_client.disconnect()
    casa.paradaEmergencia("SALIENDO",10)
	

		
if __name__ == "__main__":
	# Tell Python to run the handler() function when SIGINT is recieved
	signal(SIGINT, salidaAlegre)
	
	principal()