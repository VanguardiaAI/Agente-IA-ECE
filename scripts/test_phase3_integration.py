#!/usr/bin/env python3
"""
Script de Prueba Integral - Fase 3
Valida la integración completa del agente híbrido con búsqueda híbrida
"""

import asyncio
import sys
import os
import json
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent
from services.database import db_service
from services.embedding_service import embedding_service

class Phase3IntegrationTest:
    """Pruebas integrales para la Fase 3"""
    
    def __init__(self):
        self.agent = None
        self.test_results = []
        self.start_time = datetime.now()
        
    async def run_all_tests(self):
        """Ejecutar todas las pruebas"""
        print("🚀 INICIANDO PRUEBAS INTEGRALES - FASE 3")
        print("=" * 60)
        print(f"⏰ Hora de inicio: {self.start_time}")
        print("=" * 60)
        
        tests = [
            ("Inicialización de Servicios", self.test_service_initialization),
            ("Búsqueda Híbrida Directa", self.test_hybrid_search),
            ("Inicialización del Agente", self.test_agent_initialization),
            ("Procesamiento de Mensajes", self.test_message_processing),
            ("Estrategias Adaptativas", self.test_adaptive_strategies),
            ("Integración con Base de Datos", self.test_database_integration),
            ("Manejo de Errores", self.test_error_handling),
            ("Rendimiento del Sistema", self.test_performance),
        ]
        
        for test_name, test_func in tests:
            await self.run_test(test_name, test_func)
        
        await self.generate_report()
    
    async def run_test(self, test_name: str, test_func):
        """Ejecutar una prueba individual"""
        print(f"\n🧪 Ejecutando: {test_name}")
        print("-" * 40)
        
        try:
            start_time = datetime.now()
            result = await test_func()
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            self.test_results.append({
                "name": test_name,
                "status": "PASSED" if result else "FAILED",
                "duration": duration,
                "timestamp": start_time.isoformat()
            })
            
            status_icon = "✅" if result else "❌"
            print(f"{status_icon} {test_name}: {'PASSED' if result else 'FAILED'} ({duration:.2f}s)")
            
        except Exception as e:
            self.test_results.append({
                "name": test_name,
                "status": "ERROR",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            })
            print(f"💥 {test_name}: ERROR - {str(e)}")
    
    async def test_service_initialization(self) -> bool:
        """Prueba: Inicialización de servicios base"""
        try:
            # Verificar base de datos
            if not db_service.initialized:
                await db_service.initialize()
            
            stats = await db_service.get_statistics()
            print(f"   📊 Base de datos: {stats.get('total_products', 0)} productos")
            
            # Verificar embeddings
            if not embedding_service.initialized:
                await embedding_service.initialize()
            
            print(f"   🧠 Servicio de embeddings: Inicializado")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error en inicialización: {e}")
            return False
    
    async def test_hybrid_search(self) -> bool:
        """Prueba: Búsqueda híbrida directa"""
        try:
            # Prueba de búsqueda semántica
            query = "iluminación LED exterior"
            embedding = await embedding_service.generate_embedding(query)
            
            results = await db_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                content_types=["product"],
                limit=5
            )
            
            print(f"   🔍 Búsqueda '{query}': {len(results)} resultados")
            
            if results:
                best_match = results[0]
                print(f"   🎯 Mejor resultado: {best_match.get('title', 'N/A')} (score: {best_match.get('rrf_score', 0):.3f})")
            
            return len(results) > 0
            
        except Exception as e:
            print(f"   ❌ Error en búsqueda híbrida: {e}")
            return False
    
    async def test_agent_initialization(self) -> bool:
        """Prueba: Inicialización del agente híbrido"""
        try:
            self.agent = HybridCustomerAgent()
            await self.agent.initialize()
            
            print(f"   🤖 Agente inicializado correctamente")
            print(f"   🔧 Multi-agente habilitado: {self.agent.enable_multi_agent}")
            print(f"   🧠 Routing inteligente: {self.agent.enable_smart_routing}")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Error inicializando agente: {e}")
            return False
    
    async def test_message_processing(self) -> bool:
        """Prueba: Procesamiento básico de mensajes"""
        if not self.agent:
            print("   ⚠️ Agente no inicializado")
            return False
        
        try:
            test_messages = [
                "Hola, soy María",
                "Busco productos de iluminación LED",
                "¿Cuáles están en stock?",
                "Gracias por la ayuda"
            ]
            
            responses = []
            for i, message in enumerate(test_messages, 1):
                print(f"   📤 Mensaje {i}: {message[:30]}...")
                
                response = await self.agent.process_message(message, f"test_user_{i}")
                responses.append(response)
                
                print(f"   📥 Respuesta {i}: {response[:50]}...")
            
            # Verificar que todas las respuestas son válidas
            valid_responses = all(
                response and len(response.strip()) > 10 
                for response in responses
            )
            
            print(f"   📊 Respuestas válidas: {len(responses)}/4")
            
            return valid_responses
            
        except Exception as e:
            print(f"   ❌ Error procesando mensajes: {e}")
            return False
    
    async def test_adaptive_strategies(self) -> bool:
        """Prueba: Estrategias adaptativas del agente"""
        if not self.agent:
            return False
        
        try:
            # Probar diferentes tipos de consultas
            strategy_tests = [
                ("Hola, buenos días", "quick_response"),
                ("Busco focos LED para exterior", "tool_assisted"),
                ("¿Cuál es mi pedido y cuándo llega?", "multi_agent"),
                ("Cuéntame sobre sus políticas", "standard_response")
            ]
            
            strategy_results = []
            
            for message, expected_strategy in strategy_tests:
                # Determinar estrategia sin procesar completamente
                strategy = await self.agent._determine_response_strategy(message)
                strategy_results.append((message, strategy, expected_strategy))
                
                print(f"   🎯 '{message[:20]}...' → {strategy}")
            
            # Verificar que se asignan estrategias válidas
            valid_strategies = all(
                strategy in ["quick_response", "tool_assisted", "multi_agent", "standard_response"]
                for _, strategy, _ in strategy_results
            )
            
            return valid_strategies
            
        except Exception as e:
            print(f"   ❌ Error en estrategias adaptativas: {e}")
            return False
    
    async def test_database_integration(self) -> bool:
        """Prueba: Integración con base de datos"""
        if not self.agent:
            return False
        
        try:
            # Probar búsqueda de productos específica
            response = await self.agent._handle_product_search("reflectores LED jardín")
            
            print(f"   🔍 Búsqueda de productos: {len(response)} caracteres")
            
            # Verificar que la respuesta contiene información relevante
            contains_products = any(
                keyword in response.lower() 
                for keyword in ["producto", "precio", "stock", "encontré"]
            )
            
            # Probar verificación de stock
            stock_response = await self.agent._handle_stock_check("LED")
            
            print(f"   📦 Verificación de stock: {len(stock_response)} caracteres")
            
            contains_stock_info = any(
                keyword in stock_response.lower()
                for keyword in ["stock", "disponible", "inventario"]
            )
            
            return contains_products and contains_stock_info
            
        except Exception as e:
            print(f"   ❌ Error en integración de base de datos: {e}")
            return False
    
    async def test_error_handling(self) -> bool:
        """Prueba: Manejo de errores y casos edge"""
        if not self.agent:
            return False
        
        try:
            error_cases = [
                "",  # Mensaje vacío
                "   ",  # Solo espacios
                "x" * 1000,  # Mensaje muy largo
                "🤖🔥💻🚀" * 50,  # Solo emojis
            ]
            
            handled_errors = 0
            
            for case in error_cases:
                try:
                    response = await self.agent.process_message(case, "error_test")
                    if response and len(response.strip()) > 0:
                        handled_errors += 1
                        print(f"   ✅ Caso manejado: '{case[:20]}...'")
                except Exception:
                    print(f"   ⚠️ Caso no manejado: '{case[:20]}...'")
            
            success_rate = handled_errors / len(error_cases)
            print(f"   📊 Casos manejados: {handled_errors}/{len(error_cases)} ({success_rate:.1%})")
            
            return success_rate >= 0.75  # Al menos 75% de casos manejados
            
        except Exception as e:
            print(f"   ❌ Error en manejo de errores: {e}")
            return False
    
    async def test_performance(self) -> bool:
        """Prueba: Rendimiento del sistema"""
        if not self.agent:
            return False
        
        try:
            # Medir tiempo de respuesta promedio
            test_queries = [
                "Hola",
                "Busco productos LED",
                "¿Qué tienen en stock?",
                "Información de precios",
                "Gracias"
            ]
            
            response_times = []
            
            for query in test_queries:
                start_time = datetime.now()
                await self.agent.process_message(query, "perf_test")
                end_time = datetime.now()
                
                response_time = (end_time - start_time).total_seconds()
                response_times.append(response_time)
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            print(f"   ⏱️ Tiempo promedio: {avg_response_time:.2f}s")
            print(f"   ⏱️ Tiempo máximo: {max_response_time:.2f}s")
            
            # Criterio: promedio < 5s, máximo < 10s
            return avg_response_time < 5.0 and max_response_time < 10.0
            
        except Exception as e:
            print(f"   ❌ Error en prueba de rendimiento: {e}")
            return False
    
    async def generate_report(self):
        """Generar reporte final de pruebas"""
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.test_results if r["status"] == "PASSED")
        failed = sum(1 for r in self.test_results if r["status"] == "FAILED")
        errors = sum(1 for r in self.test_results if r["status"] == "ERROR")
        total = len(self.test_results)
        
        success_rate = (passed / total) * 100 if total > 0 else 0
        
        print("\n" + "=" * 60)
        print("📊 REPORTE FINAL DE PRUEBAS - FASE 3")
        print("=" * 60)
        print(f"⏰ Duración total: {total_duration:.2f} segundos")
        print(f"📈 Tasa de éxito: {success_rate:.1f}%")
        print(f"✅ Pruebas exitosas: {passed}")
        print(f"❌ Pruebas fallidas: {failed}")
        print(f"💥 Errores: {errors}")
        print(f"📊 Total de pruebas: {total}")
        
        print("\n📋 DETALLE DE RESULTADOS:")
        for result in self.test_results:
            status_icon = {"PASSED": "✅", "FAILED": "❌", "ERROR": "💥"}[result["status"]]
            duration = result.get("duration", 0)
            print(f"   {status_icon} {result['name']}: {result['status']} ({duration:.2f}s)")
        
        # Recomendaciones
        print("\n💡 RECOMENDACIONES:")
        if success_rate >= 90:
            print("   🎉 Excelente! El sistema está listo para producción.")
        elif success_rate >= 75:
            print("   👍 Bien! Revisar las pruebas fallidas antes de producción.")
        elif success_rate >= 50:
            print("   ⚠️ Advertencia! Resolver problemas críticos antes de continuar.")
        else:
            print("   🚨 Crítico! El sistema requiere revisión completa.")
        
        print("\n🚀 SIGUIENTE PASO:")
        if success_rate >= 75:
            print("   Iniciar el sistema completo con: python app.py")
            print("   Acceder al chat en: http://localhost:8000/chat")
        else:
            print("   Revisar logs y resolver problemas identificados")
        
        print("=" * 60)
        
        # Guardar reporte en archivo
        report_data = {
            "timestamp": self.start_time.isoformat(),
            "duration": total_duration,
            "success_rate": success_rate,
            "summary": {
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "total": total
            },
            "results": self.test_results
        }
        
        with open("test_results_phase3.json", "w") as f:
            json.dump(report_data, f, indent=2)
        
        print(f"📄 Reporte guardado en: test_results_phase3.json")

async def main():
    """Función principal"""
    tester = Phase3IntegrationTest()
    await tester.run_all_tests()

if __name__ == "__main__":
    asyncio.run(main()) 