#!/usr/bin/env python3
"""
Script para probar el formato de productos optimizado para WhatsApp
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_whatsapp_format():
    """Probar el formato de productos como se verán en WhatsApp"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        # Crear agente
        agent = HybridCustomerAgent()
        
        print("=" * 80)
        print("🧪 PRUEBA DE FORMATO PARA WHATSAPP")
        print("=" * 80)
        
        # Probar con diferentes búsquedas
        queries = [
            "ventilador gabarron",
            "productos en oferta",
            "calefactor"
        ]
        
        for query in queries:
            print(f"\n📱 Simulando mensaje de WhatsApp: '{query}'")
            print("-" * 60)
            
            # Procesar mensaje
            response = await agent.process_message(
                message=query,
                user_id="test_user"
            )
            
            print("\n📤 Respuesta formateada para WhatsApp:")
            print(response)
            print("\n" + "=" * 80)
            
            # Pequeña pausa entre pruebas
            await asyncio.sleep(1)
        
        # También probar directamente la búsqueda
        print("\n🔍 Prueba directa de búsqueda de productos:")
        print("-" * 60)
        
        # Buscar un producto específico
        embedding = await embedding_service.generate_embedding("gabarron v-25")
        results = await db_service.hybrid_search(
            query_text="gabarron v-25",
            query_embedding=embedding,
            content_types=["product"],
            limit=1
        )
        
        if results:
            result = results[0]
            metadata = result.get('metadata', {})
            
            print("\n📦 Ejemplo de producto individual:")
            print(f"Título: {result.get('title', 'N/A')}")
            print(f"Precio: {metadata.get('price', 'N/A')}€")
            print(f"Precio regular: {metadata.get('regular_price', 'N/A')}€")
            print(f"Precio oferta: {metadata.get('sale_price', 'N/A')}€")
            print(f"Link: {metadata.get('permalink', 'N/A')}")
            print(f"SKU: {metadata.get('sku', 'N/A')}")
            print(f"Categorías: {metadata.get('categories', [])}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_whatsapp_format())