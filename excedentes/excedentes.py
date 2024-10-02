import json
import logging
from dispositivo import capacitativo
from inversor import fronius



class instalacion:
    def __init__(self):
        self.maxRed = 0
        self.inversor = 0
        self.arduinos = {}
        self.resistivos = []
        self.capacitativos = []
        self.kill_threads = False

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