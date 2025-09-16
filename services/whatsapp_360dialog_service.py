"""
Servicio para integración con WhatsApp Business API via 360Dialog
"""

import aiohttp
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from config.settings import settings

logger = logging.getLogger(__name__)


class MessageType(Enum):
    """Tipos de mensaje soportados por WhatsApp"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    TEMPLATE = "template"
    INTERACTIVE = "interactive"
    CONTACTS = "contacts"


class MessageStatus(Enum):
    """Estados de mensaje de WhatsApp"""
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"


@dataclass
class WhatsAppMessage:
    """Estructura de mensaje de WhatsApp"""
    to: str  # Número de teléfono del destinatario
    type: MessageType
    content: Dict[str, Any]
    reply_to: Optional[str] = None  # ID del mensaje al que responde
    preview_url: bool = True  # Habilitar preview de enlaces


class WhatsApp360DialogService:
    """
    Servicio para manejar la comunicación con WhatsApp Business API via 360Dialog
    """
    
    def __init__(self):
        self.api_key = getattr(settings, 'WHATSAPP_360DIALOG_API_KEY', None)
        self.api_url = getattr(settings, 'WHATSAPP_360DIALOG_API_URL', 'https://waba-v2.360dialog.io')
        self.phone_number = getattr(settings, 'WHATSAPP_PHONE_NUMBER', None)
        self.webhook_verify_token = getattr(settings, 'WHATSAPP_WEBHOOK_VERIFY_TOKEN', None)
        
        # Headers para la API
        self.headers = {
            "D360-API-KEY": self.api_key or "",
            "Content-Type": "application/json"
        }
        
        # Cache de plantillas aprobadas
        self._templates_cache = {}
        self._templates_cache_time = None
        
        if self.api_key and self.phone_number:
            logger.info(f"WhatsApp 360Dialog Service initialized for number: {self.phone_number}")
        else:
            logger.warning("WhatsApp 360Dialog Service initialized without complete configuration")
    
    async def send_message(self, message: WhatsAppMessage) -> Dict[str, Any]:
        """
        Envía un mensaje a través de WhatsApp
        
        Args:
            message: Objeto WhatsAppMessage con los datos del mensaje
            
        Returns:
            Respuesta de la API con el ID del mensaje enviado
        """
        endpoint = f"{self.api_url}/messages"
        
        # Construir el payload según el tipo de mensaje
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": message.to,
            "type": message.type.value
        }
        
        # Añadir contenido según el tipo
        if message.type == MessageType.TEXT:
            payload["text"] = {
                "preview_url": message.preview_url,
                "body": message.content.get("body", "")
            }
        
        elif message.type == MessageType.IMAGE:
            payload["image"] = {
                "link": message.content.get("link"),
                "caption": message.content.get("caption", "")
            }
        
        elif message.type == MessageType.DOCUMENT:
            payload["document"] = {
                "link": message.content.get("link"),
                "caption": message.content.get("caption", ""),
                "filename": message.content.get("filename", "document.pdf")
            }
        
        elif message.type == MessageType.TEMPLATE:
            payload["template"] = message.content
        
        elif message.type == MessageType.INTERACTIVE:
            payload["interactive"] = message.content
        
        # Añadir contexto de respuesta si existe
        if message.reply_to:
            payload["context"] = {
                "message_id": message.reply_to
            }
        
        # DEBUG: Imprimir payload completo para templates
        if message.type == MessageType.TEMPLATE:
            logger.info(f"DEBUG - Sending template: {payload.get('template', {}).get('name', 'unknown')}")
            logger.info(f"DEBUG - Full payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=self.headers, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Message sent successfully to {message.to}: {result.get('messages', [{}])[0].get('id')}")
                        return result
                    else:
                        logger.error(f"Failed to send message: {result}")
                        logger.error(f"DEBUG - Payload that failed: {json.dumps(payload, indent=2, ensure_ascii=False)}")
                        raise Exception(f"WhatsApp API error: {result.get('error', {}).get('message', 'Unknown error')}")
        
        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {str(e)}")
            if message.type == MessageType.TEMPLATE:
                logger.error(f"DEBUG - Template name was: {payload.get('template', {}).get('name', 'unknown')}")
            raise
    
    async def send_text_message(self, to: str, text: str, reply_to: Optional[str] = None) -> Dict[str, Any]:
        """
        Método conveniente para enviar mensajes de texto
        
        Args:
            to: Número de teléfono del destinatario
            text: Texto del mensaje
            reply_to: ID del mensaje al que responde (opcional)
            
        Returns:
            Respuesta de la API
        """
        message = WhatsAppMessage(
            to=to,
            type=MessageType.TEXT,
            content={"body": text},
            reply_to=reply_to
        )
        return await self.send_message(message)
    
    async def send_template_message(self, to: str, template_name: str, 
                                  language_code: str = "es", 
                                  components: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Envía un mensaje de plantilla aprobada
        
        Args:
            to: Número de teléfono del destinatario
            template_name: Nombre de la plantilla aprobada
            language_code: Código de idioma (default: es)
            components: Componentes de la plantilla (header, body, buttons)
            
        Returns:
            Respuesta de la API
        """
        template_content = {
            "name": template_name,
            "language": {"code": language_code}
        }
        
        if components:
            template_content["components"] = components
        
        message = WhatsAppMessage(
            to=to,
            type=MessageType.TEMPLATE,
            content=template_content
        )
        return await self.send_message(message)
    
    async def send_interactive_message(self, to: str, interactive_type: str = None, 
                                     body: str = None, header: Optional[str] = None,
                                     footer: Optional[str] = None,
                                     action: Optional[Dict] = None,
                                     interactive_content: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Envía un mensaje interactivo (botones, listas, etc.)
        
        Args:
            to: Número de teléfono del destinatario
            interactive_type: Tipo de interacción (button, list, etc.)
            body: Texto principal del mensaje
            header: Encabezado opcional
            footer: Pie de página opcional
            action: Configuración de la acción (botones, elementos de lista, etc.)
            interactive_content: Contenido interactivo completo (alternativa)
            
        Returns:
            Respuesta de la API
        """
        # Si se proporciona contenido interactivo completo, usarlo
        if interactive_content:
            content = interactive_content
        else:
            # Construir contenido desde parámetros individuales
            content = {
                "type": interactive_type,
                "body": {"text": body}
            }
            
            if header:
                content["header"] = {"type": "text", "text": header}
            
            if footer:
                content["footer"] = {"text": footer}
            
            if action:
                content["action"] = action
        
        message = WhatsAppMessage(
            to=to,
            type=MessageType.INTERACTIVE,
            content=content
        )
        return await self.send_message(message)
    
    async def send_product_carousel(self, to: str, products: List[Dict[str, Any]], 
                                  header: str = "Productos recomendados") -> Dict[str, Any]:
        """
        Envía un carrusel de productos usando mensajes interactivos
        
        Args:
            to: Número de teléfono del destinatario
            products: Lista de productos con título, descripción, precio
            header: Encabezado del mensaje
            
        Returns:
            Respuesta de la API
        """
        # WhatsApp tiene límites en el número de elementos
        products = products[:10]  # Máximo 10 elementos en una lista
        
        sections = [{
            "title": "Productos",
            "rows": [
                {
                    "id": f"product_{i}",
                    "title": product.get("name", "")[:24],  # Límite de 24 caracteres
                    "description": f"{product.get('price', '')} - {product.get('description', '')[:72]}"  # Límite de 72 caracteres
                }
                for i, product in enumerate(products)
            ]
        }]
        
        action = {
            "button": "Ver opciones",
            "sections": sections
        }
        
        return await self.send_interactive_message(
            to=to,
            interactive_type="list",
            body="Estos son los productos que podrían interesarte:",
            header=header,
            footer="Selecciona un producto para más información",
            action=action
        )
    
    async def mark_as_read(self, message_id: str) -> Dict[str, Any]:
        """
        Marca un mensaje como leído
        
        Args:
            message_id: ID del mensaje a marcar como leído
            
        Returns:
            Respuesta de la API
        """
        endpoint = f"{self.api_url}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(endpoint, headers=self.headers, json=payload) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        logger.info(f"Message {message_id} marked as read")
                        return result
                    else:
                        logger.error(f"Failed to mark message as read: {result}")
                        return result
        
        except Exception as e:
            logger.error(f"Error marking message as read: {str(e)}")
            raise
    
    async def get_media_url(self, media_id: str) -> str:
        """
        Obtiene la URL de un archivo multimedia
        
        Args:
            media_id: ID del archivo multimedia
            
        Returns:
            URL del archivo
        """
        endpoint = f"{self.api_url}/media/{media_id}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=self.headers) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        return result.get("url", "")
                    else:
                        logger.error(f"Failed to get media URL: {result}")
                        return ""
        
        except Exception as e:
            logger.error(f"Error getting media URL: {str(e)}")
            return ""
    
    async def download_media(self, media_url: str) -> bytes:
        """
        Descarga un archivo multimedia
        
        Args:
            media_url: URL del archivo multimedia
            
        Returns:
            Contenido del archivo en bytes
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(media_url, headers=self.headers) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        logger.error(f"Failed to download media: {response.status}")
                        return b""
        
        except Exception as e:
            logger.error(f"Error downloading media: {str(e)}")
            return b""
    
    async def get_templates(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de plantillas aprobadas
        
        Args:
            force_refresh: Forzar actualización del cache
            
        Returns:
            Lista de plantillas disponibles
        """
        # Verificar cache
        if not force_refresh and self._templates_cache_time:
            if datetime.now() - self._templates_cache_time < timedelta(hours=1):
                return self._templates_cache
        
        endpoint = f"{self.api_url}/configs/templates"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, headers=self.headers) as response:
                    result = await response.json()
                    
                    if response.status == 200:
                        templates = result.get("waba_templates", [])
                        # Actualizar cache
                        self._templates_cache = templates
                        self._templates_cache_time = datetime.now()
                        logger.info(f"Retrieved {len(templates)} templates")
                        return templates
                    else:
                        logger.error(f"Failed to get templates: {result}")
                        return []
        
        except Exception as e:
            logger.error(f"Error getting templates: {str(e)}")
            return []
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Union[str, bool]:
        """
        Verifica el webhook de 360Dialog
        
        Args:
            mode: Modo de verificación (debe ser "subscribe")
            token: Token de verificación
            challenge: Challenge string a devolver
            
        Returns:
            Challenge string si es válido, False si no
        """
        if not self.webhook_verify_token:
            logger.warning("Webhook verify token not configured")
            return False
            
        if mode == "subscribe" and token == self.webhook_verify_token:
            logger.info("Webhook verified successfully")
            return challenge
        else:
            logger.warning("Invalid webhook verification attempt")
            return False
    
    def format_phone_number(self, phone: str) -> str:
        """
        Formatea un número de teléfono para WhatsApp
        
        Args:
            phone: Número de teléfono
            
        Returns:
            Número formateado (sin + ni espacios)
        """
        # Eliminar caracteres no numéricos
        phone = ''.join(filter(str.isdigit, phone))
        
        # Si no empieza con código de país, asumir España (34)
        if not phone.startswith('34') and len(phone) == 9:
            phone = '34' + phone
        
        return phone


# Instancia singleton del servicio
whatsapp_service = WhatsApp360DialogService()