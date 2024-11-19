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
	def __init__(self,nombre, broker_address, mqtt_client):
		self.nombre=nombre
		self.online = True
		self.kill_threads = False
		self.broker_address = broker_address
		self.client = mqtt_client
		
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

		self.subscribe()

	def subscribe(self):
		pass

#Arduino conectado por puerto serie		
class arduino_serial(arduino):	
	def __init__(self,nombre,pto, broker_address, mqtt_client):
		super().__init__(nombre, broker_address, mqtt_client)
		self.pto=pto
		self.puerto = self.creaPuerto(pto)
		self.semaforoCom = threading.Semaphore(1)	#Semaforo para maniobrar el arduino
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
		time.sleep(2)
		return(puerto)
		
	def enviaComando(self,comando):
		salida=True
		comandoBytes = comando.encode(encoding="utf-8")
		comandoBytes += b'\n'
		with self.semaforoCom:
			#self.logger.debug("Bloqueo el semaforo")
			try:
				self.puerto.write(comandoBytes);
				time.sleep(0.1)
			except:
				self.logger.error("Al enviar comando a %s" % self.nombre)
				salida=False
			#self.logger.debug("Desbloqueo el semaforo")

#		try:
#			respuesta = self.puerto.readline().decode("utf-8")
#			print("-"+respuesta+"-")		
#			if str(respuesta) == '':
#				respuesta=self.reset()
#				salida=False	
#		except Exception as e:
#			self.logger.error("Enviado comando a %s error:%s" %(self.nombre,e))
#			salida=False

		self.online = salida
		return(salida)
	
	def reset(self):
		self.logger.error("MIERDA, EL ARDUINO SE HA COLGADO!!!!")
		delattr(self,"puerto")
		self.puerto = self.creaPuerto(self.pto)
		self.puerto.close()
		self.puerto.open()
		self.puerto.setDTR(False)							#Flanco de bajada resetea arduino
		time.sleep(0.3)  
		self.puerto.flushInput()							# Se borra cualquier data que haya quedado en el buffer
		self.puerto.setDTR()								#Flanco de subida
		time.sleep(0.3)
		with self.semaforoCom:
			try:
				respuesta = self.puerto.readline().decode("utf-8")	#Espero la respuesta de arduino
			except Exception as e:
				respuesta = "No hay respuesta, error %s" %e
		self.logger.warning("Reseteo arduino, respuesta: -"+str(respuesta))
		return(respuesta)
			
	def setPin(self,nombre,valor):
		return(self.enviaComando('{"command":"setPin", "dispositivo":"'+nombre+'", "valor":"'+str(valor)+'"}'))
	
	def setup(self, tipo, nombre, pin, pinPower):
		msg = '{"command":"setup", "tipo":"'+tipo+'","nombre":"'+nombre+'", "pin":'+str(pin)+', "pinPower":'+str(pinPower)+'}'
		self.logger.info("Hago setup:%s-" % msg)
		self.enviaComando(msg)
		
	def subscribe(self):
		self.client.subscribe("Arduinos/%s/event" % self.nombre)
		self.client.subscribe("Arduinos/%s/online" % self.nombre)

#arduino conectado por MQTT	
class arduino_MQTT(arduino):	
	def __init__(self,nombre, broker_address, mqtt_client):
		super().__init__(nombre, broker_address, mqtt_client)
		#self.broker_address = broker_address
		#self.client = mqtt_client
		self.conexion = "MQTT"

	def enviaComando(self,mensaje):
		#client = mqtt.Client("Solar")
		#client.on_connect = self.on_connect
		try:
			self.client.connect(self.broker_address)

			topic='Arduinos/'+self.nombre+'/command'
			self.client.publish(topic,mensaje)
			self.client.disconnect()
			return(True)
		except:
			return(False)
	
	def setPin(self,nombre,valor):
		return(self.enviaComando('{"command":"setPin", "dispositivo":"'+nombre+'", "valor":"'+str(valor)+'"}'))

	def reset(self):
		self.logger.info("Reseteando...")
		self.enviaComando('{"command":"reset"}')

	def subscribe(self):
		self.client.subscribe("Arduinos/%s/event" % self.nombre)
		self.client.subscribe("Arduinos/%s/online" % self.nombre)
  
	def setup(self, tipo, nombre, pin, pinPower):
		msg = '{"command":"setup", "tipo":"'+tipo+'","nombre":"'+nombre+'", "pin":'+str(pin)+', "pinPower":'+str(pinPower)+'}'
		self.logger.info("Hago setup: %s" % msg)
		self.enviaComando(msg)

class shelly(arduino):
	def __init__(self, nombre, broker_address, mqtt_client):
		super().__init__(nombre, broker_address, mqtt_client)
		#self.broker_address = broker_address
		delattr(self,"pin")
		self.conexion = "MQTT"

	def enviaComando(self, mensaje):
		#client = mqtt.Client("Solar")
		#client.on_connect = self.on_connect
		self.client.connect(self.broker_address)
		
		topic='Shellys/'+self.nombre+'/rpc'
		self.client.publish(topic,mensaje)
		self.client.disconnect()
		return(True)
	
	def setPin(self, nombre, valor):
		valor  = True if valor == 255 else False
		return(self.enviaComando('{"id":1, "src":"Shellys/'+nombre+'/respuestas", "method":"Switch.Set","params":{"id":0,"on":'+str(valor).lower()+'}}'))

	def reset(self):
		self.enviaComando('{"id":1, "method":"Shelly.Reboot"}')
  
	def subscribe(self):
		self.client.subscribe("Shellys/%s/status/switch:0" % self.nombre)
		self.client.subscribe("Shellys/%s/online" % self.nombre)

	def setup(self):
		pass
