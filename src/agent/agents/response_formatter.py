#!/usr/bin/env python3
"""
Response Formatter Agent
Formatea las respuestas finales según la plataforma y contexto
"""

import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from services.gpt5_client import GPT5Client, ReasoningEffort, Verbosity
from src.utils.whatsapp_product_formatter import format_products_for_whatsapp

logger = logging.getLogger(__name__)


@dataclass
class FormattedResponse:
    """Respuesta formateada"""
    content: str  # Contenido principal
    platform_specific: Dict[str, Any] = None  # Datos específicos de plataforma
    includes_products: bool = False
    total_products: int = 0
    message_type: str = "text"  # text, products, mixed


class ResponseFormatterAgent:
    """Agente para formatear respuestas finales"""
    
    def __init__(self):
        self.gpt5 = GPT5Client()
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configuración por plataforma
        self.platform_config = {
            "whatsapp": {
                "max_products": 5,
                "use_emojis": True,
                "format": "simple"
            },
            "wordpress": {
                "max_products": 10,
                "use_emojis": False,
                "format": "rich"
            }
        }
    
    async def format_response(
        self,
        intent_type: str,
        content: Any,
        platform: str = "wordpress",
        context: Optional[Dict] = None
    ) -> FormattedResponse:
        """
        Formatea la respuesta según el tipo de contenido y plataforma
        
        Args:
            intent_type: Tipo de intención (product_search, technical_info, etc.)
            content: Contenido a formatear (productos, texto, etc.)
            platform: Plataforma destino
            context: Contexto adicional
            
        Returns:
            FormattedResponse formateada
        """
        
        if intent_type == "product_search":
            return await self._format_product_search_response(content, platform, context)
        elif intent_type == "technical_info":
            return await self._format_technical_response(content, platform)
        elif intent_type == "order_inquiry":
            return await self._format_order_response(content, platform)
        elif intent_type == "greeting":
            return await self._format_greeting_response(platform)
        else:
            return await self._format_general_response(content, platform)
    
    async def _format_product_search_response(
        self,
        validation_result: Dict,
        platform: str,
        context: Optional[Dict] = None
    ) -> FormattedResponse:
        """Formatea respuesta de búsqueda de productos"""
        
        products = validation_result.get("relevant_products", [])
        user_query = context.get("user_query", "productos") if context else "productos"
        
        if not products:
            # Sin productos encontrados
            no_products_prompt = f"""El cliente buscó "{user_query}" pero no se encontraron productos.

Genera una respuesta amable y útil que:
1. Reconozca que no se encontraron productos
2. Sugiera alternativas o términos de búsqueda diferentes
3. Ofrezca ayuda adicional
4. Sea breve y profesional

Plataforma: {platform}
{"Usa emojis apropiados" if platform == "whatsapp" else "No uses emojis"}"""

            response = await self.gpt5.create_response(
                input_text=no_products_prompt,
                model="gpt-5-mini",
                reasoning_effort=ReasoningEffort.LOW,
                verbosity=Verbosity.LOW
            )
            
            return FormattedResponse(
                content=response.content,
                includes_products=False,
                message_type="text"
            )
        
        # Con productos encontrados
        config = self.platform_config.get(platform, self.platform_config["wordpress"])
        max_products = config["max_products"]
        
        if platform == "whatsapp":
            # Formato WhatsApp
            formatted_content = format_products_for_whatsapp(products[:max_products])
            
            # Agregar mensaje introductorio
            intro = f"He encontrado {len(products)} productos que coinciden con tu búsqueda"
            if len(products) > max_products:
                intro += f" (mostrando los {max_products} más relevantes)"
            intro += ":\n\n"
            
            return FormattedResponse(
                content=intro + formatted_content,
                includes_products=True,
                total_products=len(products),
                message_type="products"
            )
        
        else:
            # Formato WordPress/Web
            formatted_html = self._format_products_html(products[:max_products])
            
            intro = f"<p>He encontrado <strong>{len(products)} productos</strong> para tu búsqueda"
            if len(products) > max_products:
                intro += f" (mostrando los {max_products} más relevantes)"
            intro += ":</p>\n\n"
            
            return FormattedResponse(
                content=intro + formatted_html,
                includes_products=True,
                total_products=len(products),
                message_type="products",
                platform_specific={"format": "html"}
            )
    
    async def _format_technical_response(self, content: str, platform: str) -> FormattedResponse:
        """Formatea respuesta técnica"""
        
        format_prompt = f"""Formatea esta respuesta técnica para que sea clara y profesional:

{content}

Plataforma: {platform}
{"Puedes usar emojis técnicos apropiados (⚡🔧📏)" if platform == "whatsapp" else "No uses emojis"}

Mantén la información técnica precisa pero hazla accesible."""

        response = await self.gpt5.create_response(
            input_text=format_prompt,
            model="gpt-5-mini",
            reasoning_effort=ReasoningEffort.LOW,
            verbosity=Verbosity.MEDIUM
        )
        
        return FormattedResponse(
            content=response.content,
            message_type="text"
        )
    
    async def _format_order_response(self, content: str, platform: str) -> FormattedResponse:
        """Formatea respuesta sobre pedidos"""
        
        # Las respuestas de pedidos ya vienen formateadas del sistema
        return FormattedResponse(
            content=content,
            message_type="text"
        )
    
    async def _format_greeting_response(self, platform: str) -> FormattedResponse:
        """Formatea saludo"""
        
        greetings = {
            "whatsapp": "¡Hola! 👋 Soy Eva, tu asistente de El Corte Eléctrico. ¿En qué puedo ayudarte hoy?",
            "wordpress": "Hola! Soy Eva, tu asistente virtual de El Corte Eléctrico. ¿En qué puedo ayudarte?"
        }
        
        return FormattedResponse(
            content=greetings.get(platform, greetings["wordpress"]),
            message_type="text"
        )
    
    async def _format_general_response(self, content: str, platform: str) -> FormattedResponse:
        """Formatea respuesta general"""
        
        # Si ya es string, devolver tal cual
        if isinstance(content, str):
            return FormattedResponse(
                content=content,
                message_type="text"
            )
        
        # Si es otro tipo, convertir a string
        return FormattedResponse(
            content=str(content),
            message_type="text"
        )
    
    def _format_products_html(self, products: List[Dict]) -> str:
        """Formatea productos en HTML para web"""
        
        html_parts = ['<div class="products-grid">']
        
        for product in products:
            name = product.get("title", product.get("name", "Sin nombre"))
            metadata = product.get("metadata", {})
            price = metadata.get("price", "Consultar precio")
            image = metadata.get("images", [{}])[0].get("src", "") if metadata.get("images") else ""
            link = metadata.get("permalink", "#")
            in_stock = metadata.get("stock_status") == "instock"
            sku = metadata.get("sku", "")
            
            # Extraer especificaciones de la descripción corta
            short_desc = metadata.get("short_description", "")
            if short_desc:
                # Limpiar HTML básico
                import re
                short_desc = re.sub('<[^<]+?>', '', short_desc)[:150] + "..."
            
            html_parts.append(f'''
<div class="product-item">
    <div class="product-image">
        {f'<img src="{image}" alt="{name}" />' if image else '<div class="no-image">Sin imagen</div>'}
    </div>
    <div class="product-info">
        <h3><a href="{link}" target="_blank">{name}</a></h3>
        <p class="product-sku">SKU: {sku}</p>
        <p class="product-desc">{short_desc}</p>
        <div class="product-footer">
            <span class="product-price">{price}</span>
            <span class="product-stock {'in-stock' if in_stock else 'out-stock'}">
                {'✓ En stock' if in_stock else 'Consultar disponibilidad'}
            </span>
        </div>
    </div>
</div>''')
        
        html_parts.append('</div>')
        
        # Agregar CSS inline básico
        style = '''
<style>
.products-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
    margin: 20px 0;
}
.product-item {
    border: 1px solid #ddd;
    border-radius: 8px;
    padding: 15px;
    background: #fff;
    transition: box-shadow 0.3s;
}
.product-item:hover {
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}
.product-image {
    text-align: center;
    margin-bottom: 10px;
    height: 150px;
    display: flex;
    align-items: center;
    justify-content: center;
}
.product-image img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
}
.no-image {
    color: #999;
    font-style: italic;
}
.product-info h3 {
    margin: 10px 0;
    font-size: 16px;
}
.product-info h3 a {
    color: #333;
    text-decoration: none;
}
.product-info h3 a:hover {
    color: #0066cc;
}
.product-sku {
    color: #666;
    font-size: 12px;
    margin: 5px 0;
}
.product-desc {
    font-size: 14px;
    color: #555;
    margin: 10px 0;
}
.product-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 15px;
}
.product-price {
    font-size: 18px;
    font-weight: bold;
    color: #0066cc;
}
.product-stock {
    font-size: 12px;
    padding: 4px 8px;
    border-radius: 4px;
}
.in-stock {
    background: #e8f5e9;
    color: #2e7d32;
}
.out-stock {
    background: #fff3e0;
    color: #e65100;
}
</style>'''
        
        return style + '\n'.join(html_parts)
    
    def add_clarification_request(
        self,
        formatted_response: FormattedResponse,
        clarification_questions: List[str],
        platform: str
    ) -> FormattedResponse:
        """
        Agrega preguntas de clarificación a la respuesta
        
        Args:
            formatted_response: Respuesta base
            clarification_questions: Preguntas a agregar
            platform: Plataforma destino
            
        Returns:
            Respuesta con clarificación agregada
        """
        
        if not clarification_questions:
            return formatted_response
        
        # Formato según plataforma
        if platform == "whatsapp":
            clarification = "\n\n❓ Para encontrar exactamente lo que buscas:\n"
            for i, question in enumerate(clarification_questions, 1):
                clarification += f"{i}. {question}\n"
        else:
            clarification = '\n\n<div class="clarification-box">'
            clarification += '<p><strong>Para encontrar exactamente lo que buscas:</strong></p><ul>'
            for question in clarification_questions:
                clarification += f'<li>{question}</li>'
            clarification += '</ul></div>'
        
        # Agregar a la respuesta
        formatted_response.content += clarification
        formatted_response.message_type = "mixed"
        
        return formatted_response


# Instancia singleton
response_formatter = ResponseFormatterAgent()