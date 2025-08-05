#!/usr/bin/env python3
"""
Servidor MCP HTTP para Sistema de Atención al Cliente
FASE 3: Integrado con búsqueda híbrida y agente IA
Versión FastMCP optimizada para el agente híbrido
"""

import asyncio
import uvicorn
import sys
import os
from typing import List, Dict, Any, Optional

# Agregar el directorio raíz al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastmcp import FastMCP
from services.database import db_service
from services.embedding_service import embedding_service
from services.woocommerce import WooCommerceService
from services.conversation_logger import conversation_logger
from config.settings import settings

# Crear instancia de FastMCP
mcp = FastMCP("Customer Service Assistant - Fase 3")

# Inicializar servicios
wc_service = WooCommerceService()

@mcp.tool()
async def search_products_hybrid(query: str, limit: int = 10) -> str:
    """
    Buscar productos usando búsqueda híbrida (semántica + texto)
    
    Args:
        query: Término de búsqueda (ej: "iluminación exterior LED")
        limit: Número máximo de resultados
    
    Returns:
        Resultados formateados con productos encontrados
    """
    try:
        if not db_service.initialized:
            await db_service.initialize()
        
        # Generar embedding para la consulta
        embedding = await embedding_service.generate_embedding(query)
        
        # Realizar búsqueda híbrida
        results = await db_service.hybrid_search(
            query_text=query,
            query_embedding=embedding,
            content_types=["product"],
            limit=limit
        )
        
        if not results:
            return f"❌ No encontré productos que coincidan con '{query}'. ¿Podrías ser más específico?"
        
        # Formatear respuesta
        response = f"🔍 **Encontré {len(results)} productos para '{query}':**\n\n"
        
        for i, result in enumerate(results, 1):
            title = result.get('title', 'Producto')
            metadata = result.get('metadata', {})
            price = metadata.get('price', 0)
            stock_status = metadata.get('stock_status', 'unknown')
            rrf_score = result.get('rrf_score', 0)
            external_id = result.get('external_id', '')
            
            # Icono de stock
            stock_icon = "✅" if stock_status == 'instock' else "❌"
            
            response += f"{i}. {stock_icon} **{title}**\n"
            if price > 0:
                response += f"   💰 Precio: ${price}\n"
            if external_id:
                response += f"   🆔 ID: {external_id}\n"
            response += f"   📊 Relevancia: {rrf_score:.3f}\n\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error en búsqueda híbrida: {str(e)}"

@mcp.tool()
async def get_product_details(product_id: str) -> str:
    """
    Obtener detalles completos de un producto específico
    
    Args:
        product_id: ID del producto (puede ser externo o WooCommerce)
    
    Returns:
        Detalles completos del producto
    """
    try:
        # Intentar obtener desde base de conocimiento primero
        product = await db_service.get_knowledge_by_external_id(product_id)
        
        if product:
            title = product.get('title', 'Producto')
            content = product.get('content', '')
            metadata = product.get('metadata', {})
            
            response = f"📦 **{title}**\n\n"
            if content:
                response += f"**Descripción:** {content}\n\n"
            
            # Información de metadata
            for key, value in metadata.items():
                if key == 'price' and value > 0:
                    response += f"💰 **Precio:** ${value}\n"
                elif key == 'stock_status':
                    status = "✅ En stock" if value == 'instock' else "❌ Sin stock"
                    response += f"📦 **Estado:** {status}\n"
                elif key == 'categories' and value:
                    response += f"📂 **Categorías:** {', '.join(value) if isinstance(value, list) else value}\n"
                elif key == 'sku' and value:
                    response += f"🔢 **SKU:** {value}\n"
            
            return response
        else:
            # Fallback a WooCommerce directo
            try:
                wc_product = await wc_service.get_product(int(product_id))
                if wc_product:
                    return wc_service.format_product(wc_product)
                else:
                    return f"❌ No se encontró el producto con ID: {product_id}"
            except ValueError:
                return f"❌ ID de producto inválido: {product_id}"
            
    except Exception as e:
        return f"❌ Error obteniendo detalles: {str(e)}"

@mcp.tool()
async def check_product_stock(product_query: str) -> str:
    """
    Verificar disponibilidad de stock de productos
    
    Args:
        product_query: Nombre del producto o ID para verificar stock
    
    Returns:
        Estado de stock de los productos encontrados
    """
    try:
        if not db_service.initialized:
            await db_service.initialize()
        
        # Si parece ser un ID numérico, buscar directamente
        if product_query.isdigit():
            return await get_product_details(product_query)
        
        # Buscar productos por nombre
        embedding = await embedding_service.generate_embedding(product_query)
        
        results = await db_service.hybrid_search(
            query_text=product_query,
            query_embedding=embedding,
            content_types=["product"],
            limit=5
        )
        
        if not results:
            return f"❌ No encontré productos para verificar stock con: '{product_query}'"
        
        response = f"📦 **Estado de stock para '{product_query}':**\n\n"
        
        for result in results:
            title = result.get('title', 'Producto')
            metadata = result.get('metadata', {})
            stock_status = metadata.get('stock_status', 'unknown')
            stock_quantity = metadata.get('stock_quantity', 0)
            
            if stock_status == 'instock':
                if stock_quantity > 0:
                    response += f"✅ **{title}** - En stock ({stock_quantity} disponibles)\n"
                else:
                    response += f"✅ **{title}** - En stock\n"
            else:
                response += f"❌ **{title}** - Sin stock disponible\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error verificando stock: {str(e)}"

@mcp.tool()
async def get_product_categories() -> str:
    """
    Obtener todas las categorías de productos disponibles
    
    Returns:
        Lista de categorías con número de productos
    """
    try:
        categories = await wc_service.get_product_categories()
        
        if not categories:
            return "❌ No se encontraron categorías de productos"
        
        response = "📂 **Categorías de Productos Disponibles:**\n\n"
        
        for category in categories[:15]:  # Limitar a 15 categorías principales
            name = category.get('name', 'Sin nombre')
            count = category.get('count', 0)
            response += f"• **{name}** ({count} productos)\n"
        
        if len(categories) > 15:
            response += f"\n... y {len(categories) - 15} categorías más."
        
        return response
        
    except Exception as e:
        return f"❌ Error obteniendo categorías: {str(e)}"

@mcp.tool()
async def search_products_by_category(category_name: str, limit: int = 10) -> str:
    """
    Buscar productos de una categoría específica
    
    Args:
        category_name: Nombre de la categoría
        limit: Número máximo de productos
    
    Returns:
        Productos de la categoría especificada
    """
    try:
        # Buscar la categoría primero
        categories = await wc_service.get_product_categories(search=category_name)
        
        if not categories:
            return f"❌ No se encontró la categoría: '{category_name}'"
        
        category_id = categories[0]['id']
        products = await wc_service.get_products(category=category_id, per_page=limit)
        
        if not products:
            return f"❌ No hay productos en la categoría: '{category_name}'"
        
        return wc_service.format_product_list(products, f"Productos en '{category_name}'")
        
    except Exception as e:
        return f"❌ Error obteniendo productos por categoría: {str(e)}"

@mcp.tool()
async def smart_product_recommendation(user_query: str, limit: int = 5) -> str:
    """
    Recomendar productos usando IA semántica avanzada
    
    Args:
        user_query: Consulta del usuario (ej: "necesito algo para iluminar mi jardín")
        limit: Número de recomendaciones
    
    Returns:
        Recomendaciones inteligentes de productos
    """
    try:
        if not db_service.initialized:
            await db_service.initialize()
        
        # Generar embedding para la consulta
        embedding = await embedding_service.generate_embedding(user_query)
        
        # Búsqueda híbrida enfocada en productos
        results = await db_service.hybrid_search(
            query_text=user_query,
            query_embedding=embedding,
            content_types=["product"],
            limit=limit
        )
        
        if not results:
            return f"❌ No encontré recomendaciones específicas para: '{user_query}'\n\n¿Podrías ser más específico sobre qué tipo de producto necesitas?"
        
        response = f"🎯 **Recomendaciones inteligentes para: '{user_query}'**\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            title = result.get('title', 'Producto')
            price = metadata.get('price', 0)
            stock_status = metadata.get('stock_status', 'unknown')
            rrf_score = result.get('rrf_score', 0)
            
            # Icono de stock
            stock_icon = "✅" if stock_status == 'instock' else "❌"
            
            response += f"{i}. {stock_icon} **{title}**\n"
            if price > 0:
                response += f"   💰 Precio: ${price}\n"
            response += f"   🎯 Relevancia: {rrf_score:.3f}\n\n"
        
        response += "💡 **¿Te interesa algún producto específico?** Puedo darte más detalles sobre cualquiera de estos."
        
        return response
        
    except Exception as e:
        return f"❌ Error en recomendación inteligente: {str(e)}"

@mcp.tool()
async def get_order_status(order_id: str) -> str:
    """
    Consultar estado de un pedido específico
    
    Args:
        order_id: Número de pedido
    
    Returns:
        Estado detallado del pedido
    """
    try:
        # Intentar obtener pedido de WooCommerce
        order = await wc_service.get_order(order_id)
        
        if not order:
            return f"❌ No se encontró el pedido #{order_id}\n\n¿Podrías verificar el número de pedido? También puedes proporcionarme tu email para buscar todos tus pedidos."
        
        # Formatear información del pedido
        status = order.get('status', 'unknown')
        total = order.get('total', '0')
        date_created = order.get('date_created', '')
        customer_email = order.get('billing', {}).get('email', 'No disponible')
        
        status_emoji = {
            'pending': '⏳',
            'processing': '🔄',
            'completed': '✅',
            'cancelled': '❌',
            'refunded': '💸',
            'failed': '🚫'
        }.get(status, '❓')
        
        response = f"📋 **Pedido #{order_id}**\n\n"
        response += f"{status_emoji} **Estado:** {status.title()}\n"
        response += f"💰 **Total:** ${total}\n"
        response += f"📧 **Email:** {customer_email}\n"
        response += f"📅 **Fecha:** {date_created[:10] if date_created else 'No disponible'}\n\n"
        
        # Productos del pedido
        line_items = order.get('line_items', [])
        if line_items:
            response += "📦 **Productos:**\n"
            for item in line_items:
                name = item.get('name', 'Producto')
                quantity = item.get('quantity', 1)
                response += f"   • {name} (x{quantity})\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error consultando pedido: {str(e)}"

@mcp.tool()
async def search_orders_by_customer(customer_email: str) -> str:
    """
    Buscar pedidos por email del cliente
    
    Args:
        customer_email: Email del cliente
    
    Returns:
        Lista de pedidos del cliente
    """
    try:
        orders = await wc_service.get_orders(customer=customer_email, per_page=10)
        
        if not orders:
            return f"❌ No se encontraron pedidos para el email: {customer_email}\n\n¿El email está escrito correctamente?"
        
        response = f"📋 **Pedidos para {customer_email}:**\n\n"
        
        for order in orders:
            order_id = order.get('id', 'N/A')
            status = order.get('status', 'unknown')
            total = order.get('total', '0')
            date_created = order.get('date_created', '')
            
            status_emoji = {
                'pending': '⏳',
                'processing': '🔄',
                'completed': '✅',
                'cancelled': '❌',
                'refunded': '💸'
            }.get(status, '❓')
            
            response += f"{status_emoji} **Pedido #{order_id}** - ${total} ({status})\n"
            response += f"   📅 {date_created[:10] if date_created else 'Sin fecha'}\n\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error buscando pedidos: {str(e)}"

@mcp.tool()
async def get_system_health() -> str:
    """
    Verificar el estado del sistema
    
    Returns:
        Estado de todos los servicios
    """
    try:
        health_status = []
        
        # Verificar base de datos
        if db_service.initialized:
            stats = await db_service.get_statistics()
            health_status.append(f"✅ **Base de Datos:** Operativa ({stats.get('total_products', 0)} productos)")
        else:
            health_status.append("❌ **Base de Datos:** No disponible")
        
        # Verificar embeddings
        if embedding_service.initialized:
            health_status.append("✅ **Servicio de Embeddings:** Operativo")
        else:
            health_status.append("❌ **Servicio de Embeddings:** No disponible")
        
        # Verificar WooCommerce
        try:
            test_products = await wc_service.get_products(per_page=1)
            if test_products:
                health_status.append("✅ **WooCommerce:** Conectado")
            else:
                health_status.append("⚠️ **WooCommerce:** Sin productos")
        except:
            health_status.append("❌ **WooCommerce:** Error de conexión")
        
        response = "🏥 **Estado del Sistema:**\n\n"
        response += "\n".join(health_status)
        response += f"\n\n⏰ **Verificado:** {asyncio.get_running_loop().time()}"
        
        return response
        
    except Exception as e:
        return f"❌ Error verificando sistema: {str(e)}"

@mcp.tool()
async def get_help() -> str:
    """
    Obtener ayuda sobre las herramientas disponibles
    
    Returns:
        Lista completa de herramientas disponibles
    """
    return """
🛠️ **HERRAMIENTAS DISPONIBLES DEL SISTEMA:**

📦 **PRODUCTOS:**
• `search_products_hybrid` - Búsqueda híbrida (semántica + texto)
• `get_product_details` - Detalles completos de un producto
• `check_product_stock` - Verificar disponibilidad de stock
• `get_product_categories` - Listar todas las categorías
• `search_products_by_category` - Productos por categoría
• `smart_product_recommendation` - Recomendaciones IA avanzadas

📋 **PEDIDOS:**
• `get_order_status` - Estado de un pedido específico
• `search_orders_by_customer` - Pedidos por email del cliente

🔧 **SISTEMA:**
• `get_system_health` - Estado de todos los servicios
• `get_help` - Esta ayuda

🚀 **SISTEMA INTEGRADO FASE 3:**
- Búsqueda híbrida con embeddings OpenAI
- Base de conocimiento PostgreSQL + pgvector
- Conexión directa a WooCommerce
- Agente IA conversacional avanzado

💡 **Uso recomendado:** El sistema aprende de las consultas y mejora las recomendaciones automáticamente.
"""

async def initialize_services():
    """Inicializar todos los servicios necesarios"""
    try:
        print("🚀 Inicializando servicios MCP...")
        
        # Inicializar base de datos
        if not db_service.initialized:
            await db_service.initialize()
            print("✅ Base de datos inicializada")
        
        # Inicializar embeddings
        if not embedding_service.initialized:
            await embedding_service.initialize()
            print("✅ Servicio de embeddings inicializado")
        
        print("✅ Servidor MCP listo con búsqueda híbrida")
        
    except Exception as e:
        print(f"❌ Error inicializando servicios: {e}")
        raise

if __name__ == "__main__":
    print("🚀 Iniciando Servidor MCP HTTP - Fase 3")
    print("🔍 Búsqueda Híbrida + Agente IA + WooCommerce")
    print("=" * 60)
    print("📍 URL: http://localhost:8000/mcp")
    print("🔧 Herramientas: 10 herramientas híbridas")
    print("🤖 Integrado con agente conversacional")
    print("=" * 60)
    
    # Ejecutar servidor con transporte HTTP
    mcp.run(
        transport="streamable-http",
        host="127.0.0.1",
        port=8000,
        path="/mcp",
        on_startup=initialize_services
    ) 