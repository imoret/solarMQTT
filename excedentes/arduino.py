import logging
import threading
import serial,time, sched
import json
import paho.mqtt.client as mqtt

class pin:
	def __init__(self,mode = "OUTPUT",value = 0):
		if mode == "OUTPUT" or mode == "INPUT":		
			self.pinMode = mode
		else:
			print ("Error al crear pin: pinMode error")
			
		if value >= 0 and value <= 255:
			self.pinValue = value
		else:
			print ("Error al crear pin: pinValue error")
		self.consumo=0
			
	def setPinMode(self,mode):
		if mode == "OUTPUT" or mode == "INPUT":		
			self.pinMode = mode
		else:
			print ("Error al asignar modo al pin: pinMode error")
	
	def setPinValue(self,value):
		if value >= 0 and value <= 255:
			self.pinValue = value
		else:
			print ("Error al crear pin: pinValue error")
	
#Arduino "metaClase"
class arduino:
	def __init__(self,nombre,):
		self.nombre=nombre
		self.online = True
		self.kill_threads = False
		
		#Defino los pines
		self.pin = []
		for i in range(14):
			newPin = pin()
			self.pin.append(newPin)
		
		#Creo el logger del arduino
		self.logger = logging.getLogger(self.nombre)
		self.logger.setLevel(logging.DEBUG)
		fhd = logging.FileHandler('excedentes.log')
		fhd.setLevel(logging.DEBUG)
		self.logger.addHandler(fhd)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fhd.setFormatter(formatter)
		self.logger.addHandler(fhd)

#Arduino conectado por puerto serie		
class arduino_serial(arduino):	

	def __init__(self,nombre,pto):
		super().__init__(nombre)
		self.pto=pto
		self.puerto = self.creaPuerto(pto)
		self.conexion = "serial"
	
	def creaPuerto(self, pto):
		puerto = serial.Serial(pto, baudrate=9600, timeout=3.0)
		#self.puerto.setDTR(False)
		time.sleep(3)
		# toss any data already received, see
		# http://pyserial.sourceforge.net/pyserial_api.html#serial.Serial.flushInput
		puerto.flushInput()
		#self.puerto.setDTR(False)
		puerto.close()
		puerto.open()
		return(puerto)
	
	def recibeComando(self):		
		comandos = {b'1': self.clicLCD, b'2': self.giroDerecha, b'3':self.giroIzq} #Diccionario de comandos/funciones
		comando = 0
		
		while not self.kill_threads:
			with self.semaforoCom:
				try:
					if self.puerto.in_waiting > 0:
						comando = self.puerto.readline().decode("utf-8").strip()
						#self.logger.debug("He recibido un comando:" +comando)
						try:
							comandoJson = json.loads(comando)
							#self.logger.debug("JSON: " +str(comandoJson))
							if (comandoJson["comando"]=="consumo"):
								if (comandoJson["consumo"]<0):comandoJson["consumo"]=0
								self.pin[comandoJson["pin"]].consumo = comandoJson["consumo"]
								#self.logger.debug("Pin: "+str(comandoJson["pin"])+" puesto a "+str(self.pin[comandoJson["pin"]].consumo ))
						except:
							pass
							#self.logger.error("JSON: invalido")
					#self.puerto.reset_input_buffer()
				except:
					#self.logger.debug("Este dispositivo no se comunica por puerto serie, no se admiten comandos")
					exit()
			if comando in comandos:
				self.logger.debug("Ejecuto: "+str(comandos[comando]))
				comandos[comando]()	
			comando = 0
			time.sleep(0.1)
		self.logger.info("Matando hilo<--------------------------------------------")
		
	def enviaComando(self,comando):
		salida=True
		comandoBytes = comando.encode()
		with self.semaforoCom:
			self.puerto.write(comandoBytes);
			time.sleep(0.1)
			respuesta = self.puerto.readline().decode("utf-8")
			#self.logger.debug("Respuesta Arduino: "+str(respuesta))
			while str(respuesta) == '':
				respuesta=self.reset()
				salida=False
			#self.puerto.reset_input_buffer()
			#self.puerto.close()
		self.online = salida
		return(salida)

	def reset(self):
		self.logger.error("MIERDA, EL ARDUINO SE HA COLGADO!!!!")
		self.puerto.close()
		self.puerto.open()
		self.puerto.setDTR(False)							#Flanco de bajada resetea arduino
		time.sleep(0.3)  
		self.puerto.flushInput()							# Se borra cualquier data que haya quedado en el buffer
		self.puerto.setDTR()								#Flanco de subida
		time.sleep(0.3)
		respuesta = self.puerto.readline().decode("utf-8")	#Espero la respuesta de arduino
		self.logger.warning("Reseteo arduino, respuesta: -"+str(respuesta))
		return(respuesta)
			
	def setPin(self,nombre,valor):
		return(self.enviaComando('{"command":"setPin", "dispositivo":"'+nombre+'", "valor":"'+valor+'"}'))

#arduino conectado por MQTT	
class arduino_MQTT(arduino):	
	def __init__(self,nombre,broker_address):
		super().__init__(nombre)
		self.broker_address = broker_address
		self.conexion = "MQTT"

	def enviaComando(self,mensaje):
		client = mqtt.Client("Solar")
		#client.on_connect = self.on_connect
		client.connect(self.broker_address)

		topic='Arduino/'+self.nombre+'/command'
		client.publish(topic,mensaje)
		client.disconnect()
		return(True)
	
	def setPin(self,nombre,valor):
		return(self.enviaComando('{"command":"setPin", "dispositivo":"'+nombre+'", "valor":"'+valor+'"}'))

	def reset(self):
		self.enviaComando('{"command":"reset"}')

	def subscribe(self, client):
		client.subscribe("Arduinos/%s/event" % self.nombre)
		client.subscribe("Arduinos/%s/online" % self.nombre)
  
	def setup(self, tipo, nombre, pin, pinPower):
		msg = '{"command":"setup", "tipo":'+tipo+',"nombre":'+nombre+', "pin":'+pin+', "pinPower":'+pinPower+'}'
		self.enviaComando(msg)

class shelly(arduino):
	def __init__(self, nombre, broker_address):
		super().__init__(nombre)
		self.broker_address = broker_address
		delattr(self.pin)
		self.conexion = "MQTT"

	def enviaComando(self, mensaje):
		client = mqtt.Client("Solar")
		#client.on_connect = self.on_connect
		client.connect(self.broker_address)
		
		topic='Shellys/'+self.nombre+'/rpc'
		client.publish(topic,mensaje)
		client.disconnect()
		return(True)
	
	def setPin(self, nombre, valor):
		return(self.enviaComando('{"id":1, "src":"Shellys/'+nombre+'/respuestas", "method":"Switch.Set","params":{"id":0,"on":'+str(valor).lower()+'}}'))

	def reset(self):
		self.enviaComando('{"id":1, "method":"Shelly.Reboot"}')
  
	def subscribe(self, client):
		client.subscribe("Shellys/%s/status/switch:0" % self.nombre)
		client.subscribe("Shellys/%s/online" % self.nombre)
  