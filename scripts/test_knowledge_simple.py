#!/usr/bin/env python3
"""
Simple test script to verify knowledge base integration
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
load_dotenv('env.agent')

from src.agent.hybrid_agent import HybridCustomerAgent

async def test_knowledge_integration():
    """Test various FAQ queries to ensure knowledge base is being used"""
    
    print("🧪 Testing Knowledge Base Integration with Agent\n")
    print("=" * 60)
    
    # Initialize the agent (it will initialize its own services)
    print("🔧 Initializing agent...")
    agent = HybridCustomerAgent()
    print("✅ Agent initialized\n")
    
    # Test queries that should trigger knowledge base search
    test_queries = [
        # FAQ queries that should use knowledge base
        ("¿Cuál es el horario de atención?", "faq"),
        ("¿Cuáles son las formas de pago?", "faq"),
        ("¿Cómo puedo devolver un producto?", "faq"),
        ("¿Cuál es la política de garantía?", "faq"),
        ("¿Cuánto tiempo tarda el envío?", "faq"),
        
        # Product queries for comparison
        ("Busco un diferencial de 40A", "product"),
        ("¿Tienen ventiladores de techo?", "product"),
        
        # Order queries for comparison
        ("Quiero ver mi pedido jose@example.com", "order"),
    ]
    
    # Test each query
    for i, (query, query_type) in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_queries)} [{query_type.upper()}]: {query}")
        print(f"{'='*60}")
        
        try:
            # Process the message
            response = await agent.process_message(
                message=query,
                user_id="test_user",
                platform="whatsapp"
            )
            
            print(f"\n🤖 Response:\n{response}")
            
            # Analyze response based on query type
            if query_type == "faq":
                # For FAQ queries, check if response contains specific information
                faq_indicators = [
                    'lunes', 'viernes', 'horario', '9:00', '14:00', '16:00', '19:00',  # Schedule
                    'transferencia', 'tarjeta', 'efectivo', 'pago',  # Payment
                    'devolución', 'días', 'cambio', 'garantía',  # Returns
                    'envío', 'península', 'islas', '24', '48', 'horas',  # Shipping
                    'política', 'condiciones'  # Policies
                ]
                
                if any(indicator in response.lower() for indicator in faq_indicators):
                    print("\n✅ Response contains specific FAQ information - Knowledge base is working!")
                else:
                    print("\n⚠️ Response seems generic - Knowledge base might not be working")
                    print("   Expected specific information about policies, schedules, etc.")
                    
            elif query_type == "product":
                if any(word in response.lower() for word in ['producto', 'precio', '€', 'stock']):
                    print("\n✅ Product search response detected")
                    
            elif query_type == "order":
                if any(word in response.lower() for word in ['pedido', 'orden', 'email']):
                    print("\n✅ Order inquiry response detected")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print("\nFor FAQ queries, the agent should provide specific information from")
    print("the knowledge base documents (schedules, policies, etc.)")
    print("\nIf FAQ responses are generic or inventive, the knowledge base")
    print("integration needs to be fixed.")
    print("\n✨ Check the responses above to verify knowledge base usage.")

if __name__ == "__main__":
    asyncio.run(test_knowledge_integration())