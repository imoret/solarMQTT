import logging
import requests
import time
import platform
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException, TimeoutException
try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None

class fronius:	
	def __init__(self, nombre, _ip, web_username="service", web_password="yourPassword!", web_headless=False, potencia_instalada=4800):
		self.excedente=0
		self.produccion=0
		self.autoconsumo=0
		self.consumo=0
		self.nombre=nombre
		self.ip = _ip
		self.url = "http://"+self.ip+"/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
		self.online = True

		# Atributos para autenticación web
		self.web_username = web_username
		self.web_password = web_password
		self.web_headless = web_headless
		self.potencia_instalada = potencia_instalada

		#Creo el logger del fronius
		self.logger = logging.getLogger(self.nombre)
		self.logger.setLevel(logging.DEBUG)
		fhd = logging.FileHandler('excedentes.log')
		fhd.setLevel(logging.DEBUG)
		self.logger.addHandler(fhd)
		formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
		fhd.setFormatter(formatter)
		self.logger.addHandler(fhd)

		# Estado de la inyección dinámica
		self.is_raspberry_pi = self._detect_raspberry_pi()
		self.disable_dynamic_power_injection()  # Intentamos desactivar la inyeccion dinamica al iniciar para asegurar estado conocido
		self.dynamic_injection_active = False

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
					self.autoconsumo=self.produccion if self.excedente > 0 else self.produccion + self.excedente
					self.consumo=self.produccion + self.excedente if self.excedente > 0 else self.produccion + self.excedente
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
	
	def getStatus(self):
		self.update()
		return(self.online)
	
	def getDatos(self):
		self.update()
		return(self.produccion,self.excedente,self.autoconsumo,self.consumo)

	def _detect_raspberry_pi(self):
		"""Detecta si el código se está ejecutando en una Raspberry Pi"""
		try:
			machine = platform.machine()
			return machine.startswith('arm') and os.path.exists('/proc/device-tree/model')
		except:
			return False

	def _get_chrome_driver(self):
		"""Configura y retorna el driver de Chrome apropiado para la plataforma"""
		chrome_options = Options()
		
		if self.is_raspberry_pi:
			# Configuración específica para Raspberry Pi
			chrome_options.binary_location = "/usr/bin/chromium-browser"
			chrome_options.add_argument("--headless")
			chrome_options.add_argument("--no-sandbox")
			chrome_options.add_argument("--disable-dev-shm-usage")
			chrome_options.add_argument("--disable-gpu")
			chrome_options.add_argument("--disable-extensions")
			chrome_options.add_argument("--disable-web-security")
			chrome_options.add_argument("--memory-pressure-off")
			chrome_options.add_argument("--max_old_space_size=256")
			chrome_options.add_argument("--single-process")
			
			try:
				driver = webdriver.Chrome(options=chrome_options, command_executor=None)
			except Exception as e:
				self.logger.error(f"Error iniciando Chromium en RPi: {e}")
				# Intentar con configuración mínima
				chrome_options = Options()
				chrome_options.binary_location = "/usr/bin/chromium-browser"
				chrome_options.add_argument("--headless")
				chrome_options.add_argument("--no-sandbox")
				chrome_options.add_argument("--disable-dev-shm-usage")
				driver = webdriver.Chrome(options=chrome_options)
		else:
			# Configuración para PC normal
			if self.web_headless:
				chrome_options.add_argument("--headless")
			chrome_options.add_argument("--no-sandbox")
			chrome_options.add_argument("--disable-dev-shm-usage")
			
			try:
				if ChromeDriverManager:
					driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
				else:
					driver = webdriver.Chrome(options=chrome_options)
			except Exception:
				# Fallback sin Service
				driver = webdriver.Chrome(options=chrome_options)
		
		return driver

	def disable_dynamic_power_injection(self):
		"""
		Desactiva la reducción dinámica de potencia (EVU) en el inversor Fronius.
		Utiliza los atributos self.web_username, self.web_password y self.web_headless.
		
		Returns:
			bool: True si se desactivó correctamente, False si hubo error
		"""
		try:
			# Inicializar driver con configuración automática
			driver = self._get_chrome_driver()
			wait = WebDriverWait(driver, 20)

			def wait_until_clickable(locator):
				while True:
					try:
						return wait.until(EC.element_to_be_clickable(locator))
					except StaleElementReferenceException:
						continue

			# Navegar a login
			LOGIN_URL = f"http://{self.ip}/#/settings"
			self.logger.info("Iniciando login en interfaz web del inversor")
			driver.get(LOGIN_URL)

			user_select_element = wait_until_clickable((By.CSS_SELECTOR, "select[ng-model='username']"))
			user_select = Select(user_select_element)
			user_select.select_by_visible_text(self.web_username)

			password_field = wait_until_clickable((By.NAME, "password"))
			password_field.clear()
			password_field.send_keys(self.web_password)

			login_button = wait_until_clickable((By.CSS_SELECTOR, "button[ng-click='loginLogoutClick()']"))
			login_button.click()

			try:
				wait.until(EC.url_changes(LOGIN_URL))
			except TimeoutException:
				wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "button[ng-click='loginLogoutClick()']")))

			if driver.current_url == LOGIN_URL:
				self.logger.error("Error en el login: no se pudo acceder a la interfaz web")
				driver.quit()
				return False

			self.logger.info("Login exitoso, configurando reducción dinámica de potencia")

			# Navegar a configuración
			evu_link = wait_until_clickable((By.CSS_SELECTOR, "a[ui-sref='settings.evu'], a[href*='#/settings/evu']"))
			evu_link.click()
			wait.until(EC.url_contains("#/settings/evu"))
			time.sleep(5)

			# Desactivar reducción
			off_radio = wait_until_clickable((By.XPATH, "//label[input[@type='radio' and @ng-model='model.powerLimits.exportLimits.activePower.mode' and @value='off']]"))
			off_radio.click()
			time.sleep(3)

			# Guardar
			save_button = wait_until_clickable((By.CSS_SELECTOR, "#ICSConfigTitlebar button.OK[ng-click='save();']"))
			driver.execute_script("arguments[0].click();", save_button)
			time.sleep(3)

			self.logger.info("Reducción dinámica de potencia desactivada correctamente")
			self.dynamic_injection_active = False
			driver.quit()
			return True

		except Exception as e:
			self.logger.error(f"Error al desactivar EVU: {str(e)}")
			try:
				driver.quit()
			except:
				pass
			return False

	def enable_dynamic_power_injection(self, soft_limit_power=250):
		"""
		Activa la inyección dinámica de potencia en el inversor Fronius.
		Configura el modo "Limit Entire System" con wattPeakReferenceValue=self.potencia_instalada,
		habilita soft limit con powerLimit=soft_limit_power W.
		Utiliza los atributos self.web_username, self.web_password y self.web_headless.
		
		Args:
			soft_limit_power (int): Potencia límite del soft limit en watts. Default: 250
		
		Returns:
			bool: True si se activó correctamente, False si hubo error
		"""
		try:
			# Inicializar driver con configuración automática
			driver = self._get_chrome_driver()
			wait = WebDriverWait(driver, 20)

			def wait_until_clickable(locator):
				while True:
					try:
						return wait.until(EC.element_to_be_clickable(locator))
					except StaleElementReferenceException:
						continue

			# Navegar a login
			LOGIN_URL = f"http://{self.ip}/#/settings"
			self.logger.info("Iniciando login en interfaz web del inversor")
			driver.get(LOGIN_URL)

			user_select_element = wait_until_clickable((By.CSS_SELECTOR, "select[ng-model='username']"))
			user_select = Select(user_select_element)
			user_select.select_by_visible_text(self.web_username)

			password_field = wait_until_clickable((By.NAME, "password"))
			password_field.clear()
			password_field.send_keys(self.web_password)

			login_button = wait_until_clickable((By.CSS_SELECTOR, "button[ng-click='loginLogoutClick()']"))
			login_button.click()

			try:
				wait.until(EC.url_changes(LOGIN_URL))
			except TimeoutException:
				wait.until(EC.invisibility_of_element_located((By.CSS_SELECTOR, "button[ng-click='loginLogoutClick()']")))

			if driver.current_url == LOGIN_URL:
				self.logger.error("Error en el login: no se pudo acceder a la interfaz web")
				driver.quit()
				return False

			self.logger.info("Login exitoso, configurando inyección dinámica de potencia")

			# Navegar a configuración
			evu_link = wait_until_clickable((By.CSS_SELECTOR, "a[ui-sref='settings.evu'], a[href*='#/settings/evu']"))
			evu_link.click()
			wait.until(EC.url_contains("#/settings/evu"))
			time.sleep(5)

			# Activar inyección dinámica
			entire_system_radio = wait_until_clickable((By.XPATH, "//label[input[@type='radio' and @ng-model='model.powerLimits.exportLimits.activePower.mode' and @value='entireSystem']]"))
			entire_system_radio.click()
			time.sleep(10)

			# Configurar parámetros
			watt_peak_input = wait_until_clickable((By.ID, "wattPeakReferenceValue"))
			watt_peak_input.clear()
			watt_peak_input.send_keys(str(self.potencia_instalada))
			time.sleep(5)

			soft_limit_checkbox = wait_until_clickable((By.XPATH, "//enable[@ng-model='model.powerLimits.exportLimits.activePower.softLimit.enabled']//input[@type='checkbox']"))
			if not soft_limit_checkbox.is_selected():
				soft_limit_checkbox.click()

			soft_limit_input = wait_until_clickable((By.CSS_SELECTOR, "input[ng-model='model.powerLimits.exportLimits.activePower.softLimit.powerLimit']"))
			soft_limit_input.clear()
			soft_limit_input.send_keys(str(soft_limit_power))

			unit_select_element = wait_until_clickable((By.XPATH, "//select[option[@value='absolute']]"))
			unit_select = Select(unit_select_element)
			unit_select.select_by_value("absolute")

			# Guardar
			save_button = wait_until_clickable((By.CSS_SELECTOR, "#ICSConfigTitlebar button.OK[ng-click='save();']"))
			driver.execute_script("arguments[0].click();", save_button)
			time.sleep(5)

			self.logger.info("Inyección dinámica de potencia activada correctamente")
			self.dynamic_injection_active = True
			driver.quit()
			return True

		except Exception as e:
			self.logger.error(f"Error al activar inyección dinámica: {str(e)}")
			try:
				driver.quit()
			except:
				pass
			return False
