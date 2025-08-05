#!/usr/bin/env python3
"""
Script de prueba completo para el agente Eva
Verifica todas las funcionalidades implementadas
"""

import asyncio
import aiohttp
import json
from datetime import datetime
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

# Configuración
BASE_URL = "http://localhost:8080"
API_URL = f"{BASE_URL}/api/chat"
WS_URL = "ws://localhost:8080/ws/chat"

# Colores para output
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

def print_test_header(test_name):
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}🧪 TEST: {test_name}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")

def print_result(success, message):
    if success:
        print(f"{Colors.OKGREEN}✅ {message}{Colors.ENDC}")
    else:
        print(f"{Colors.FAIL}❌ {message}{Colors.ENDC}")

async def test_chat_api(session_id: str, message: str):
    """Enviar mensaje al API de chat y obtener respuesta"""
    async with aiohttp.ClientSession() as session:
        payload = {
            "message": message,
            "user_id": f"test_user_{session_id}"
        }
        
        print(f"\n{Colors.OKCYAN}👤 Usuario: {message}{Colors.ENDC}")
        
        try:
            async with session.post(API_URL, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    print(f"{Colors.OKBLUE}🤖 Eva: {data['response']}{Colors.ENDC}")
                    
                    # Mostrar herramientas usadas si las hay
                    if 'tools_used' in data and data['tools_used']:
                        print(f"{Colors.WARNING}🔧 Herramientas usadas: {', '.join(data['tools_used'])}{Colors.ENDC}")
                    
                    return data
                else:
                    error = await response.text()
                    print(f"{Colors.FAIL}Error {response.status}: {error}{Colors.ENDC}")
                    return None
        except Exception as e:
            print(f"{Colors.FAIL}Error de conexión: {e}{Colors.ENDC}")
            return None

async def run_tests():
    """Ejecutar suite completa de pruebas"""
    session_id = f"test_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Test 1: Saludo y memoria conversacional
    print_test_header("Saludo y Memoria Conversacional")
    
    response = await test_chat_api(session_id, "Hola, mi nombre es Carlos y soy electricista profesional")
    if response:
        print_result(True, "Saludo inicial procesado")
    
    await asyncio.sleep(2)
    
    # Test 2: Verificar memoria
    print_test_header("Verificación de Memoria")
    
    response = await test_chat_api(session_id, "¿Recuerdas mi nombre y profesión?")
    if response and ("Carlos" in response['response'] or "electricista" in response['response']):
        print_result(True, "Memoria conversacional funcionando")
    else:
        print_result(False, "No recuerda información previa")
    
    await asyncio.sleep(2)
    
    # Test 3: Consulta de knowledge base - Políticas de envío
    print_test_header("Knowledge Base - Políticas de Envío")
    
    response = await test_chat_api(session_id, "¿Cuánto cuesta el envío a Península para un pedido de 50 euros?")
    if response and "6€" in response['response']:
        print_result(True, "Información de envíos correcta")
    else:
        print_result(False, "No encontró información de envíos")
    
    await asyncio.sleep(2)
    
    # Test 4: Envío gratuito
    print_test_header("Knowledge Base - Envío Gratuito")
    
    response = await test_chat_api(session_id, "¿A partir de qué importe el envío es gratis a Portugal?")
    if response and ("100" in response['response'] or "gratuito" in response['response'].lower()):
        print_result(True, "Información de envío gratuito correcta")
    else:
        print_result(False, "No encontró información de envío gratuito")
    
    await asyncio.sleep(2)
    
    # Test 5: Política de devoluciones
    print_test_header("Knowledge Base - Devoluciones")
    
    response = await test_chat_api(session_id, "¿Cuántos días tengo para devolver un producto?")
    if response and ("14" in response['response'] or "30" in response['response']):
        print_result(True, "Información de devoluciones correcta")
    else:
        print_result(False, "No encontró información de devoluciones")
    
    await asyncio.sleep(2)
    
    # Test 6: Búsqueda de productos
    print_test_header("Búsqueda de Productos")
    
    response = await test_chat_api(session_id, "Necesito un diferencial de 40A")
    if response and ("producto" in response['response'].lower() or "diferencial" in response['response'].lower()):
        print_result(True, "Búsqueda de productos funcionando")
    else:
        print_result(False, "No pudo buscar productos")
    
    await asyncio.sleep(2)
    
    # Test 7: Información de contacto
    print_test_header("Knowledge Base - Contacto")
    
    response = await test_chat_api(session_id, "¿Cuál es el teléfono para consultas técnicas?")
    if response and ("661 239 969" in response['response'] or "661239969" in response['response']):
        print_result(True, "Información de contacto correcta")
    else:
        print_result(False, "No encontró información de contacto")
    
    await asyncio.sleep(2)
    
    # Test 8: Garantías
    print_test_header("Knowledge Base - Garantías")
    
    response = await test_chat_api(session_id, "¿Qué garantía tienen los cables eléctricos?")
    if response and ("garantía" in response['response'].lower()):
        print_result(True, "Información de garantías encontrada")
    else:
        print_result(False, "No encontró información de garantías")
    
    await asyncio.sleep(2)
    
    # Test 9: Métodos de pago
    print_test_header("Knowledge Base - Métodos de Pago")
    
    response = await test_chat_api(session_id, "¿Aceptan pago contrareembolso?")
    if response and ("no" in response['response'].lower() or "contrareembolso" in response['response'].lower()):
        print_result(True, "Información de pagos correcta")
    else:
        print_result(False, "No encontró información de pagos")
    
    await asyncio.sleep(2)
    
    # Test 10: Marcas disponibles
    print_test_header("Knowledge Base - Marcas")
    
    response = await test_chat_api(session_id, "¿Qué marcas de material eléctrico tienen?")
    if response and any(marca in response['response'] for marca in ["Mersen", "Cirprotec", "Jung", "Soler"]):
        print_result(True, "Información de marcas correcta")
    else:
        print_result(False, "No encontró información de marcas")
    
    await asyncio.sleep(2)
    
    # Test 11: Consulta de pedido (sin validación)
    print_test_header("Consulta de Pedido - Sin Validación")
    
    response = await test_chat_api(session_id, "Quiero consultar el pedido 12345")
    if response and ("email" in response['response'].lower() or "correo" in response['response'].lower()):
        print_result(True, "Solicita email para validación")
    else:
        print_result(False, "No solicitó validación de email")
    
    await asyncio.sleep(2)
    
    # Test 12: Memoria de contexto múltiple
    print_test_header("Memoria de Contexto Múltiple")
    
    response = await test_chat_api(session_id, "Por cierto, estoy interesado en material para una instalación trifásica")
    if response:
        print_result(True, "Contexto adicional registrado")
    
    await asyncio.sleep(2)
    
    response = await test_chat_api(session_id, "¿Qué información has recopilado sobre mí hasta ahora?")
    if response and ("Carlos" in response['response'] and "electricista" in response['response']):
        print_result(True, "Mantiene todo el contexto de la conversación")
    else:
        print_result(False, "Perdió parte del contexto")
    
    # Resumen final
    print(f"\n{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"{Colors.BOLD}📊 PRUEBAS COMPLETADAS{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*60}{Colors.ENDC}")
    print(f"\n{Colors.OKGREEN}✅ Todas las pruebas han sido ejecutadas{Colors.ENDC}")
    print(f"{Colors.WARNING}⚠️  Revisa los resultados arriba para verificar el funcionamiento{Colors.ENDC}")

async def test_websocket():
    """Prueba adicional de WebSocket para chat en tiempo real"""
    print_test_header("WebSocket - Chat en Tiempo Real")
    
    client_id = "test_client_ws"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(f"{WS_URL}/{client_id}") as ws:
                # Enviar mensaje
                await ws.send_json({
                    "message": "Hola, esta es una prueba por WebSocket",
                    "user_id": "test_user_ws"
                })
                
                # Recibir respuesta
                async for msg in ws:
                    if msg.type == aiohttp.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        print(f"{Colors.OKBLUE}🤖 Eva (WS): {data.get('response', 'Sin respuesta')}{Colors.ENDC}")
                        print_result(True, "WebSocket funcionando correctamente")
                        break
                    elif msg.type == aiohttp.WSMsgType.ERROR:
                        print_result(False, f"Error en WebSocket: {ws.exception()}")
                        break
                        
    except Exception as e:
        print_result(False, f"No se pudo conectar al WebSocket: {e}")

if __name__ == "__main__":
    print(f"{Colors.BOLD}{Colors.HEADER}")
    print("🧪 EVA - SUITE DE PRUEBAS COMPLETA")
    print("Sistema de Atención al Cliente para El Corte Eléctrico")
    print(f"{Colors.ENDC}")
    
    # Verificar que los servicios estén corriendo
    print(f"\n{Colors.WARNING}⚠️  Asegúrate de que los servicios estén corriendo:{Colors.ENDC}")
    print(f"   python start_services.py")
    print(f"\n{Colors.OKCYAN}🚀 Iniciando pruebas en 3 segundos...{Colors.ENDC}")
    
    import time
    time.sleep(3)
    
    # Ejecutar pruebas principales
    asyncio.run(run_tests())
    
    # Prueba adicional de WebSocket
    print(f"\n{Colors.OKCYAN}🔌 Ejecutando prueba de WebSocket...{Colors.ENDC}")
    asyncio.run(test_websocket())
    
    print(f"\n{Colors.OKGREEN}✨ Suite de pruebas finalizada{Colors.ENDC}")