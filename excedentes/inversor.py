import logging
import requests
import time

class fronius:	
	def __init__(self,nombre,_ip):
		self.excedente=0
		self.produccion=0
		self.nombre=nombre
		self.ip = _ip
		self.url = "http://"+self.ip+"/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
		self.online = True

		#Creo el logger del fronius
		self.logger = logging.getLogger(self.nombre)
		self.logger.setLevel(logging.DEBUG)
		fhd = logging.FileHandler('excedentes.log')
		fhd.setLevel(logging.DEBUG)
		self.logger.addHandler(fhd)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fhd.setFormatter(formatter)
		self.logger.addHandler(fhd)

	def update(self):
		intento = 1
		exito = False
		while (intento<3 and not exito):
			try:
				self.request = requests.get(self.url, timeout=10)
				exito = True
			except:
				intento+=1
				time.sleep(10)
			else:
				if not self.online:
					self.logger.info("Inversor vuelve a funcionar")
					self.online = True 
				try:
					self.Json=self.request.json()
				except:
					self.logger.error("Error al convertir JSON")
				else:
					self.produccion=self.Json["Body"]["Data"]["Inverters"]["1"]["P"]
					self.excedente=self.Json["Body"]["Data"]["Site"]["P_Grid"]
					#self.produccion = 2600
					#self.excedente = 2591
					#self.logger.info("Produccion: %s excedente: %s" %(self.produccion, self.excedente))
		
		if (intento >= 3 and not self.online):
			self.logger.error("Inversor fuera de servicio o inalcanzable")
			self.online = False
			
			#self.excedente=-3000
			#self.excedente=-500
			#self.excedente=15000
			#self.produccion=0
		
	def getProduccion(self):
		self.update()
		return(self.produccion)
		
	def getExcedente(self):
		self.update()
		return(self.excedente)
