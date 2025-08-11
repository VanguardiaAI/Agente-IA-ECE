#!/usr/bin/env python3
"""
Test script to verify that the agent is correctly using the knowledge base
Version 2: With proper initialization
"""

import asyncio
import sys
import os
import logging
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
load_dotenv('env.agent')

from src.agent.hybrid_agent import HybridCustomerAgent
from services.knowledge_base import KnowledgeBaseService
from services.database import DatabaseService
from services.embedding_service import EmbeddingService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_knowledge_integration():
    """Test various FAQ queries to ensure knowledge base is being used"""
    
    print("🧪 Testing Knowledge Base Integration with Agent\n")
    
    # Initialize services first
    print("🔧 Initializing services...")
    
    # Initialize database service
    db_service = DatabaseService()
    await db_service.initialize()
    
    # Initialize embedding service
    embedding_service = EmbeddingService()
    
    # Initialize knowledge base service
    knowledge_service = KnowledgeBaseService()
    await knowledge_service.initialize()
    
    # Ensure knowledge base is loaded
    print("📚 Loading knowledge base documents...")
    await knowledge_service.load_all_documents()
    
    print("✅ Services initialized\n")
    
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
    
    # Test direct knowledge base search first
    print("🔍 Testing direct knowledge base search...")
    for query in test_queries[:3]:
        print(f"\nSearching for: {query}")
        results = await knowledge_service.search_knowledge(query, limit=2)
        if results:
            print(f"✅ Found {len(results)} results")
            for i, result in enumerate(results, 1):
                print(f"   {i}. {result.get('title', 'Unknown')}: {result.get('content', '')[:100]}...")
        else:
            print("❌ No results found")
    
    print("\n" + "="*60 + "\n")
    
    # Test each query with the agent
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
            knowledge_keywords = ['horario', 'pago', 'devolución', 'garantía', 'envío', 'política', 
                                'lunes', 'viernes', 'días', 'transferencia', 'tarjeta', 'efectivo',
                                '24 horas', '48 horas', 'península', 'islas']
            
            if any(keyword in response.lower() for keyword in knowledge_keywords):
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