#!/usr/bin/env python3
"""
Script para diagnosticar errores 404 en el widget
"""

import requests
import json
from colorama import init, Fore, Style

init()

def test_endpoint(url, method='GET', data=None, headers=None):
    """Prueba un endpoint y reporta el resultado"""
    try:
        if method == 'GET':
            response = requests.get(url, headers=headers)
        else:
            response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            print(f"{Fore.GREEN}✓ {url} - OK (200){Style.RESET_ALL}")
            return True
        elif response.status_code == 404:
            print(f"{Fore.RED}✗ {url} - NOT FOUND (404){Style.RESET_ALL}")
            return False
        else:
            print(f"{Fore.YELLOW}? {url} - Status: {response.status_code}{Style.RESET_ALL}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"{Fore.RED}✗ {url} - CONNECTION ERROR (¿Servidor apagado?){Style.RESET_ALL}")
        return False
    except Exception as e:
        print(f"{Fore.RED}✗ {url} - ERROR: {e}{Style.RESET_ALL}")
        return False

def main():
    print(f"\n{Fore.CYAN}=== Diagnóstico de errores 404 en Eva Widget ==={Style.RESET_ALL}\n")
    
    base_url = "http://localhost:8080"
    
    # 1. Verificar servidor principal
    print(f"{Fore.YELLOW}1. Verificando servidor principal:{Style.RESET_ALL}")
    server_ok = test_endpoint(f"{base_url}/")
    
    # 2. Verificar endpoints críticos
    print(f"\n{Fore.YELLOW}2. Verificando endpoints críticos:{Style.RESET_ALL}")
    test_endpoint(f"{base_url}/health")
    test_endpoint(f"{base_url}/api/chat", method='POST', 
                  data={"message": "test", "user_id": "test", "platform": "wordpress"},
                  headers={"Content-Type": "application/json", "X-Platform": "wordpress"})
    
    # 3. Verificar archivos estáticos (si el servidor los sirve)
    print(f"\n{Fore.YELLOW}3. Verificando archivos estáticos:{Style.RESET_ALL}")
    test_endpoint(f"{base_url}/static/css/style.css")
    test_endpoint(f"{base_url}/static/js/script.js")
    
    # 4. Verificar MCP endpoints
    print(f"\n{Fore.YELLOW}4. Verificando endpoints MCP:{Style.RESET_ALL}")
    test_endpoint("http://localhost:8000/health")
    test_endpoint("http://localhost:8000/mcp")
    
    # 5. Sugerencias
    print(f"\n{Fore.CYAN}=== Sugerencias ==={Style.RESET_ALL}")
    
    if not server_ok:
        print(f"{Fore.YELLOW}• El servidor parece estar apagado. Ejecuta:{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}python app.py{Style.RESET_ALL}")
        print(f"  {Fore.GREEN}python main.py{Style.RESET_ALL} (en otra terminal)")
    else:
        print(f"{Fore.YELLOW}• Verifica la configuración del widget en WordPress:{Style.RESET_ALL}")
        print(f"  - Ve a Eva Chatbot > Configuración")
        print(f"  - Asegúrate de que la URL del servidor sea: {base_url}")
        print(f"  - Prueba la conexión con el botón 'Probar Conexión'")
    
    print(f"\n{Fore.YELLOW}• Para ver más detalles del error 404:{Style.RESET_ALL}")
    print(f"  1. Abre las herramientas de desarrollador (F12)")
    print(f"  2. Ve a la pestaña 'Network' (Red)")
    print(f"  3. Recarga la página")
    print(f"  4. Busca las peticiones con status 404 (en rojo)")
    print(f"  5. Haz clic en ellas para ver la URL completa")

if __name__ == "__main__":
    main()