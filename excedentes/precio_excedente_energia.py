#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Descarga el precio de la energía desde la página de ESIOS.
"""

import os
import time
import traceback
import json
import tempfile
import shutil
import platform
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
try:
    from webdriver_manager.chrome import ChromeDriverManager
except ImportError:
    ChromeDriverManager = None


def _detect_raspberry_pi():
    """Detecta si el código se está ejecutando en una Raspberry Pi"""
    try:
        machine = platform.machine()
        return machine.startswith('arm') and os.path.exists('/proc/device-tree/model')
    except:
        return False


def _get_chrome_driver(download_dir=None, headless=False):
    """Configura y retorna el driver de Chrome apropiado para la plataforma"""
    is_rpi = _detect_raspberry_pi()
    options = Options()
    
    if is_rpi:
        # Configuración específica para Raspberry Pi
        options.binary_location = "/usr/bin/chromium-browser"
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-web-security")
        options.add_argument("--memory-pressure-off")
        options.add_argument("--max_old_space_size=256")
        options.add_argument("--single-process")
    else:
        # Configuración para PC normal
        if headless:
            options.add_argument('--headless=new')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')
    
    # Configuración de descarga
    actual_download_dir = download_dir or '/tmp'
    print(f'DEBUG: download_dir parameter = {download_dir}')
    print(f'DEBUG: actual_download_dir = {actual_download_dir}')
    print(f'DEBUG: type of actual_download_dir = {type(actual_download_dir)}')
    
    prefs = {
        'download.default_directory': actual_download_dir,
        'download.prompt_for_download': False,
        'download.directory_upgrade': True,
        'safebrowsing.enabled': True,
        'profile.default_content_settings.popups': 0,
    }
    print(f'Configurando Chrome prefs con directorio: {actual_download_dir}')
    options.add_experimental_option('prefs', prefs)
    
    try:
        if is_rpi:
            driver = webdriver.Chrome(options=options)
        else:
            if ChromeDriverManager:
                driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
            else:
                driver = webdriver.Chrome(options=options)
    except Exception as e:
        print(f"Error iniciando Chrome: {e}")
        if is_rpi:
            options.add_argument("--remote-debugging-port=9222")
            driver = webdriver.Chrome(options=options)
        else:
            raise
    
    return driver


def download_esios_price_json(url, download_dir=None, headless=False, label=None):
    if download_dir is None:
        download_dir = os.path.join(os.path.dirname(__file__), 'temp_downloads')
    download_dir = os.path.abspath(download_dir)  # Convertir a ruta absoluta
    os.makedirs(download_dir, exist_ok=True)
    print(f'DEBUG: download_esios_price_json - Directorio final: {download_dir}')
    print(f'DEBUG: download_esios_price_json - Existe directorio: {os.path.exists(download_dir)}')
    print(f'DEBUG: download_esios_price_json - Contenido del directorio:')
    for f in os.listdir(download_dir):
        print(f'  - {f}')

    driver = _get_chrome_driver(download_dir=download_dir, headless=headless)
    try:
        # Configurar comportamiento de descarga para RPi
        is_rpi = _detect_raspberry_pi()
        if headless or is_rpi:
            driver.execute_cdp_cmd('Page.setDownloadBehavior', {
                'behavior': 'allow',
                'downloadPath': download_dir,
            })

        print(f'Abriendo {url}')
        driver.get(url)

        wait = WebDriverWait(driver, 40)

        print('Esperando botón de exportación...')
        export_button = wait.until(
            EC.presence_of_element_located((By.ID, 'export_multiple'))
        )
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', export_button)
        driver.execute_script('arguments[0].click();', export_button)

        print('Esperando opción JSON...')
        json_option = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//div[contains(@class, 'options_select')]//div[contains(@class, 'opt-ancle') and normalize-space(text())='JSON']")
            )
        )
        driver.execute_script('arguments[0].scrollIntoView({block: "center"});', json_option)
        driver.execute_script('arguments[0].click();', json_option)

        print('Opción JSON pulsada, esperando descarga...')
        print(f'DEBUG: Antes de descarga - Directorio monitoreado: {download_dir}')
        print(f'DEBUG: Antes de descarga - Archivos existentes:')
        for f in os.listdir(download_dir):
            print(f'  - {f}')
        before_files = set(os.listdir(download_dir))
        timeout = time.time() + 60
        downloaded_file = None
        
        # Para la segunda descarga, ignorar archivos que ya existen
        existing_files = set(os.listdir(download_dir))

        while time.time() < timeout:
            time.sleep(1)
            current_files = set(os.listdir(download_dir))
            # Solo considerar archivos que no existían antes de esta descarga
            truly_new_files = current_files - existing_files
            if truly_new_files:
                for name in truly_new_files:
                    if name.lower().endswith('.json'):
                        downloaded_file = os.path.join(download_dir, name)
                        print(f'DEBUG: Nuevo archivo detectado: {name}')
                        break
                    if name.lower().endswith('.part') or name.lower().endswith('.crdownload'):
                        continue
                if downloaded_file:
                    break

        if downloaded_file is None:
            # Fallback: buscar cualquier json NUEVO tras esperar unos segundos
            print(f'DEBUG: Fallback - buscando archivos nuevos en directorio configurado: {download_dir}')
            for _ in range(5):
                time.sleep(1)
                current_files = set(os.listdir(download_dir))
                new_files = current_files - existing_files
                for name in new_files:
                    if name.lower().endswith('.json'):
                        downloaded_file = os.path.join(download_dir, name)
                        print(f'DEBUG: Fallback - nuevo archivo encontrado: {downloaded_file}')
                        break
                if downloaded_file:
                    break
            
            # Si todavía no se encuentra, buscar en el directorio de trabajo actual
            if downloaded_file is None:
                current_dir = os.getcwd()
                print(f'DEBUG: Fallback - buscando en directorio de trabajo actual: {current_dir}')
                for name in os.listdir(current_dir):
                    if name.lower().endswith('.json'):
                        downloaded_file = os.path.join(current_dir, name)
                        print(f'DEBUG: Fallback - encontrado en directorio de trabajo: {downloaded_file}')
                        break

        if downloaded_file is None:
            # Búsqueda extendida para RPi
            print('Buscando archivos JSON descargados...')
            for _ in range(10):  # 10 intentos más
                time.sleep(2)
                for name in os.listdir(download_dir):
                    if name.lower().endswith('.json'):
                        downloaded_file = os.path.join(download_dir, name)
                        print(f'Archivo encontrado en búsqueda extendida: {downloaded_file}')
                        break
                if downloaded_file:
                    break

        if downloaded_file:
            if label:
                base_name = os.path.basename(downloaded_file)
                labeled_name = f"{label}_{base_name}"
                labeled_path = os.path.join(download_dir, labeled_name)
                if not os.path.exists(labeled_path):
                    print(f'DEBUG: Renombrando {downloaded_file} -> {labeled_path}')
                    os.rename(downloaded_file, labeled_path)
                    downloaded_file = labeled_path
            print(f'Descarga completada: {downloaded_file}')
            return downloaded_file

        raise RuntimeError(f'No se detectó ningún archivo JSON descargado en {download_dir}.')

    except Exception:
        print(f'Error durante la descarga de ESIOS para {url}:')
        traceback.print_exc()
        return None

    finally:
        driver.quit()


def load_json_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def extract_venta_prices(data):
    if isinstance(data, dict):
        raise ValueError('Formato inesperado para datos de venta: dict no soportado directamente')

    if not isinstance(data, list):
        raise ValueError('Formato inesperado para datos de venta: no es lista')

    prices = []
    for item in data:
        if isinstance(item, dict):
            if 'values' in item:
                prices.append(float(item['values']))
            elif 'value' in item:
                prices.append(float(item['value']))
            elif 'precio' in item:
                prices.append(float(item['precio']))
            else:
                raise ValueError('Elemento de venta sin campo de valor reconocible')
        else:
            prices.append(float(item))
    return prices


def extract_compra_prices(data, geoname='Baleares'):
    if isinstance(data, dict) and 'data' in data and isinstance(data['data'], list):
        data = data['data']

    if not isinstance(data, list):
        raise ValueError('Formato inesperado para datos de compra: no es lista')

    # Agrupar por geoname
    zones = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        name = item.get('geoname') or item.get('geoName') or item.get('name')
        if not name:
            continue
        zones.setdefault(name.strip().lower(), []).append(item)

    target = geoname.strip().lower()
    if target not in zones:
        raise ValueError(f'Zona geográfica "{geoname}" no encontrada en datos de compra')

    zone_items = zones[target]
    zone_items.sort(key=lambda x: x.get('datetime') or '')

    prices = []
    for item in zone_items:
        if 'values' in item:
            prices.append(float(item['values']))
        elif 'value' in item:
            prices.append(float(item['value']))
        elif 'precio' in item:
            prices.append(float(item['precio']))
        else:
            raise ValueError('Elemento de compra sin campo de valor reconocible')
    return prices

    raise ValueError(f'Zona geográfica "{geoname}" no encontrada en datos de compra')


def download_esios_prices(download_dir=None, headless=False):
    # Usar un directorio persistente si no se especifica uno para evitar problemas con RPi
    if download_dir is None:
        download_dir = os.path.join(os.path.dirname(__file__), 'temp_downloads')
        download_dir = os.path.abspath(download_dir)
        os.makedirs(download_dir, exist_ok=True)
        cleanup_temp = False
    else:
        download_dir = os.path.abspath(download_dir)
        cleanup_temp = False
        
    results = {}
    results['venta'] = download_esios_price_json(
        'https://www.esios.ree.es/es/analisis/1739',
        download_dir=download_dir,
        headless=headless,
        label='venta'
    )
    results['compra'] = download_esios_price_json(
        'https://www.esios.ree.es/es/analisis/1001',
        download_dir=download_dir,
        headless=headless,
        label='compra'
    )
    return results


def download_and_load_prices(download_dir=None, headless=False, geoname='Baleares'):
    # Usar un directorio persistente si no se especifica uno para evitar problemas con RPi
    if download_dir is None:
        download_dir = os.path.join(os.path.dirname(__file__), 'temp_downloads')
        download_dir = os.path.abspath(download_dir)
        os.makedirs(download_dir, exist_ok=True)
        cleanup_temp = False
    else:
        download_dir = os.path.abspath(download_dir)
        cleanup_temp = False
    
    try:
        files = download_esios_prices(download_dir=download_dir, headless=headless)
        if not files['venta'] or not files['compra']:
            raise RuntimeError('No se descargaron ambos archivos correctamente')

        print(f'Intentando cargar archivos: venta={files["venta"]}, compra={files["compra"]}')
        
        # Intentar cargar archivos con reintentos para manejar problemas de acceso temporal
        max_retries = 3
        venta_data = None
        compra_data = None
        
        for attempt in range(max_retries):
            try:
                if not os.path.exists(files['venta']):
                    raise FileNotFoundError(f'Archivo de venta no encontrado: {files["venta"]}')
                if not os.path.exists(files['compra']):
                    raise FileNotFoundError(f'Archivo de compra no encontrado: {files["compra"]}')

                venta_data = load_json_file(files['venta'])
                compra_data = load_json_file(files['compra'])
                break  # Éxito, salir del loop de reintentos
            except (FileNotFoundError, json.JSONDecodeError) as e:
                if attempt == max_retries - 1:
                    raise  # Último intento, propagar el error
                print(f'Intento {attempt + 1} fallido, reintentando en 2 segundos...')
                time.sleep(2)

        venta_prices = extract_venta_prices(venta_data)
        compra_prices = extract_compra_prices(compra_data, geoname=geoname)

        return {
            'venta': venta_prices,
            'compra': compra_prices,
        }
    finally:
        # Eliminar el directorio temporal y sus archivos
        if cleanup_temp:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == '__main__':
    result = download_and_load_prices(headless=False, geoname='Baleares')
    print('Descargas OK')
    print('Venta precios:', result['venta'])
    print('Compra precios Baleares:', result['compra'])
