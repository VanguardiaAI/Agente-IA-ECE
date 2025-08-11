#!/usr/bin/env python3
"""
Test script to verify that the agent is correctly using the knowledge base
"""

import asyncio
import sys
import os
import logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_knowledge_integration():
    """Test various FAQ queries to ensure knowledge base is being used"""
    
    print("🧪 Testing Knowledge Base Integration with Agent\n")
    
    # Initialize the agent
    agent = HybridCustomerAgent()
    
    # Test queries that should trigger knowledge base search
    test_queries = [
        "¿Cuál es el horario de atención?",
        "¿Cuáles son las formas de pago?",
        "¿Cómo puedo devolver un producto?",
        "¿Cuál es la política de garantía?",
        "¿Cuánto tarda el envío?",
        "¿Hacen envíos a toda España?",
        "¿Puedo cambiar un producto?",
        "¿Dónde están ubicados?",
        "¿Cuál es el teléfono de contacto?",
        "Quiero hacer una reclamación"
    ]
    
    # Test each query
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*60}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print(f"{'='*60}")
        
        try:
            # Process the message
            response = await agent.process_message(
                message=query,
                user_id="test_user",
                platform="whatsapp"
            )
            
            print(f"\n🤖 Response:\n{response}")
            
            # Check if response seems to come from knowledge base
            if any(keyword in response.lower() for keyword in ['horario', 'pago', 'devolución', 'garantía', 'envío', 'política']):
                print("\n✅ Response appears to contain knowledge base information")
            else:
                print("\n⚠️ Response might not be using knowledge base")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.error(f"Error testing query '{query}': {e}", exc_info=True)
        
        # Small delay between tests
        await asyncio.sleep(1)
    
    print("\n\n📊 Test Summary:")
    print("If responses contain specific information about policies, schedules, etc.,")
    print("then the knowledge base integration is working correctly.")
    print("\nIf responses are generic or don't match the FAQ content,")
    print("there might be an issue with the knowledge base search or integration.")

if __name__ == "__main__":
    asyncio.run(test_knowledge_integration())