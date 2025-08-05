"""
Handler para webhooks de WhatsApp via 360Dialog
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

from services.whatsapp_360dialog_service import whatsapp_service
from services.database import db_service
from config.settings import settings

logger = logging.getLogger(__name__)


class WebhookEventType(Enum):
    """Tipos de eventos de webhook"""
    MESSAGE = "message"
    STATUS = "status"
    ERROR = "error"
    NOTIFICATION = "notification"


class MessageType(Enum):
    """Tipos de mensaje recibidos"""
    TEXT = "text"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    CONTACTS = "contacts"
    INTERACTIVE = "interactive"
    BUTTON_REPLY = "button"
    LIST_REPLY = "list_reply"
    REACTION = "reaction"
    UNKNOWN = "unknown"


@dataclass
class WhatsAppUser:
    """Información del usuario de WhatsApp"""
    phone_number: str
    name: Optional[str] = None
    profile_picture: Optional[str] = None


@dataclass
class WhatsAppMessage:
    """Estructura de mensaje recibido de WhatsApp"""
    id: str
    from_number: str
    type: MessageType
    timestamp: datetime
    content: Dict[str, Any]
    context: Optional[Dict[str, Any]] = None  # Para respuestas a mensajes anteriores
    user: Optional[WhatsAppUser] = None


class WhatsAppWebhookHandler:
    """
    Maneja los webhooks entrantes de WhatsApp 360Dialog
    """
    
    def __init__(self):
        self.db_service = db_service
        self.active_sessions = {}  # Sesiones activas por número de teléfono
        logger.info("WhatsApp Webhook Handler initialized")
    
    async def process_webhook(self, webhook_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Procesa un webhook entrante de 360Dialog
        
        Args:
            webhook_data: Datos del webhook
            
        Returns:
            Respuesta para el webhook
        """
        try:
            # 360Dialog envía los datos en el campo 'entry'
            entries = webhook_data.get("entry", [])
            
            for entry in entries:
                changes = entry.get("changes", [])
                
                for change in changes:
                    value = change.get("value", {})
                    
                    # Procesar mensajes
                    if "messages" in value:
                        for message_data in value["messages"]:
                            await self._process_message(message_data, value)
                    
                    # Procesar actualizaciones de estado
                    if "statuses" in value:
                        for status_data in value["statuses"]:
                            await self._process_status_update(status_data)
                    
                    # Procesar errores
                    if "errors" in value:
                        for error_data in value["errors"]:
                            await self._process_error(error_data)
            
            return {"status": "success"}
        
        except Exception as e:
            logger.error(f"Error processing webhook: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def _process_message(self, message_data: Dict[str, Any], 
                             value_data: Dict[str, Any]) -> None:
        """
        Procesa un mensaje individual
        
        Args:
            message_data: Datos del mensaje
            value_data: Datos adicionales del webhook
        """
        try:
            # Extraer información del mensaje
            message = self._parse_message(message_data, value_data)
            
            # Marcar mensaje como leído
            await whatsapp_service.mark_as_read(message.id)
            
            # Obtener o crear sesión del usuario
            session = await self._get_or_create_session(message.from_number)
            
            # Registrar el mensaje en la base de datos
            await self._log_message(message, session)
            
            # Emitir evento para procesamiento por el agente
            await self._emit_message_event(message, session)
            
            logger.info(f"Message processed: {message.id} from {message.from_number}")
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
    
    def _parse_message(self, message_data: Dict[str, Any], 
                      value_data: Dict[str, Any]) -> WhatsAppMessage:
        """
        Parsea los datos del mensaje a la estructura interna
        
        Args:
            message_data: Datos del mensaje del webhook
            value_data: Datos adicionales
            
        Returns:
            Objeto WhatsAppMessage
        """
        # Información básica
        message_id = message_data["id"]
        from_number = message_data["from"]
        timestamp = datetime.fromtimestamp(int(message_data["timestamp"]))
        message_type = MessageType(message_data.get("type", "unknown"))
        
        # Contexto (si es respuesta a otro mensaje)
        context = message_data.get("context")
        
        # Información del usuario
        contacts = value_data.get("contacts", [])
        user = None
        if contacts:
            contact = contacts[0]
            user = WhatsAppUser(
                phone_number=from_number,
                name=contact.get("profile", {}).get("name"),
                profile_picture=None
            )
        
        # Contenido según el tipo de mensaje
        content = {}
        
        if message_type == MessageType.TEXT:
            content = {
                "text": message_data.get("text", {}).get("body", "")
            }
        
        elif message_type == MessageType.IMAGE:
            image_data = message_data.get("image", {})
            content = {
                "media_id": image_data.get("id"),
                "caption": image_data.get("caption", ""),
                "mime_type": image_data.get("mime_type")
            }
        
        elif message_type == MessageType.DOCUMENT:
            doc_data = message_data.get("document", {})
            content = {
                "media_id": doc_data.get("id"),
                "filename": doc_data.get("filename"),
                "caption": doc_data.get("caption", ""),
                "mime_type": doc_data.get("mime_type")
            }
        
        elif message_type == MessageType.AUDIO:
            audio_data = message_data.get("audio", {})
            content = {
                "media_id": audio_data.get("id"),
                "mime_type": audio_data.get("mime_type")
            }
        
        elif message_type == MessageType.VIDEO:
            video_data = message_data.get("video", {})
            content = {
                "media_id": video_data.get("id"),
                "caption": video_data.get("caption", ""),
                "mime_type": video_data.get("mime_type")
            }
        
        elif message_type == MessageType.LOCATION:
            location_data = message_data.get("location", {})
            content = {
                "latitude": location_data.get("latitude"),
                "longitude": location_data.get("longitude"),
                "name": location_data.get("name"),
                "address": location_data.get("address")
            }
        
        elif message_type == MessageType.INTERACTIVE:
            interactive_data = message_data.get("interactive", {})
            content = {
                "type": interactive_data.get("type"),
                "button_reply": interactive_data.get("button_reply"),
                "list_reply": interactive_data.get("list_reply")
            }
        
        elif message_type == MessageType.BUTTON_REPLY:
            button_data = message_data.get("button", {})
            content = {
                "payload": button_data.get("payload"),
                "text": button_data.get("text")
            }
        
        return WhatsAppMessage(
            id=message_id,
            from_number=from_number,
            type=message_type,
            timestamp=timestamp,
            content=content,
            context=context,
            user=user
        )
    
    async def _process_status_update(self, status_data: Dict[str, Any]) -> None:
        """
        Procesa una actualización de estado de mensaje
        
        Args:
            status_data: Datos del estado
        """
        try:
            message_id = status_data.get("id")
            status = status_data.get("status")  # sent, delivered, read, failed
            timestamp = datetime.fromtimestamp(int(status_data.get("timestamp")))
            recipient = status_data.get("recipient_id")
            
            # Actualizar estado en base de datos si es necesario
            logger.info(f"Status update: {message_id} - {status} for {recipient}")
            
            # Aquí podrías actualizar el estado en la base de datos
            # o emitir un evento para notificar al frontend
            
        except Exception as e:
            logger.error(f"Error processing status update: {str(e)}")
    
    async def _process_error(self, error_data: Dict[str, Any]) -> None:
        """
        Procesa un error reportado por WhatsApp
        
        Args:
            error_data: Datos del error
        """
        try:
            error_code = error_data.get("code")
            error_title = error_data.get("title")
            error_message = error_data.get("message")
            error_details = error_data.get("error_data", {})
            
            logger.error(f"WhatsApp error: [{error_code}] {error_title} - {error_message}")
            logger.error(f"Error details: {error_details}")
            
            # Aquí podrías implementar lógica específica según el tipo de error
            # Por ejemplo, reintentar envío, notificar al administrador, etc.
            
        except Exception as e:
            logger.error(f"Error processing error webhook: {str(e)}")
    
    async def _get_or_create_session(self, phone_number: str) -> Dict[str, Any]:
        """
        Obtiene o crea una sesión para el usuario
        
        Args:
            phone_number: Número de teléfono del usuario
            
        Returns:
            Datos de la sesión
        """
        if phone_number not in self.active_sessions:
            # Crear nueva sesión
            session = {
                "phone_number": phone_number,
                "session_id": f"wa_{phone_number}_{datetime.now().timestamp()}",
                "started_at": datetime.now(),
                "last_activity": datetime.now(),
                "platform": "whatsapp",
                "context": {}
            }
            self.active_sessions[phone_number] = session
        else:
            # Actualizar última actividad
            self.active_sessions[phone_number]["last_activity"] = datetime.now()
        
        return self.active_sessions[phone_number]
    
    async def _log_message(self, message: WhatsAppMessage, session: Dict[str, Any]) -> None:
        """
        Registra el mensaje en la base de datos
        
        Args:
            message: Mensaje a registrar
            session: Sesión del usuario
        """
        try:
            # Preparar datos para guardar
            message_data = {
                "session_id": session["session_id"],
                "platform": "whatsapp",
                "user_id": message.from_number,
                "message_id": message.id,
                "message_type": message.type.value,
                "content": message.content,
                "timestamp": message.timestamp,
                "direction": "inbound",
                "metadata": {
                    "context": message.context,
                    "user_name": message.user.name if message.user else None
                }
            }
            
            # Aquí deberías implementar el guardado en la base de datos
            # usando el servicio de PostgreSQL
            
        except Exception as e:
            logger.error(f"Error logging message: {str(e)}")
    
    async def _emit_message_event(self, message: WhatsAppMessage, session: Dict[str, Any]) -> None:
        """
        Emite un evento para que el mensaje sea procesado por el agente
        
        Args:
            message: Mensaje a procesar
            session: Sesión del usuario
        """
        try:
            # Preparar evento
            event = {
                "type": "whatsapp_message",
                "session": session,
                "message": {
                    "id": message.id,
                    "from": message.from_number,
                    "type": message.type.value,
                    "content": message.content,
                    "timestamp": message.timestamp.isoformat(),
                    "context": message.context
                }
            }
            
            # Aquí deberías emitir el evento al sistema de procesamiento
            # Por ejemplo, usando un queue, WebSocket, o llamada directa al agente
            logger.info(f"Message event emitted for processing: {event}")
            
        except Exception as e:
            logger.error(f"Error emitting message event: {str(e)}")
    
    def verify_webhook(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """
        Verifica el webhook durante el registro en 360Dialog
        
        Args:
            mode: Modo de verificación
            token: Token de verificación
            challenge: Challenge a devolver
            
        Returns:
            Challenge si es válido, None si no
        """
        return whatsapp_service.verify_webhook(mode, token, challenge)
    
    async def cleanup_inactive_sessions(self, timeout_minutes: int = 30) -> None:
        """
        Limpia sesiones inactivas
        
        Args:
            timeout_minutes: Minutos de inactividad para considerar timeout
        """
        current_time = datetime.now()
        sessions_to_remove = []
        
        for phone, session in self.active_sessions.items():
            last_activity = session["last_activity"]
            if (current_time - last_activity).total_seconds() > timeout_minutes * 60:
                sessions_to_remove.append(phone)
        
        for phone in sessions_to_remove:
            del self.active_sessions[phone]
            logger.info(f"Session cleaned up for {phone}")


# Instancia singleton del handler
whatsapp_webhook_handler = WhatsAppWebhookHandler()