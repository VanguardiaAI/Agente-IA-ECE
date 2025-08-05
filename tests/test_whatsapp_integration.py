#!/usr/bin/env python3
"""
Tests de integración para WhatsApp Business API con 360Dialog
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime
from typing import Dict, Any, List

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.whatsapp_360dialog_service import whatsapp_service
from services.whatsapp_webhook_handler import whatsapp_webhook_handler
from services.whatsapp_templates import template_manager
from src.agent.hybrid_agent import HybridCustomerAgent
from config.settings import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class WhatsAppIntegrationTester:
    """
    Clase para realizar pruebas de integración de WhatsApp
    """
    
    def __init__(self):
        self.test_phone = None  # Se configurará con número de prueba
        self.results = {
            "total_tests": 0,
            "passed": 0,
            "failed": 0,
            "errors": []
        }
    
    async def initialize(self):
        """Inicializa los servicios necesarios"""
        logger.info("Inicializando servicios para pruebas...")
        
        # Inicializar agente
        self.agent = HybridCustomerAgent()
        await self.agent.initialize()
        
        logger.info("✅ Servicios inicializados")
    
    async def test_configuration(self) -> bool:
        """Prueba la configuración básica"""
        test_name = "Configuration Test"
        self.results["total_tests"] += 1
        
        try:
            logger.info(f"\n🧪 {test_name}")
            
            # Verificar variables de entorno
            checks = {
                "API Key": bool(settings.WHATSAPP_360DIALOG_API_KEY),
                "API URL": bool(settings.WHATSAPP_360DIALOG_API_URL),
                "Phone Number": bool(settings.WHATSAPP_PHONE_NUMBER),
                "Webhook Token": bool(settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN)
            }
            
            all_passed = True
            for check, result in checks.items():
                status = "✅" if result else "❌"
                logger.info(f"  {status} {check}: {'Configured' if result else 'Missing'}")
                if not result:
                    all_passed = False
            
            if all_passed:
                self.results["passed"] += 1
                logger.info(f"✅ {test_name} PASSED")
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name}: Missing configuration")
                logger.error(f"❌ {test_name} FAILED")
            
            return all_passed
            
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    async def test_webhook_verification(self) -> bool:
        """Prueba la verificación del webhook"""
        test_name = "Webhook Verification Test"
        self.results["total_tests"] += 1
        
        try:
            logger.info(f"\n🧪 {test_name}")
            
            # Simular verificación de webhook
            test_mode = "subscribe"
            test_token = settings.WHATSAPP_WEBHOOK_VERIFY_TOKEN
            test_challenge = "test_challenge_123"
            
            result = whatsapp_webhook_handler.verify_webhook(
                mode=test_mode,
                token=test_token,
                challenge=test_challenge
            )
            
            if result == test_challenge:
                self.results["passed"] += 1
                logger.info(f"✅ {test_name} PASSED")
                return True
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name}: Verification failed")
                logger.error(f"❌ {test_name} FAILED")
                return False
                
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    async def test_message_formatting(self) -> bool:
        """Prueba el formateo de mensajes para WhatsApp"""
        test_name = "Message Formatting Test"
        self.results["total_tests"] += 1
        
        try:
            logger.info(f"\n🧪 {test_name}")
            
            # Mensajes de prueba
            test_messages = [
                {
                    "input": "<p>Este es un <strong>mensaje</strong> de prueba</p>",
                    "platform": "whatsapp",
                    "should_contain": ["Este es un", "mensaje", "de prueba"],
                    "should_not_contain": ["<p>", "</p>", "<strong>", "</strong>"]
                },
                {
                    "input": "Mensaje simple sin HTML",
                    "platform": "whatsapp",
                    "should_contain": ["💬", "Mensaje simple sin HTML"]
                }
            ]
            
            all_passed = True
            
            for i, test in enumerate(test_messages, 1):
                # Aplicar formateo
                formatted = self.agent._format_for_platform(
                    test["input"],
                    test["platform"]
                )
                
                logger.info(f"\n  Test {i}:")
                logger.info(f"  Input: {test['input']}")
                logger.info(f"  Output: {formatted}")
                
                # Verificar contenido esperado
                test_passed = True
                
                for expected in test.get("should_contain", []):
                    if expected not in formatted:
                        logger.error(f"    ❌ Missing expected content: '{expected}'")
                        test_passed = False
                        all_passed = False
                
                for unexpected in test.get("should_not_contain", []):
                    if unexpected in formatted:
                        logger.error(f"    ❌ Contains unexpected content: '{unexpected}'")
                        test_passed = False
                        all_passed = False
                
                if test_passed:
                    logger.info(f"    ✅ Test {i} passed")
            
            if all_passed:
                self.results["passed"] += 1
                logger.info(f"\n✅ {test_name} PASSED")
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name}: Formatting issues")
                logger.error(f"\n❌ {test_name} FAILED")
            
            return all_passed
            
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    async def test_webhook_processing(self) -> bool:
        """Prueba el procesamiento de webhooks"""
        test_name = "Webhook Processing Test"
        self.results["total_tests"] += 1
        
        try:
            logger.info(f"\n🧪 {test_name}")
            
            # Webhook de prueba (formato 360Dialog)
            test_webhook = {
                "entry": [{
                    "id": "ENTRY_ID",
                    "changes": [{
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": settings.WHATSAPP_PHONE_NUMBER,
                                "phone_number_id": "PHONE_ID"
                            },
                            "contacts": [{
                                "profile": {
                                    "name": "Test User"
                                },
                                "wa_id": "34612345678"
                            }],
                            "messages": [{
                                "from": "34612345678",
                                "id": "MESSAGE_ID",
                                "timestamp": str(int(datetime.now().timestamp())),
                                "text": {
                                    "body": "Hola, busco información sobre productos"
                                },
                                "type": "text"
                            }]
                        }
                    }]
                }]
            }
            
            # Procesar webhook
            result = await whatsapp_webhook_handler.process_webhook(test_webhook)
            
            if result and result.get("status") == "success":
                self.results["passed"] += 1
                logger.info(f"✅ {test_name} PASSED")
                return True
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name}: Processing failed")
                logger.error(f"❌ {test_name} FAILED")
                return False
                
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    async def test_template_system(self) -> bool:
        """Prueba el sistema de plantillas"""
        test_name = "Template System Test"
        self.results["total_tests"] += 1
        
        try:
            logger.info(f"\n🧪 {test_name}")
            
            # Verificar que las plantillas están configuradas
            templates = {
                "Cart Recovery": settings.WHATSAPP_CART_RECOVERY_TEMPLATE,
                "Order Confirmation": settings.WHATSAPP_ORDER_CONFIRMATION_TEMPLATE,
                "Welcome": settings.WHATSAPP_WELCOME_TEMPLATE
            }
            
            all_configured = True
            for name, template in templates.items():
                if template:
                    logger.info(f"  ✅ {name}: {template}")
                else:
                    logger.error(f"  ❌ {name}: Not configured")
                    all_configured = False
            
            if all_configured:
                self.results["passed"] += 1
                logger.info(f"✅ {test_name} PASSED")
                return True
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name}: Templates not configured")
                logger.error(f"❌ {test_name} FAILED")
                return False
                
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    async def test_agent_integration(self) -> bool:
        """Prueba la integración con el agente de IA"""
        test_name = "Agent Integration Test"
        self.results["total_tests"] += 1
        
        try:
            logger.info(f"\n🧪 {test_name}")
            
            # Simular conversación WhatsApp
            test_conversations = [
                {
                    "message": "Hola",
                    "expected_type": "greeting"
                },
                {
                    "message": "Busco velas aromáticas",
                    "expected_type": "product_search"
                },
                {
                    "message": "¿Cuál es el estado de mi pedido?",
                    "expected_type": "order_inquiry"
                }
            ]
            
            all_passed = True
            
            for i, test in enumerate(test_conversations, 1):
                logger.info(f"\n  Conversación {i}:")
                logger.info(f"  Usuario: {test['message']}")
                
                # Procesar mensaje
                response = await self.agent.process_message(
                    message=test['message'],
                    user_id="test_whatsapp_user",
                    platform="whatsapp"
                )
                
                logger.info(f"  Eva: {response[:100]}{'...' if len(response) > 100 else ''}")
                
                # Verificar respuesta
                if response and len(response) > 0:
                    # Verificar formato WhatsApp (sin HTML)
                    if '<' in response and '>' in response:
                        logger.error(f"    ❌ Response contains HTML tags")
                        all_passed = False
                    else:
                        logger.info(f"    ✅ Valid WhatsApp format")
                else:
                    logger.error(f"    ❌ Empty response")
                    all_passed = False
            
            if all_passed:
                self.results["passed"] += 1
                logger.info(f"\n✅ {test_name} PASSED")
            else:
                self.results["failed"] += 1
                self.results["errors"].append(f"{test_name}: Integration issues")
                logger.error(f"\n❌ {test_name} FAILED")
            
            return all_passed
            
        except Exception as e:
            self.results["failed"] += 1
            self.results["errors"].append(f"{test_name}: {str(e)}")
            logger.error(f"❌ {test_name} ERROR: {e}")
            return False
    
    def print_summary(self):
        """Imprime el resumen de las pruebas"""
        print("\n" + "="*60)
        print("📊 RESUMEN DE PRUEBAS DE INTEGRACIÓN WHATSAPP")
        print("="*60)
        print(f"Total de pruebas: {self.results['total_tests']}")
        print(f"✅ Exitosas: {self.results['passed']}")
        print(f"❌ Fallidas: {self.results['failed']}")
        
        if self.results['errors']:
            print(f"\n❌ Errores encontrados:")
            for error in self.results['errors']:
                print(f"  - {error}")
        
        success_rate = (self.results['passed'] / self.results['total_tests'] * 100) if self.results['total_tests'] > 0 else 0
        print(f"\n📈 Tasa de éxito: {success_rate:.1f}%")
        print("="*60)


async def main():
    """Función principal de pruebas"""
    import argparse
    
    parser = argparse.ArgumentParser(description='WhatsApp Integration Tests')
    parser.add_argument('--test-phone', help='Número de teléfono para pruebas (formato: 34123456789)')
    parser.add_argument('--skip-api-tests', action='store_true', help='Omitir pruebas que requieren API real')
    
    args = parser.parse_args()
    
    # Crear tester
    tester = WhatsAppIntegrationTester()
    
    if args.test_phone:
        tester.test_phone = args.test_phone
    
    # Inicializar
    await tester.initialize()
    
    print("\n🚀 INICIANDO PRUEBAS DE INTEGRACIÓN WHATSAPP")
    print("="*60)
    
    # Ejecutar pruebas
    tests = [
        tester.test_configuration(),
        tester.test_webhook_verification(),
        tester.test_message_formatting(),
        tester.test_webhook_processing(),
        tester.test_template_system(),
        tester.test_agent_integration()
    ]
    
    # Si se especifica skip-api-tests, omitir algunas pruebas
    if not args.skip_api_tests:
        # Aquí irían pruebas que requieren API real
        pass
    
    # Ejecutar todas las pruebas
    for test in tests:
        await test
    
    # Mostrar resumen
    tester.print_summary()
    
    # Retornar código de salida según resultados
    return 0 if tester.results['failed'] == 0 else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)