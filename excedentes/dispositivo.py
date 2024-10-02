import logging
import time
import threading
from datetime import datetime
import json
from filelock import Timeout, FileLock
import paho.mqtt.client as mqtt #import the client1

kill_threads = False

class dispositivo:
	def __init__(self, nombre, power, hOn, hOff, consumirE, minPo=20):
		self.nombre=nombre
		self.power = int(power)
		self.minP = power*minPo/100
		self.horasOn = hOn
		self.horasOff = hOff
		self.consumExcedente = consumirE
		self.consumo = 0
		self.setPower(0)					#Inicializo apagado

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
		while not kill_threads:
			self.nuevaConf()
			time.sleep(86402-(datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second))
			self.logger.info("El hilo threadDiario duerme "+str(86402-(datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second))+" segundos")
		self.logger.info("El hilo nuevaconf ha terminado <-----------------------")

# Clase componente resistivo
class resistivo(dispositivo):
	def __init__(self,nombre,power,ardu,pinconec,pinPower,hOn,hOff,consumirE,minPo=20):
		super().__init__(nombre, power, hOn, hOff, consumirE, minPo)
		self.powerAct = 0
		self.ard = ardu
		self.pin = pinconec
		self.pinToGetPower = pinPower
		self.consumExcedente = consumirE
		self.modoManual = False 

		self.setPower(0);
	
	def nuevaConf(self):
		lock = FileLock("excedentes.conf.lock", timeout=10)
		try:
			with lock:
				with open('excedentes.conf') as fileConf:
					conf = json.load(fileConf)
					for r in conf['resistivos']:
						if r["nombre"]==self.nombre:
							dias_semana=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
							self.horasOn = r["modos"][r['modoDia'][datetime.today().weekday()]]["timeOn"]
							self.horasOff = r["modos"][r['modoDia'][datetime.today().weekday()]]["timeOff"]
							self.consumExcedente = r["modos"][r['modoDia'][datetime.today().weekday()]]['consumirExcedente']
							self.logger.info("Cargada configuracion para el "+dias_semana[datetime.today().weekday()]+": "+r['modoDia'][datetime.today().weekday()])
		#except lock.Timeout:
		#	self.logger.error("No es posible bloquear el archivo excedentes.conf.lock")
		except:
			self.logger.error("No es posible cargar la nueva configuracion");
		
	def setPower(self,pw):
		self.ard.enviaComando('{"command":"setPin","dispositivo":"'+self.nombre+'", "valor":'+pw+'}')

class capacitativo(dispositivo):
	def __init__(self,nombre,power,ardu,pinconec,pinPower,hOn,hOff,consumirE,tiempoAlDia=3600,tiempoMaximo=0, minTiempoSeguidoEnMarcha=10, horaC=12, minPo=20):
		super().__init__(nombre, power, hOn, hOff, consumirE, minPo)
		self.encendido = False
		self.horaEncendido = int(time.time())

		self.ard=ardu
		self.pin=pinconec
		self.pinToGetPower = pinPower

		self.consumirExcedente = consumirE
		self.tiempoDiario=tiempoAlDia*60
		self.tiempoMaximo=tiempoMaximo*60
		self.minTiempoSeguido = minTiempoSeguidoEnMarcha*60
		self.setTiempoHoy(self.tiempoDiario, True)
		self.horaCorte = horaC * 3600
		self.emergencia = False
		self.modoManual = False 	#Modo manual inactivo(Solo para shellys, pero necesito el parametro en el reparto)

		self.setPower(False)
		
		#Creo un semaforo para maniobrar el capacitativo
		self.semaforoCom = threading.Semaphore(1)
	
	def setPower(self,E):
		with self.semaforoCom:	#Activo el semaforo para evitar concurrencias en el apagado
			t=int(time.time())
			if E :
				if self.ard.enviaComando('{"command":"setPin","dispositivo":"'+self.nombre+'", "valor":'+E+'}'):
					self.encendido = E	# #######ATENCION ESTA linea habrá que quitarla y otras tb
					self.horaEncendido=t
					
					#Si hay limite de ejecucion y no debo consumir excedentes creo un hilo que apagará el dispositivo al llegar la hora, si el dispositivo se apaga antes el hilo muere
					if (self.tiempoDiario > 0) and (self.consumirExcedente == False):
						self.tApagado = threading.Thread(target=self.threadApagado)
						self.tApagado.setDaemon(True)
						self.tApagado.start()
					return True
				else:
					return False
					self.logger.info("FALLO EN EL Encendido")
			else:
				if (self.horaEncendido+self.minTiempoSeguido < t) or (self.emergencia):
					if self.ard.enviaComando('{"command":"setPin","dispositivo":"'+self.nombre+'", "valor":'+E+'}'):							
						if self.encendido != E:		#Evito que dos apagados seguidos quiten tiempo de encendido diario
							self.setTiempoHoy(self.tiempoHoy - t + self.horaEncendido)
							self.encendido = E
						self.emergencia=False
						'''
						runHours = abs(self.tiempoHoy)/3600
						secsRemaining = abs(self.tiempoHoy)%3600
						runMinutes=secsRemaining/60
						secsRemaining%=60
						self.logger.info("Apagado, quedan %dh %d' %d\" hoy"%(runHours,runMinutes,secsRemaining))
						'''
						return True
					else:
						return False
				else:
					return False
			
	def threadDiario(self):
		while not kill_threads:
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

		
	def resetea(self):
		if self.encendido:
			t=int(time.time())
			self.horaEncendido=t
		#self.logger.info("Hora de corte alcanzada, contador reseteado")
	
	def threadApagado(self):
		horaApagado = (self.tiempoHoy+self.horaEncendido) #Si no calculo esto al principio puede sufrir variaciones dentro del while
		tiempoDormido = (self.horaEncendido+self.minTiempoSeguido)
		while self.encendido:
			t=int(time.time())
			if (horaApagado - t <= 0):
				if (tiempoDormido-t>0):
					time.sleep(tiempoDormido-t)
#				self.logger.debug("Tiempo diario terminado, apagando el dispositivo")
				while not self.encenderApagar(False):
					time.sleep(1)
				self.logger.info("Tiempo diario terminado, dispositivo apagado")
			time.sleep(0.2)
#		self.logger.debug("Hilo de apagado terminado");
	
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
	
#Clase enchufe shelly Subclase capacitativo
class shelly(capacitativo):	
	# mosquitto_pub -d -h 192.168.2.105 -p 1883 -t shellyplusplugs-80646fcfa640/rpc -m '{"id":1, "src":"prueva", "method":"Switch.Set","params":{"id":0,"on":false}}'				
	def __init__(self,nombre,power,broker_address,hOn,hOff, consumirE,tiempoAlDia=3600, tiempoMaximo=0, minTiempoSeguidoEnMarcha=10, horaC=12, minPo=20):
		#Creo el atributo nombre para poder crear el logger
		self.nombre=nombre

		#Creo el logger del capacitativo
		self.logger = logging.getLogger(self.nombre)
		self.logger.setLevel(logging.DEBUG)
		fhd = logging.FileHandler('excedentes.log')
		fhd.setLevel(logging.DEBUG)
		self.logger.addHandler(fhd)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fhd.setFormatter(formatter)
		self.logger.addHandler(fhd)
  
		#Creo atributos
		self.encendido = False
		self.horaEncendido = int(time.time())
  
		self.power = power
		self.broker_address = broker_address
		self.pinToGetPower = 1 #Este atributo es para que sea posible pedir el consumo
		self.ard = "shelly"
		self.minPower = power*minPo/100
		self.horasOn = hOn
		self.horasOff = hOff
		self.consumirExcedente = consumirE
		self.tiempoDiario=tiempoAlDia*60
		self.tiempoMaximo=tiempoMaximo*60
		self.minTiempoSeguido = minTiempoSeguidoEnMarcha*60
		self.setTiempoHoy(self.tiempoDiario, True)
		self.horaCorte = horaC * 3600
		self.emergencia = False
		self.online=True	
		self.on_off(False)	#Apago el dispositivo al inicio
		self.modoManual = False 	#Modo manual inactivo
		self.consumoAct=0
	
		#Creo un hilo que reinicia el capacitativo a la hora ...
		self.tDiario = threading.Thread(target=self.threadDiario)
		self.tDiario.setDaemon(True)
		self.tDiario.start()
		
		#Creo un semaforo para maniobrar el capacitativo
		self.semaforoCom = threading.Semaphore(1)
		
	def on_connect(self, client, userdata, flags, rc):
		self.logger.info("Connected with flags [%s] rtn code [%d]"% (flags, rc) )
  
	def on_off(self,E):
		client = mqtt.Client("Solar")
		client.on_connect = self.on_connect
		client.connect(self.broker_address)
		#client.loop_start() #start the loop
		#client.publish("Shellys/"+self.nombre+"/rpc",'{"id":1, "src":"Shellys/'+self.nombre+'/respuestas", "method":"Switch.Set","params":{"id":0,"on":'+str(E).lower()+'}}')
		#client.publish("Shellys/"+self.nombre+"/rpc",'{"id":1, "src":"Shellys/'+self.nombre+'/respuestas", "method":"Switch.Set","params":{"id":0,"on":'+str(E).lower()+'}}')
		topic='Shellys/'+self.nombre+'/rpc'
		mensaje='{"id":1, "src":"Shellys/'+self.nombre+'/respuestas", "method":"Switch.Set","params":{"id":0,"on":'+str(E).lower()+'}}'
		client.publish(topic,mensaje)
		client.disconnect()
		#time.sleep(4) # wait
		#client.loop_stop() #stop the loop
		return(True)
 
	def consumo(self):
		return(self.consumoAct)
  
	def encenderApagar(self,E):
		with self.semaforoCom:	#Activo el semaforo para evitar concurrencias en el apagado
			t=int(time.time())
			if E :
				if self.on_off(E):
					self.encendido = E
					#self.ard.setPinTo(self.pin, E)
					self.horaEncendido=t
					#self.logger.debug("Encendido")
			
					#Si hay limite de ejecucion y no debo consumir excedentes creo un hilo que apagará el dispositivo al llegar la hora, si el dispositivo se apaga antes el hilo muere
					if (self.tiempoDiario > 0) and (self.consumirExcedente == False):
						self.tApagado = threading.Thread(target=self.threadApagado)
						self.tApagado.setDaemon(True)
						self.tApagado.start()
					return True
				else:
					return False
					self.logger.info("FALLO EN EL Encendido")
			else:
				if (self.horaEncendido+self.minTiempoSeguido < t) or (self.emergencia):
					if self.on_off(E):								
						if self.encendido != E:		#Evito que dos apagados seguidos quiten tiempo de encendido diario
							self.setTiempoHoy(self.tiempoHoy - t + self.horaEncendido)
							self.encendido = E
						'''
						self.emergencia=False
						runHours = abs(self.tiempoHoy)/3600
						secsRemaining = abs(self.tiempoHoy)%3600
						runMinutes=secsRemaining/60
						secsRemaining%=60
						self.logger.info("Apagado, quedan %dh %d' %d\" hoy"%(runHours,runMinutes,secsRemaining))
						'''
						return True
					else:
						return False
				else:
					#self.logger.debug("Anulado apagado")
					return False
	
	def nuevaConf(self):
		h=datetime.now().hour*3600+datetime.now().minute*60+datetime.now().second
		dia = datetime.today().weekday() if (h<self.horaCorte) else (datetime.today().weekday() + 1)
		dia = 0 if dia > 6 else dia
		lock = FileLock("excedentes.conf.lock", timeout=10)
		try:
			with lock:
				with open('excedentes.conf') as fileConf:
					conf = json.load(fileConf)
					for s in conf['shellys']:
						if s["nombre"]==self.nombre:
							dias_semana=["lunes","martes","miercoles","jueves","viernes","sabado","domingo"]
							self.horasOn = s["modos"][s['modoDia'][dia]]["timeOn"]
							self.horasOff = s["modos"][s['modoDia'][dia]]["timeOff"]
							self.consumirExcedente = s["modos"][s['modoDia'][dia]]['consumirExcedente']
							self.tiempoDiario = s["modos"][s['modoDia'][dia]]['tiempoAldia'] * 60
							self.minTiempoSeguido = s["modos"][s['modoDia'][dia]]['tiempoSeguido'] *60
							self.tiempoMaximo = s["modos"][s['modoDia'][dia]]["tiempoMaximo"] * 60
							self.setTiempoHoy(self.tiempoDiario)
							self.horaCorte = s["modos"][s['modoDia'][dia]]['horaCorte'] * 3600
							self.on_off(self.encendido) #Dejo el dispositivo como esta pero envio un mensaje para que se ponga en modo automatico
							self.logger.info("Cargada configuracion para el "+dias_semana[dia]+": "+s['modoDia'][dia])
		#except lock.Timeout:
		#	self.logger.error("No es posible bloquear el archivo excedentes.conf.lock")
		except:
			self.logger.error("No es posible cargar la nueva configuracion")
