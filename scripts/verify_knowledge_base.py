#!/usr/bin/env python3
"""
Verify that the knowledge base is properly loaded and searchable
"""

import asyncio
import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
load_dotenv('env.agent')

async def verify_knowledge_base():
    """Verify knowledge base functionality"""
    
    print("🔍 Verifying Knowledge Base System\n")
    print("=" * 60)
    
    # Test 1: Check if knowledge files exist
    print("\n1️⃣ Checking knowledge files...")
    knowledge_dir = "/Users/vanguardia/Desktop/Proyectos/MCP-WC/knowledge"
    
    import glob
    md_files = glob.glob(f"{knowledge_dir}/**/*.md", recursive=True)
    print(f"Found {len(md_files)} markdown files:")
    for file in md_files:
        print(f"  ✓ {os.path.basename(file)}")
    
    # Test 2: Try to initialize services
    print("\n2️⃣ Testing database connection...")
    try:
        from services.database import db_service
        await db_service.initialize()
        print("  ✓ Database service initialized")
        
        # Test connection
        stats = await db_service.get_statistics()
        print(f"  ✓ Database connection successful")
        print(f"  ℹ️ Total documents: {stats.get('total_documents', 0)}")
        print(f"  ℹ️ Products: {stats.get('by_type', {}).get('product', 0)}")
        print(f"  ℹ️ Knowledge docs: {stats.get('by_type', {}).get('knowledge', 0)}")
    except Exception as e:
        print(f"  ✗ Database error: {e}")
        print("  💡 Make sure PostgreSQL is running and configured correctly")
        return
    
    # Test 3: Test embedding service
    print("\n3️⃣ Testing embedding service...")
    try:
        from services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        
        # Initialize the service first
        await embedding_service.initialize()
        print("  ✓ Embedding service initialized")
        
        # Test embedding generation
        test_embedding = await embedding_service.generate_embedding("test query")
        print(f"  ✓ Embedding generated (dimension: {len(test_embedding)})")
    except Exception as e:
        print(f"  ✗ Embedding error: {e}")
        print("  💡 Check your OpenAI API key in env.agent")
        return
    
    # Test 4: Test knowledge base service
    print("\n4️⃣ Testing knowledge base service...")
    try:
        from services.knowledge_base import KnowledgeBaseService
        kb_service = KnowledgeBaseService()
        await kb_service.initialize()
        print("  ✓ Knowledge base service initialized")
        
        # Check if documents are loaded from statistics
        stats = await db_service.get_statistics()
        doc_count = stats.get('by_type', {}).get('knowledge', 0)
        print(f"  ℹ️ Knowledge documents in database: {doc_count}")
        
        if doc_count == 0:
            print("  ⚠️ No documents in database. Loading documents...")
            await kb_service.load_all_documents()
            
            # Check again
            stats = await db_service.get_statistics()
            doc_count = stats.get('by_type', {}).get('knowledge', 0)
            print(f"  ✓ Documents loaded: {doc_count}")
        
        # Test search
        print("\n5️⃣ Testing knowledge search...")
        test_queries = [
            "horario de atención",
            "formas de pago",
            "política de devolución"
        ]
        
        for query in test_queries:
            results = await kb_service.search_knowledge(query, limit=1)
            if results:
                print(f"  ✓ '{query}' → Found: {results[0].get('title', 'Unknown')}")
                print(f"    Preview: {results[0].get('content', '')[:100]}...")
            else:
                print(f"  ✗ '{query}' → No results")
        
    except Exception as e:
        print(f"  ✗ Knowledge base error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print("\nIf all tests passed, the knowledge base system is working correctly.")
    print("If there are errors, fix them before testing the agent integration.")

if __name__ == "__main__":
    asyncio.run(verify_knowledge_base())