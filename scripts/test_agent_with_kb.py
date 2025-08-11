#!/usr/bin/env python3
"""
Test agent with properly initialized knowledge base
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
load_dotenv('env.agent')

async def test_agent_with_knowledge():
    """Test agent with initialized services"""
    
    print("🧪 Testing Agent with Knowledge Base Integration\n")
    print("=" * 60)
    
    # Initialize services BEFORE importing the agent
    print("🔧 Initializing services...")
    
    from services.database import db_service
    from services.embedding_service import embedding_service
    from services.knowledge_base import knowledge_service
    from services.conversation_logger import conversation_logger
    from services.conversation_memory import memory_service
    
    # Initialize all services
    await db_service.initialize()
    print("  ✅ Database initialized")
    
    await embedding_service.initialize()
    print("  ✅ Embedding service initialized")
    
    await knowledge_service.initialize()
    print("  ✅ Knowledge base initialized")
    
    await conversation_logger.initialize()
    print("  ✅ Conversation logger initialized")
    
    await memory_service.initialize()
    print("  ✅ Memory service initialized")
    
    # Now import and create the agent
    from src.agent.hybrid_agent import HybridCustomerAgent
    
    print("\n🤖 Creating agent...")
    agent = HybridCustomerAgent()
    print("✅ Agent created with initialized services\n")
    
    # Test queries
    test_queries = [
        # FAQ queries that MUST use knowledge base
        ("¿Cuál es el horario de atención?", "faq"),
        ("¿Cuáles son las formas de pago?", "faq"),
        ("¿Cómo puedo devolver un producto?", "faq"),
        ("¿Cuál es la política de garantía?", "faq"),
        ("¿Cuánto tiempo tarda el envío?", "faq"),
        ("¿Hacen envíos a Canarias?", "faq"),
    ]
    
    # Test each query
    success_count = 0
    for i, (query, query_type) in enumerate(test_queries, 1):
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
            
            # Check if response contains real knowledge base info
            knowledge_indicators = {
                "horario": ["lunes", "viernes", "9:00", "14:00", "16:00", "19:00", "sábado"],
                "pago": ["transferencia", "tarjeta", "bizum", "paypal", "contrareembolso"],
                "devolver": ["14 días", "30 días", "desistimiento", "estado original"],
                "garantía": ["3 años", "2 años", "fabricante", "defecto"],
                "envío": ["24", "48", "72", "horas", "península", "baleares"],
                "canarias": ["islas", "72 horas", "96 horas", "envío"]
            }
            
            # Check for specific indicators based on query
            found_indicator = False
            for key in knowledge_indicators:
                if key in query.lower():
                    for indicator in knowledge_indicators[key]:
                        if indicator in response.lower():
                            found_indicator = True
                            break
                    break
            
            if found_indicator:
                print("\n✅ Response contains REAL knowledge base information!")
                success_count += 1
            else:
                print("\n⚠️ Response seems generic - NOT using knowledge base")
                print("   Expected specific information from the knowledge documents")
                    
        except Exception as e:
            print(f"\n❌ Error: {e}")
            import traceback
            traceback.print_exc()
        
        # Small delay between tests
        await asyncio.sleep(0.5)
    
    # Summary
    print("\n\n" + "="*60)
    print("📊 TEST RESULTS")
    print("="*60)
    print(f"\nPassed: {success_count}/{len(test_queries)} tests")
    print(f"Success rate: {(success_count/len(test_queries)*100):.1f}%")
    
    if success_count == len(test_queries):
        print("\n✅ All tests passed! The agent is correctly using the knowledge base.")
    else:
        print("\n❌ Some tests failed. The agent is not consistently using the knowledge base.")
        print("   Check the error messages and responses above for details.")
    
    # Close services
    print("\n🔧 Closing services...")
    await db_service.close()
    await conversation_logger.close()
    await memory_service.close()

if __name__ == "__main__":
    asyncio.run(test_agent_with_knowledge())