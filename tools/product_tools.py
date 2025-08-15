"""
Herramientas MCP para gestión de productos de WooCommerce
Integra búsqueda híbrida (semántica + texto) con base de conocimiento
"""

from typing import List, Dict, Any
from services.woocommerce import WooCommerceService
from services.database import db_service
from services.embedding_service import embedding_service

def register_product_tools(mcp):
    """Registrar herramientas relacionadas con productos"""
    
    @mcp.tool()
    async def search_products(query: str, limit: int = 10, use_hybrid: bool = True) -> str:
        """
        Buscar productos por nombre o descripción usando búsqueda híbrida (semántica + texto)
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
            use_hybrid: Si usar búsqueda híbrida (True) o búsqueda directa en WooCommerce (False)
        """
        try:
            if use_hybrid and await db_service.initialized:
                # Usar búsqueda híbrida en base de conocimiento
                return await _hybrid_product_search(query, limit)
            else:
                # Fallback a búsqueda directa en WooCommerce
                return await _direct_wc_search(query, limit)
                
        except Exception as e:
            return f"❌ Error al buscar productos: {str(e)}"
    
    @mcp.tool()
    async def get_product_details(product_id: int) -> str:
        """Obtener detalles completos de un producto específico"""
        try:
            wc_service = WooCommerceService()
            product = await wc_service.get_product(product_id)
            
            if not product:
                return f"❌ No se encontró el producto con ID: {product_id}"
            
            return wc_service.format_product(product)
            
        except Exception as e:
            return f"❌ Error al obtener producto: {str(e)}"
    
    @mcp.tool()
    async def check_product_stock(product_id: int) -> str:
        """Verificar disponibilidad de stock de un producto"""
        try:
            wc_service = WooCommerceService()
            product = await wc_service.get_product(product_id)
            
            if not product:
                return f"❌ No se encontró el producto con ID: {product_id}"
            
            name = product.get('name', 'Producto')
            stock_status = product.get('stock_status', 'outofstock')
            stock_quantity = product.get('stock_quantity', 0)
            
            if stock_status == 'instock':
                if stock_quantity:
                    return f"✅ **{name}** - En stock ({stock_quantity} disponibles)"
                else:
                    return f"✅ **{name}** - En stock"
            else:
                return f"❌ **{name}** - Sin stock disponible"
                
        except Exception as e:
            return f"❌ Error al verificar stock: {str(e)}"
    
    @mcp.tool()
    async def get_product_categories() -> str:
        """Obtener todas las categorías de productos disponibles"""
        try:
            wc_service = WooCommerceService()
            categories = await wc_service.get_product_categories()
            
            if not categories:
                return "❌ No se encontraron categorías"
            
            result = "📂 **Categorías de Productos**\n\n"
            
            for category in categories:
                name = category.get('name', 'Sin nombre')
                count = category.get('count', 0)
                result += f"• **{name}** ({count} productos)\n"
            
            return result
            
        except Exception as e:
            return f"❌ Error al obtener categorías: {str(e)}"
    
    @mcp.tool()
    async def get_products_by_category(category_name: str, limit: int = 10) -> str:
        """Obtener productos de una categoría específica"""
        try:
            wc_service = WooCommerceService()
            
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
            return f"❌ Error al obtener productos por categoría: {str(e)}"
    
    @mcp.tool()
    async def get_featured_products(limit: int = 10) -> str:
        """Obtener productos destacados"""
        try:
            wc_service = WooCommerceService()
            products = await wc_service.get_products(featured=True, per_page=limit)
            
            if not products:
                return "❌ No hay productos destacados disponibles"
            
            return wc_service.format_product_list(products, "Productos Destacados")
            
        except Exception as e:
            return f"❌ Error al obtener productos destacados: {str(e)}"
    
    @mcp.tool()
    async def get_products_on_sale(limit: int = 10) -> str:
        """Obtener productos en oferta"""
        try:
            wc_service = WooCommerceService()
            products = await wc_service.get_products(on_sale=True, per_page=limit)
            
            if not products:
                return "❌ No hay productos en oferta actualmente"
            
            return wc_service.format_product_list(products, "Productos en Oferta")
            
        except Exception as e:
            return f"❌ Error al obtener productos en oferta: {str(e)}"
    
    @mcp.tool()
    async def smart_product_recommendation(query: str, limit: int = 5) -> str:
        """
        Recomendar productos usando búsqueda semántica inteligente
        Ideal para consultas como 'necesito algo para iluminación exterior'
        """
        try:
            if not await db_service.initialized:
                return "❌ Base de conocimiento no disponible"
            
            # Generar embedding para la consulta
            embedding = await embedding_service.generate_embedding(query)
            
            # Búsqueda híbrida enfocada en productos
            results = await db_service.hybrid_search(
                query_text=query,
                query_embedding=embedding,
                content_types=["product"],
                limit=limit
            )
            
            if not results:
                return f"❌ No se encontraron recomendaciones para: '{query}'"
            
            response = f"🎯 **Recomendaciones para: '{query}'**\n\n"
            
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
                response += f"   📊 Relevancia: {rrf_score:.3f}\n\n"
            
            return response
            
        except Exception as e:
            return f"❌ Error en recomendación inteligente: {str(e)}"
    
    @mcp.tool()
    async def find_similar_products(product_id: int, limit: int = 5) -> str:
        """Encontrar productos similares usando búsqueda vectorial"""
        try:
            if not await db_service.initialized:
                return "❌ Base de conocimiento no disponible"
            
            # Obtener el producto base
            external_id = f"product_{product_id}"
            base_product = await db_service.get_knowledge_by_external_id(external_id)
            
            if not base_product:
                return f"❌ Producto {product_id} no encontrado en base de conocimiento"
            
            # Usar el embedding del producto base para buscar similares
            base_embedding = eval(base_product.get('embedding', '[]'))
            
            if not base_embedding:
                return f"❌ No hay embedding disponible para el producto {product_id}"
            
            # Búsqueda vectorial de productos similares
            similar_results = await db_service.vector_search(
                query_embedding=base_embedding,
                content_types=["product"],
                limit=limit + 1  # +1 porque incluirá el producto base
            )
            
            # Filtrar el producto base de los resultados
            similar_products = [r for r in similar_results if r.get('external_id') != external_id][:limit]
            
            if not similar_products:
                return f"❌ No se encontraron productos similares a {base_product.get('title', 'este producto')}"
            
            response = f"🔍 **Productos similares a: {base_product.get('title', 'Producto')}**\n\n"
            
            for i, product in enumerate(similar_products, 1):
                metadata = product.get('metadata', {})
                title = product.get('title', 'Producto')
                price = metadata.get('price', 0)
                stock_status = metadata.get('stock_status', 'unknown')
                similarity = product.get('similarity', 0)
                
                stock_icon = "✅" if stock_status == 'instock' else "❌"
                
                response += f"{i}. {stock_icon} **{title}**\n"
                if price > 0:
                    response += f"   💰 Precio: ${price}\n"
                response += f"   📊 Similitud: {similarity:.3f}\n\n"
            
            return response
            
        except Exception as e:
            return f"❌ Error buscando productos similares: {str(e)}"

# Funciones auxiliares
async def _hybrid_product_search(query: str, limit: int) -> str:
    """Realizar búsqueda inteligente combinando WooCommerce y búsqueda híbrida"""
    try:
        # Generar embedding para la consulta
        embedding = await embedding_service.generate_embedding(query)
        
        # Crear instancia de WooCommerce para la búsqueda inteligente
        from services.woocommerce import WooCommerceService
        wc_service = WooCommerceService()
        
        # Búsqueda inteligente que combina WooCommerce + híbrida
        results = await db_service.intelligent_product_search(
            query_text=query,
            query_embedding=embedding,
            content_types=["product"],
            limit=limit,
            wc_service=wc_service
        )
        
        if not results:
            return f"❌ No se encontraron productos para: '{query}'"
        
        response = f"🔍 **Resultados inteligentes para: '{query}'**\n\n"
        
        for i, result in enumerate(results, 1):
            metadata = result.get('metadata', {})
            title = result.get('title', 'Producto')
            price = metadata.get('price', 0)
            regular_price = metadata.get('regular_price', 0)
            sale_price = metadata.get('sale_price', 0)
            stock_status = metadata.get('stock_status', 'unknown')
            permalink = metadata.get('permalink', '')
            sku = metadata.get('sku', '')
            categories = metadata.get('categories', [])
            rrf_score = result.get('rrf_score', 0)
            source = result.get('source', 'unknown')
            match_type = result.get('match_type', 'unknown')
            
            # Icono según la fuente
            source_icon = "🎯" if source == "woocommerce" else "🔍"
            
            response += f"{source_icon} **{title}**\n"
            
            # Precio con formato de oferta
            if sale_price and sale_price > 0 and sale_price < regular_price:
                response += f"   💰 ~{regular_price}€~ **{sale_price}€** ¡OFERTA!\n"
            else:
                response += f"   💰 **{price}€** (IVA incluido)\n"
            
            # Estado del stock
            if stock_status == 'instock':
                response += "   ✅ Disponible\n"
            else:
                response += "   ❌ Sin stock\n"
            
            # Categorías
            if categories:
                cat_text = ', '.join(categories[:2])  # Máximo 2 categorías
                response += f"   🏷️ {cat_text}\n"
            
            # SKU
            if sku:
                response += f"   📋 Ref: {sku}\n"
            
            # Link del producto
            if permalink:
                response += f"   🔗 {permalink}\n"
            
            response += f"   📊 Relevancia: {rrf_score:.1f} ({source}/{match_type})\n\n"
        
        return response
        
    except Exception as e:
        return f"❌ Error en búsqueda híbrida: {str(e)}"

async def _direct_wc_search(query: str, limit: int) -> str:
    """Búsqueda directa en WooCommerce (fallback)"""
    try:
        wc_service = WooCommerceService()
        products = await wc_service.search_products(query, per_page=limit)
        
        if not products:
            return f"❌ No se encontraron productos para: '{query}'"
        
        return wc_service.format_product_list(products, f"Resultados directos para '{query}'")
        
    except Exception as e:
        return f"❌ Error en búsqueda directa: {str(e)}" 