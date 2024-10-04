import logging
import time
import threading
from datetime import datetime
import json
from filelock import Timeout, FileLock
import paho.mqtt.client as mqtt #import the client1



class dispositivo:
	def __init__(self, tipo, nombre, power, ardu, pinconect, pinpower, hOn, hOff, consumirE, tiempoAlDia=3600,tiempoMaximo=0, minTiempoSeguidoEnMarcha=10, horaC=12, minPo=20):
		self.tipo = tipo
		self.nombre=nombre
		self.power = int(power)
		self.powerAct = 0
		self.ard = ardu
		self.pin = pinconect
		self.pinToGetPower = pinpower
		self.minP = power*minPo/100
		self.horasOn = hOn
		self.horasOff = hOff
		self.consumExcedente = consumirE
		self.consumo = 0

		self.tiempoDiario=tiempoAlDia*60
		self.tiempoMaximo=tiempoMaximo*60
		self.minTiempoSeguido = minTiempoSeguidoEnMarcha*60
		self.setTiempoHoy(self.tiempoDiario, True)
		self.horaCorte = horaC * 3600
		self.emergencia = False
		self.modoManual = False

		#Creo un semaforo para maniobrar el dispositivo
		self.semaforoCom = threading.Semaphore(1)

		self.setPower(0)					#Inicializo apagado
		self.kill_threads = False

		#Creo el logger del resistivo
		self.logger = logging.getLogger(self.nombre)
		self.logger.setLevel(logging.DEBUG)
		fhd = logging.FileHandler('excedentes.log')
		fhd.setLevel(logging.DEBUG)
		self.logger.addHandler(fhd)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fhd.setFormatter(formatter)
		self.logger.addHandler(fhd)
		
		#creo un hilo que carge la configuacion cada dia
		self.r = threading.Thread(target=self.threadDiario)
		self.r.setDaemon(True)
		self.r.start()
	
	def threadDiario(self):

		while not self.kill_threads:
			h=datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second		
			if (h<self.horaCorte):
				dormir = self.horaCorte-h
			else:
				dormir = self.horaCorte+(86400-h)
			#self.logger.info("Son las: "+str(h)+" HoraCorte es: "+str(self.horaCorte)+" Faltan: "+str(dormir))
			time.sleep(dormir)
			self.nuevaConf()
			self.resetea()
			
		self.logger.info("Matando hilo diario {}".format(self.nombre))

	def setPower(self,valor):
		with self.semaforoCom:	#Activo el semaforo para evitar concurrencias en el apagado
			t=int(time.time())
			if (self.horaEncendido+self.minTiempoSeguido < t) or (self.emergencia):
				self.ard.setpin(self.nombre, valor)
				return(True)						
			else:
				return False

	def resetea(self):
		if self.encendido:
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
					self.logger.error("No se ha podido abrir el archivo "+str(fileName))
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
					for c in conf['capacitativos']:
						if c["nombre"]==self.nombre:
							dias_semana=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
							self.horasOn = c["modos"][c['modoDia'][dia]]["timeOn"]
							self.horasOff = c["modos"][c['modoDia'][dia]]["timeOff"]
							self.consumirExcedente = c["modos"][c['modoDia'][dia]]['consumirExcedente']
							self.tiempoDiario = c["modos"][c['modoDia'][dia]]['tiempoAldia'] * 60
							self.minTiempoSeguido = c["modos"][c['modoDia'][dia]]['tiempoSeguido'] * 60
							self.tiempoMaximo = c["modos"][c['modoDia'][dia]]["tiempoMaximo"] * 60
							self.setTiempoHoy(self.tiempoDiario)
							self.horaCorte = c["modos"][c['modoDia'][dia]]['horaCorte'] * 3600
							self.modoManual = False
							self.logger.info("Cargada configuracion para el "+dias_semana[dia]+": "+str(c['modoDia'][dia]))
		except lock.Timeout:
			self.logger.error("No es posible bloquear el archivo excedentes.conf.lock")
		except:
			self.logger.error("No es posible cargar la nueva configuracion")
