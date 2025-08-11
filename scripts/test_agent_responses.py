#!/usr/bin/env python3
"""
Test comprehensive agent responses to ensure no empty messages
"""

import asyncio
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_agent_responses():
    """Test various queries to ensure agent always returns responses"""
    
    print("🧪 Testing Agent Response System\n")
    
    # Initialize the agent
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    # Test queries covering different scenarios
    test_cases = [
        {
            "category": "Product Search",
            "queries": [
                "tengo que cambiar mi sobretensiones y no se que potencia elegir",
                "busco protector sobretensiones",
                "necesito diferencial 40A",
                "quiero comprar cable eléctrico",
                "magnetotérmico bipolar"
            ]
        },
        {
            "category": "FAQ/Knowledge",
            "queries": [
                "¿cuál es el horario de atención?",
                "¿cómo puedo devolver un producto?",
                "¿cuánto tarda el envío?",
                "¿qué garantía tienen los productos?",
                "¿hacen envíos a Canarias?"
            ]
        },
        {
            "category": "Order Inquiries",
            "queries": [
                "quiero consultar mi pedido",
                "mi email es test@example.com, tengo pedidos?",
                "estado del pedido 12345",
                "¿cuándo llega mi pedido?",
                "tracking de mi compra"
            ]
        },
        {
            "category": "General/Greeting",
            "queries": [
                "hola",
                "buenos días",
                "necesito ayuda",
                "gracias",
                "adiós"
            ]
        },
        {
            "category": "Complex/Technical",
            "queries": [
                "necesito instalar un cuadro eléctrico completo para mi casa",
                "qué diferencia hay entre un diferencial de 30mA y uno de 300mA",
                "cómo calculo la sección de cable que necesito",
                "protección para instalación fotovoltaica",
                "normativa actual para instalaciones eléctricas"
            ]
        }
    ]
    
    # Track results
    total_tests = 0
    empty_responses = 0
    errors = 0
    response_times = []
    
    for category_data in test_cases:
        category = category_data["category"]
        queries = category_data["queries"]
        
        print(f"\n{'='*60}")
        print(f"📁 Category: {category}")
        print(f"{'='*60}")
        
        for query in queries:
            total_tests += 1
            print(f"\n🔍 Query: '{query}'")
            
            try:
                import time
                start_time = time.time()
                
                # Process the message
                response = await agent.process_message(
                    message=query,
                    user_id="test_user",
                    platform="whatsapp"
                )
                
                end_time = time.time()
                response_time = end_time - start_time
                response_times.append(response_time)
                
                # Check response
                if not response or response.strip() == '':
                    print(f"❌ EMPTY RESPONSE!")
                    empty_responses += 1
                else:
                    print(f"✅ Response received ({len(response)} chars, {response_time:.2f}s)")
                    # Show first 150 chars of response
                    preview = response[:150] + "..." if len(response) > 150 else response
                    print(f"   Preview: {preview}")
                    
            except Exception as e:
                print(f"❌ Error: {e}")
                errors += 1
                logger.error(f"Error processing query '{query}'", exc_info=True)
            
            # Small delay between tests
            await asyncio.sleep(0.5)
    
    # Print summary
    print(f"\n\n{'='*60}")
    print(f"📊 TEST SUMMARY")
    print(f"{'='*60}")
    print(f"Total tests: {total_tests}")
    print(f"Empty responses: {empty_responses}")
    print(f"Errors: {errors}")
    print(f"Success rate: {(total_tests - empty_responses - errors) / total_tests * 100:.1f}%")
    
    if response_times:
        avg_time = sum(response_times) / len(response_times)
        print(f"Average response time: {avg_time:.2f}s")
        print(f"Min response time: {min(response_times):.2f}s")
        print(f"Max response time: {max(response_times):.2f}s")
    
    print(f"\n{'='*60}")
    
    if empty_responses == 0 and errors == 0:
        print("✅ All tests passed! No empty responses detected.")
    else:
        print("⚠️ Some tests failed. Check the logs above for details.")

if __name__ == "__main__":
    asyncio.run(test_agent_responses())