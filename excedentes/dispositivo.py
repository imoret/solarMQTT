import logging
import time
import threading
from datetime import datetime
import json
from filelock import Timeout, FileLock
import paho.mqtt.client as mqtt #import the client1

class dispositivo:
	def __init__(self, tipo, nombre, power, ardu, pinconect, pinpower, hOn, hOff, consumirE, tiempoAlDia=3600,tiempoMaximo=0, minTiempoSeguidoEnMarcha=10, horaC=12, minPower=20, tReact=0.5):
		self.tipo = tipo
		self.nombre=nombre
		self.power = int(power)
		self.powerAct = 0
		self.ard = ardu
		self.pin = pinconect
		self.pinPower = pinpower
		self.minPower = power*minPower/100
		self.horasOn = hOn
		self.horasOff = hOff
		self.consumExcedente = consumirE
		self.consumo = 0
		self.online = True

		self.tiempoDiario=tiempoAlDia*60
		self.tiempoMaximo=tiempoMaximo*60
		self.minTiempoSeguido = minTiempoSeguidoEnMarcha*60
		#self.setTiempoHoy(self.tiempoDiario, True)
		self.tiempoHoy = self.tiempoDiario
		self.horaEncendido = int(time.time())-self.minTiempoSeguido
		self.horaCorte = horaC * 3600
		self.tiempo_reaccion = tReact
		self.emergencia = False
		self.modoManual = False

		#Creo el logger del dispositivo
		self.logger = logging.getLogger(self.nombre)
		self.logger.setLevel(logging.DEBUG)
		fhd = logging.FileHandler('excedentes.log')
		fhd.setLevel(logging.DEBUG)
		self.logger.addHandler(fhd)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fhd.setFormatter(formatter)
		self.logger.addHandler(fhd)

		#Creo un semaforo para maniobrar el dispositivo
		self.semaforoCom = threading.Semaphore(1)

		#creo un hilo que carge la configuacion cada dia
		self.kill_threads = False
		self.r = threading.Thread(target=self.threadDiario)
		self.r.setDaemon(True)
		self.r.start()

		self.setPower(0)					#Inicializo apagado
		self.logger.info("inicio con t: %s y pmin %s" % (self.tiempoHoy, self.minPower))
	
	def threadDiario(self):
		while not self.kill_threads:
			h=datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second		
			if (h<self.horaCorte):
				dormir = self.horaCorte-h
			else:
				dormir = self.horaCorte+(86400-h)
			#self.logger.info("Son las: "+str(h)+" HoraCorte es: "+str(self.horaCorte)+" Faltan: "+str(dormir))
			for i in range(0, dormir):
				time.sleep(1)
				if self.kill_threads:
					break
			self.nuevaConf()
			self.resetea()
			
		self.logger.info("Matando hilo diario {}".format(self.nombre))
	
	def setPower(self, valor):
		with self.semaforoCom:	#Activo el semaforo para evitar concurrencias en el apagado
			t=int(time.time())
			if (self.horaEncendido+self.minTiempoSeguido <= t) or (self.emergencia) or self.powerAct < valor:  	# Acepta si: 	- ha pasado el tiempo minimo de encendido
				#self.logger.info("Setpower de %s a %s" % (self.nombre, valor))
				salida = self.ard.setPin(self.nombre, valor)																#				- Es una emergencia			
				return(salida)																					#				- Es un aumento de potencia
			else:
				return(False)

	def resetea(self):
		if self.powerAct > 0:
			t=int(time.time())
			self.horaEncendido=t

	def setTiempoHoy(self,newTiempo,recupera=False):
		fileName = str(self.nombre) + ".conf"
		lockFileName = str(fileName) + ".lock"
		lock = FileLock(str(lockFileName))
		with lock:
			#Recupera estará en true cuando quiera recuperar la configuracion. Reinicios, etc.
			if recupera:
				try:
					with open(str(fileName)) as fileConf:
						conf = json.load(fileConf)
						newTiempo = conf['tiempoHoy']
				except:
					print("No se ha podido abrir el archivo "+str(fileName))
					#self.logger.error("No se ha podido abrir el archivo "+str(fileName))
			with open(str(fileName),'w') as fileConf:
				conf = {}
				conf['tiempoHoy'] = newTiempo
				json.dump(conf, fileConf, indent=4)
			self.tiempoHoy = newTiempo

	def nuevaConf(self):
		h=datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second
		dia = datetime.today().weekday() if (h<self.horaCorte) else (datetime.today().weekday() + 1)
		dia = 0 if dia > 6 else dia
		lock = FileLock("excedentes.conf.lock", timeout=10)
		try:
			with lock:
				with open('excedentes.conf') as fileConf:
					conf = json.load(fileConf)
					for d in conf['dispositivos']:
						if d["nombre"]==self.nombre:
							dias_semana=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
							self.horasOn = d["modos"][d['modoDia'][dia]]["timeOn"]
							self.horasOff = d["modos"][d['modoDia'][dia]]["timeOff"]
							self.consumExcedente = d["modos"][d['modoDia'][dia]]['consumirExcedente']
							self.tiempoDiario = d["modos"][d['modoDia'][dia]]['tiempoAldia'] * 60
							self.minTiempoSeguido = d["modos"][d['modoDia'][dia]]['tiempoSeguido'] * 60
							self.tiempoMaximo = d["modos"][d['modoDia'][dia]]["tiempoMaximo"] * 60
							self.setTiempoHoy(self.tiempoDiario)
							self.horaCorte = d["modos"][d['modoDia'][dia]]['horaCorte'] * 3600
							self.modoManual = False
							self.minPower = d['minPower']
							self.logger.info("Cargada configuracion para el "+dias_semana[dia]+": "+str(d['modoDia'][dia]))
		except Exception as e:
			self.logger.error("No es posible cargar la nueva configuracion")
			self.logger.error(e)
   
	def subscribe(self, client):
		if self.ard.conexion == "MQTT" or self.ard.conexion == "serial":
			#self.logger.info("Suscripcion a: Dispositivos/%s/status" % self.nombre)
			client.subscribe("Dispositivos/%s/status" % self.nombre)
			client.subscribe("Dispositivos/%s/online" % self.nombre)
   
	def setup(self):
		self.ard.setup(self.tipo, self.nombre, self.pin, self.pinPower)

	def setStatus(self,powerAct, consumo):
		self.consumo = consumo
		if self.powerAct != powerAct:
			if self.powerAct > 0:
				#self.setTiempoHoy(self.get_tiempo_hoy())				#Guarda en un archivo el timepo del dia y es capaz de recuperarlos si se reinicia
				self.tiempoHoy = self.get_tiempo_hoy()
				#self.logger.info("Tiempo hoy: %.2f" %self.tiempoHoy)
			t=int(time.time())
			self.horaEncendido = t
			self.powerAct = powerAct

	def get_tiempo_hoy(self):
		t=int(time.time())
		p = self.powerAct/255 # Tanto por 100 de la potencia
		th = self.tiempoHoy - (t - self.horaEncendido) * p
		return(th)
	
	def publica_actividad(self, client):
		mensaje = '{"tiempo_hoy":%f, "manual":%s}'%(self.get_tiempo_hoy(), 'true' if self.modoManual else 'false')
		topic='Dispositivos/'+self.nombre+'/activity'
		client.publish(topic,mensaje)
