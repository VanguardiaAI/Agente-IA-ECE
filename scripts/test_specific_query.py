#!/usr/bin/env python3
"""
Test specific query that returns empty response
"""

import asyncio
import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent.hybrid_agent import HybridCustomerAgent

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_specific_query():
    """Test the specific query that's returning empty responses"""
    
    print("🧪 Testing Specific Query: 'tengo que cambiar mi sobretensiones y no se que potencia elegir'\n")
    
    # Initialize the agent
    agent = HybridCustomerAgent()
    await agent.initialize()
    
    # Test queries
    test_queries = [
        # Original problematic query
        "tengo que cambiar mi sobretensiones y no se que potencia elegir",
        
        # Variations to test
        "necesito cambiar sobretensiones, qué potencia elegir",
        "busco protección contra sobretensiones",
        "qué protector de sobretensiones necesito",
        
        # Simple product search
        "sobretensiones",
        
        # FAQ-style query
        "cómo elegir protección sobretensiones"
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n{'='*80}")
        print(f"Test {i}/{len(test_queries)}: {query}")
        print(f"{'='*80}")
        
        try:
            # Get the strategy that will be used
            strategy = await agent._determine_response_strategy(query)
            print(f"📊 Strategy determined: {strategy}")
            
            # Get query type if using tools
            if strategy == "tool_assisted":
                query_type = await agent._classify_query_type(query)
                print(f"📊 Query type: {query_type}")
            
            # Process the message
            response = await agent.process_message(
                message=query,
                user_id="test_user",
                platform="whatsapp"
            )
            
            print(f"\n🤖 Response length: {len(response)} characters")
            print(f"🤖 Response empty: {not response or response.strip() == ''}")
            print(f"\n🤖 Response:\n{response}")
            
            # Check response quality
            if not response or response.strip() == '':
                print("\n❌ EMPTY RESPONSE DETECTED!")
            elif len(response) < 20:
                print("\n⚠️ Very short response")
            else:
                print("\n✅ Response looks normal")
                
        except Exception as e:
            print(f"\n❌ Error: {e}")
            logger.error(f"Error testing query '{query}'", exc_info=True)
        
        # Small delay between tests
        await asyncio.sleep(2)
    
    # Additional debug: Check if knowledge base is working
    print(f"\n\n{'='*80}")
    print("🔍 Testing knowledge base search directly")
    print(f"{'='*80}")
    
    try:
        from services.knowledge_base import knowledge_service
        
        # Search for surge protector information
        kb_results = await knowledge_service.search_knowledge(
            query="sobretensiones protección potencia",
            limit=3
        )
        
        print(f"\n📚 Knowledge base results: {len(kb_results)} documents found")
        for idx, result in enumerate(kb_results, 1):
            print(f"\n{idx}. {result.get('title', 'No title')}")
            print(f"   Score: {result.get('score', 0):.3f}")
            print(f"   Content preview: {result.get('content', '')[:100]}...")
            
    except Exception as e:
        print(f"\n❌ Error searching knowledge base: {e}")

if __name__ == "__main__":
    asyncio.run(test_specific_query())