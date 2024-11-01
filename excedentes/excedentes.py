from math import trunc
import json
import logging
import threading
import operator
from dispositivo import dispositivo
from arduino import arduino_serial, arduino_MQTT, shelly
from lcd import lcd
from inversor import fronius
from signal import signal, SIGINT
from sys import exit
from filelock import Timeout, FileLock
import serial,time, sched
from datetime import datetime
import paho.mqtt.client as mqtt #import the client1
from RPLCD import i2c

kill_threads = False

class instalacion:
    def __init__(self):
        global kill_threads
        
        self.inversores = {}
        self.arduinos = {}
        self.dispositivos = {}
        
        self.produccion = 0
        self.excedente = 0 
        
		#Creo el logger de la instalacion
        self.logger = logging.getLogger('instalacion')
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

                #Creo la LCD
                if conf['data']['lcd']:
                    lat = conf['data']['lat']
                    lon = conf['data']['lon']
                    self.lcd = lcd(lat, lon)
                else:
                    self.lcd = False
				
                #Preparo el MQTT
                self.broker_address = conf['data']['broker_address']
                self.mqtt_client = mqtt.Client("solar_MQTT")
                self.mqtt_client.on_message = self.on_message 
                self.mqtt_client.on_connect = self.on_connect
                self.mqtt_client.on_disconnect = self.on_disconnect
                self.mqtt_client.on_subscribe = self.on_subscribe
                self.mqtt_client.on_unsubscribe = self.on_unsubscribe
                self.logger.info("Inicio conexion al servidor MQTT")
                self.mqtt_client.connect(self.broker_address)
                
                self.logger.info("Cargando inversores")
                for i in conf['inversores']:				#Lo recorro pero se que solo hay uno
                    aux = fronius(i['nombre'],i['ip'])
                    self.inversores[i['nombre']] = aux
                    
                self.logger.info("Cargando arduinos serial")
                for a in conf['arduinos_serial']:
                    aux=arduino_serial(a['nombre'],a['puerto'])
                    self.arduinos[a['nombre']]=aux
                    self.arduinos[a['nombre']].subscribe(self.mqtt_client)

                self.logger.info("Cargando arduinos MQTT")   
                for l in conf['arduinos_MQTT']:
                    aux=arduino_MQTT(l['nombre'],self.broker_address)
                    self.arduinos[l['nombre']]=aux
                    self.arduinos[l['nombre']].subscribe(self.mqtt_client)
                    
                self.logger.info("Cargando Shellys")
                for s in conf['shellys']:
                    aux=shelly(s['nombre'],self.broker_address)
                    self.arduinos[s['nombre']]=aux
                    self.arduinos[s['nombre']].subscribe(self.mqtt_client)
                
                self.logger.info("Cargando dispositivos")
                for d in conf['dispositivos']:
                    tipo = d['tipo']
                    nombre = d['nombre']
                    power = d['power']
                    ardu = self.arduinos[d['ardu']]
                    pin = d['pin']
                    pinPower = d['pinPower']
                    t_on = d["modos"][d['modoDia'][datetime.today().weekday()]]["timeOn"]
                    t_off = d["modos"][d['modoDia'][datetime.today().weekday()]]["timeOff"]
                    consumirE = d["modos"][d['modoDia'][datetime.today().weekday()]]["consumirExcedente"]
                    tiempo_al_dia = d["modos"][d['modoDia'][datetime.today().weekday()]]["tiempoAldia"]
                    tiempo_maximo = d["modos"][d['modoDia'][datetime.today().weekday()]]["tiempoMaximo"]
                    tiempo_seguido = d["modos"][d['modoDia'][datetime.today().weekday()]]["tiempoSeguido"]
                    hora_corte = d["modos"][d['modoDia'][datetime.today().weekday()]]["horaCorte"]
                    minPo = d['minPo']
                    tReact = d['tiempo_reaccion']
                    aux = dispositivo(tipo, nombre, power, ardu, pin, pinPower, t_on, t_off, consumirE, tiempo_al_dia, tiempo_maximo, tiempo_seguido, hora_corte, minPo, tReact)
                    self.dispositivos[d['nombre']] = aux
                    self.dispositivos[d['nombre']].subscribe(self.mqtt_client)
                    
                

        #Creo un hilo que actualiza la produccion/excedente
        self.update_control = threading.Thread(target=self.update)
        self.update_control.daemon = True
        self.update_control.start()

        #Creo un hilo para cada arduino serial que sera el encargado de recibir mensajes
        for a in self.arduinos.values():
            if a.conexion == "serial":
                self.receptor = threading.Thread(target=self.recibeComando, args=(a.puerto, a.semaforoCom, a.nombre))
                self.receptor.daemon = True
                self.receptor.start()
        
        #Creo un hilo que gestiona las conexiones MQTT.
        self.semaforoCom = threading.Semaphore(1)	#Semaforo para maniobrar el arduino
        self.mqtt_control = threading.Thread(target=self.thread_mqtt)
        self.mqtt_control.daemon = True
        self.mqtt_control.start()

        #Reinicio los arduinos
        time.sleep(5)
        for a in self.arduinos.values():
            a.reset()

    def recibeComando(self, puerto, semaforoCom, arduino):		
        global kill_threads
        while not kill_threads:
            with semaforoCom:
                #self.logger.debug("Bloqueo el semaforo")
                try:
                    if puerto.in_waiting > 0:
                        comando = puerto.readline().decode("utf-8").strip()
                        #self.logger.debug("He recibido un comando:" +comando)
                        #try:
                        comandoJson = json.loads(comando)
                        decoded_message = json.dumps(comandoJson['mensaje'])
                        #decoded_message = str(comandoJson['mensaje'].decode("utf-8"))
                        canal = comandoJson['canal']
                        destino = comandoJson['destino']
                        nombre = comandoJson['nombre'] 
                        
                        client = mqtt.Client("Solar")
                        client.connect(self.broker_address)

                        topic=destino+'/'+nombre+'/'+canal
                        client.publish(topic,decoded_message)
                        client.disconnect()
                            
                            #self.logger.debug("Proceso: %s %s %s msg %s" % (canal, destino, nombre, decoded_message))
                            #procesandoComando = threading.Thread(target=ard.publica_comando, args=(decoded_message, canal, destino, nombre))
                            #procesandoComando.daemon = True
                            #procesandoComando.start()
                            #self.procesaComando(decoded_message, canal, destino, nombre)
                        #except Exception as e:
                         #   self.logger.error(e)
					#self.puerto.reset_input_buffer()
                except Exception as e:
                    pass
                    #self.logger.error("En recibeComando: %s" % e)
                    #self.arduinos[arduino].reset()
                    #exit()
                #self.logger.debug("Desbloqueo el semaforo")

            time.sleep(0.1)
        self.logger.info("Matando hilo<--------------------------------------------")

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

        #Creo un hilo que procesará el comando recibido
        self.procesa = threading.Thread(target=self.procesaComando, args=(decoded_message, canal, destino, nombre))
        self.procesa.daemon = True
        self.procesa.start()
        #self.logger.info("On Message:%s"%decoded_message)

    def procesaComando(self, decoded_message, canal, destino, nombre):
        #self.logger.debug("ProcesaComando canal:%s destino:%s nombre:%s" % (canal, destino, nombre))
        #Si recibo un online
        if canal == "online":
            if (destino == "Shellys" or destino == "Arduinos"):
                self.arduinos[nombre].online = True if decoded_message == 'true' else False
                #self.logger.debug("%s online a %s" % (nombre, decoded_message))
            if destino == "Dispositivos":
                self.dispositivos[nombre].online = True if decoded_message == 'true' else False
                #self.logger.debug("%s online a %s" % (nombre, decoded_message))
                
                
        #Si recibo un evento
        if canal == "event":
            if destino == "Shellys":
                pass
            if destino == "Arduinos":
                msg=json.loads(decoded_message)
                if msg['event'] == 'init':
                    #self.logger.info("Mensaje recibido: %s" % decoded_message)
                    a = self.arduinos[nombre]
                    self.logger.info("Configuro dispositivos de %s" % nombre)
                    for d in self.dispositivos.values():
                        if a.nombre == d.ard.nombre:
                            self.logger.info("Orden setup para %s" % d.nombre)
                            d.setup()
            if destino == "Dispositivos":
                pass
        
        #Si recibo un status    
        if canal == "status":
            msg=json.loads(decoded_message)

#          if destino == "Shellys":
#              d = self.dispositivos[nombre]
#             newPower = 255 if str(msg["output"]) == 'True' else 0
#                if newPower != d.powerAct and d.powerAct == 0:
#                    d.horaEncendido = int(time.time())
#                d.powerAct = newPower
#                d.consumo = msg["apower"]
#                #self.logger.debug("%s power puesto a:%s" %(nombre, d.powerAct))
#                if (msg["source"] != 'init' and msg["source"] != 'MQTT' and d.modoManual == False):
#                    #d.logger.info("Puesto en modo manual");
#                    d.modoManual = True
#                if ((msg["source"] == 'init' or msg["source"] == 'MQTT') and d.modoManual == True): 
#                    #d.logger.info("Puesto en modo automatico");
#                    d.modoManual = False
            if destino == "Shellys":
                newPower = 255 if str(msg["output"]) == 'True' else 0
                self.dispositivos[nombre].setStatus(newPower, msg["apower"])
                if self.lcd:
                    self.lcd.muestra_dispositivos(self.dispositivos.values())

            if destino == "Dispositivos":
                self.dispositivos[nombre].setStatus(msg['estado'], msg['consumo'])
                if self.lcd:
                    self.lcd.muestra_dispositivos(self.dispositivos.values())
                #self.logger.debug("%s status:%s consumo:" %(nombre, str(self.dispositivos[nombre].powerAct), str(self.dispositivos[nombre].consumo)))

            if destino == "Arduinos":
                pass
    
    def update(self):
        while not kill_threads:
            e = 0
            p = 0
            for i in self.inversores.values():
                e += i.getExcedente()
                p += i.getProduccion()
            self.excedente = e
            self.produccion = p
            #self.logger.info("Produccion %s Excedente %s" % (p,e))
            if self.lcd:   
                self.lcd.muestraProduccion(trunc(p),trunc(e))
            time.sleep(0.5)
        
    def disponible_dispositivos(self, i):
        copy_dispositivos = dict(sorted(self.dispositivos.items(), key=lambda dis: dis[1].get_tiempo_hoy()))    # Ordeno siempre en ascendente
        copy_dispositivos = dict(list(copy_dispositivos.items())[:i+1])                                         # corto desde la posicion dada + 1
        t=int(time.time())
        hora=datetime.now().hour
        tiempo = datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second
        disp = 0
        for d in copy_dispositivos.values():
            if d.pinPower >= 0 and d.powerAct > 0 and not d.modoManual and hora not in d.horasOn and not (d.tiempoHoy+tiempo >= d.horaCorte and tiempo < d.horaCorte) and (d.horaEncendido + d.minTiempoSeguido < t):
                disp += d.consumo
                #self.logger.debug("      %s cede %s. Total %s" % (d.nombre, d.consumo, disp))
        return(disp)
        
    def repartir(self):
        self.dispositivos = dict(sorted(self.dispositivos.items(), key=lambda dis: dis[1].get_tiempo_hoy(), reverse=(self.excedente < 0)))
        i = 0
        for d in self.dispositivos.values():
            ''' 
			Si hay varios dispositivos encendidos "cediendo" su consumo el disponible puede ser positivo cuando en realidad estoy consumiendo
			Si el dispositivo esta apagado intentara "robar" a los de menos prioridad.
			'''
            #self.logger.info("Reparto %s" % d.nombre)
            disponible = self.excedente - self.disponible_dispositivos(i) if d.powerAct == 0 else self.excedente
            #self.logger.info("%s dipone de %s wh" % (d.nombre, disponible))
            i+=1
            t=int(time.time())
            th = (d.tiempoHoy - t + d.horaEncendido) if d.powerAct > 0 else d.tiempoHoy
            hora=datetime.now().hour
            tiempo = datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second  #segundos trascurridos hoy
            
            if hora in d.horasOn:											#Si es hora de estar encendido lo enciendo
                E = 255
                #self.logger.info("%s1" %d.nombre)
            elif hora in d.horasOff:
                E = 0
                #self.logger.info("2")
            elif (d.tiempoMaximo != 0) and (d.get_tiempo_hoy() < -d.tiempoMaximo): #Si tiempoMaximo es distinto de 0 y ha pasado ese tiempo encendido, lo apago.
                E = 0
                #self.logger.info("3")
            elif (d.tiempoHoy+tiempo >= d.horaCorte and tiempo < d.horaCorte):	#Si se acaba el tiempo para la programacion diaria
                E = 255
                #self.logger.info("4")
            elif (d.consumExcedente) or (d.tiempoHoy > 0):			#Si hay que consumir escedentes
                if d.tipo =="capacitativo":
                    if disponible <= -(d.power-(d.minP/2)) :		#Si hay disponible suficiente enciendo 
                        E = 255
                        #self.logger.info("5")
                    elif (disponible <= d.minP and d.powerAct > 0): #Si consumo por debajo del minimo y ya estoy encendido sigo encendido
                        E = 255
                        #self.logger.info("6")
                    else:												#Si estoy consumiendo paro
                        E = 0
                if d.tipo == "resistivo":
                    if abs(disponible) > d.power*0.5:               #Hay me sobra o consumo mas de un 50%
                        E = int(d.powerAct+(255*(-disponible/d.power)))                  #Hago un encendido/apagado proporcional
                        #self.logger.info("7")
                    elif abs(disponible) > d.power*0.25:
                        E = int(d.powerAct+(255*(-disponible/d.power)/2))
                    elif abs(disponible) > d.power*0.05:
                        E = int(d.powerAct+(255*(-disponible/d.power)/3))
                    elif disponible < 0:
                        E = d.powerAct + 1
                        #self.logger.info("8")
                    #Intento comsumir 20w para que el voltage sea el mínimo
                    elif disponible < 20:
                        E = d.powerAct
                    else:               #si consumo mas de 10 bajo despacio
                        E = d.powerAct- 1
                        #self.logger.info("8")
            else:
                E = 0									#Si no hay que repartir execentes, paro
                #self.logger.info("13")
            
            #self.logger.info("comparo %s con %s" %(d.powerAct, E))
            if E > 255 : E = 255
            if E < 0 : E = 0
            if d.powerAct != E:
                if d.setPower(E):              # Si ha habido cambios y se aceptan lo muestro en la LCD
                    self.logger.info("Produccion %s, excendente %s - Dispositivo %s con disponible %s puesto a %s" %(self.produccion, self.excedente, d.nombre, disponible, E))
                    time.sleep(d.tiempo_reaccion)
                    break
            
    def paradaEmergencia(self, logText = "PARADA DE EMERGENCIA Superado maximo KWs permitidos ", espera=60):
        self.logger.warning(str(logText)+" "+str(int(self.excedente))+" de "+str(int(self.maxRed)))
        while True:	#do while bucle
            for d in self.dispositivos.values():
                d.emergencia = True
                d.setPower(0)
            if self.lcd:
                self.lcd.parada_emergencia()               
            time.sleep(10)		
            if self.excedente < self.maxRed: #¢ondicion de salida
                break
				
        for i in range(1, espera+1):
            self.lcd.writeLine("PARADA DE EMERGENCIA", 0)
            self.lcd.writeLine("Reactivacion en ", 1)
            self.lcd.writeLine("     %s segundos" % str(espera+1-i), 2)
            time.sleep(1)
        for d in self.dispositivos.values():
            d.emergencia = False
        self.logger.warning("PARADA DE EMERGENCIA TERMINADA: "+str(int(self.excedente))+" de "+str(int(self.maxRed)))      
        
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
    for d in casa.dispositivos.values():
        d.kill_threads = True
    for a in casa.arduinos.values():
        a.kill_threads = True
    kill_threads = True
    casa.mqtt_client.disconnect()
    casa.paradaEmergencia("SALIENDO",10)
	

		
if __name__ == "__main__":
	# Tell Python to run the handler() function when SIGINT is recieved
	signal(SIGINT, salidaAlegre)
	
	principal()
