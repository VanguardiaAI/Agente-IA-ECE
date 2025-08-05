#!/usr/bin/env python3
"""
Servidor MCP para El Corte Eléctrico
Integración con WooCommerce para atención al cliente con IA
"""

import asyncio
from fastmcp import FastMCP
from config.settings import settings
from tools.product_tools import register_product_tools
from tools.order_tools import register_order_tools
from services.conversation_logger import conversation_logger

# Crear instancia de FastMCP
mcp = FastMCP("Customer Service Assistant")

# Registrar herramientas
register_product_tools(mcp)
register_order_tools(mcp)

@mcp.tool()
async def test_connection() -> str:
    """Prueba la conexión con WooCommerce"""
    try:
        from services.woocommerce import WooCommerceService
        wc_service = WooCommerceService()
        
        # Intentar obtener información básica
        response = await wc_service.get_products(per_page=1)
        if response:
            return "✅ Conexión exitosa con WooCommerce"
        else:
            return "❌ Error: No se pudo conectar con WooCommerce"
    except Exception as e:
        return f"❌ Error de conexión: {str(e)}"

@mcp.tool()
async def get_help() -> str:
    """Obtiene ayuda sobre las funciones disponibles del asistente"""
    help_text = """
🛍️ **Asistente de Atención al Cliente**

**Productos:**
• Buscar productos por nombre o categoría
• Ver detalles de productos específicos
• Consultar stock disponible
• Ver categorías de productos

**Pedidos:**
• Consultar estado de pedidos
• Rastrear pedidos por número
• Ver pedidos recientes
• Buscar pedidos por cliente
• Obtener resumen de pedidos

**Ayuda:**
• test_connection - Probar conexión con la tienda
• get_help - Ver esta ayuda
• get_conversation_stats - Ver estadísticas de uso (si está habilitado)

¿En qué puedo ayudarte hoy?
    """
    return help_text

@mcp.tool()
async def get_conversation_stats(days: int = 7) -> str:
    """Obtiene estadísticas de conversaciones de los últimos días"""
    try:
        stats = await conversation_logger.get_conversation_stats(days)
        
        if "error" in stats:
            return f"❌ {stats['error']}"
        
        result = f"""
📊 **Estadísticas de Conversaciones** (últimos {stats['period_days']} días)

📈 **Resumen:**
• Total de conversaciones: {stats['total_conversations']}
• Tiempo promedio de respuesta: {stats['avg_execution_time']}s

🔧 **Herramientas más usadas:**
"""
        
        if stats['most_used_tools']:
            for tool, count in stats['most_used_tools'].items():
                result += f"• {tool}: {count} veces\n"
        else:
            result += "• No hay datos de herramientas disponibles\n"
        
        return result.strip()
        
    except Exception as e:
        return f"❌ Error obteniendo estadísticas: {str(e)}"

async def startup():
    """Inicializar servicios al arrancar"""
    if settings.ENABLE_CONVERSATION_LOGGING:
        await conversation_logger.initialize()

async def shutdown():
    """Limpiar recursos al cerrar"""
    if conversation_logger.enabled and conversation_logger.pool:
        await conversation_logger.pool.close()

if __name__ == "__main__":
    # Inicializar servicios
    asyncio.run(startup())
    
    try:
        # Ejecutar servidor en modo HTTP para compatibilidad con el agente
        print("🚀 Iniciando servidor MCP en modo HTTP...")
        print(f"🌐 Servidor disponible en: http://localhost:8000/mcp")
        print("=" * 60)
        
        mcp.run(
            transport="streamable-http",
            host="127.0.0.1",
            port=8000,
            path="/mcp"
        )
    finally:
        # Limpiar al cerrar
        asyncio.run(shutdown()) 