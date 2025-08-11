"""
Utilidades para formateo y enlaces de WhatsApp
"""

from typing import Optional, Dict, Any
import urllib.parse

# Configuración del número de soporte
SUPPORT_PHONE = "34614218122"  # Sin + ni espacios
SUPPORT_PHONE_FORMATTED = "+34 614 21 81 22"

def create_whatsapp_link(phone: str = SUPPORT_PHONE, message: Optional[str] = None) -> str:
    """
    Crea un enlace de WhatsApp que abre directamente el chat
    
    Args:
        phone: Número de teléfono sin espacios ni símbolos
        message: Mensaje predefinido opcional
        
    Returns:
        URL de WhatsApp clickeable
    """
    base_url = f"https://wa.me/{phone}"
    
    if message:
        encoded_message = urllib.parse.quote(message)
        return f"{base_url}?text={encoded_message}"
    
    return base_url

def format_escalation_message(reason: str = "general", context: Optional[Dict[str, Any]] = None, platform: str = "whatsapp") -> str:
    """
    Formatea el mensaje de escalamiento según el contexto
    
    Args:
        reason: Razón del escalamiento (product_not_found, error, complex_query, etc.)
        context: Contexto adicional (producto buscado, error, etc.)
        platform: Plataforma de destino (whatsapp o wordpress)
        
    Returns:
        Mensaje formateado para escalamiento
    """
    # Mensajes base según la razón
    messages = {
        "product_not_found": "No encontré el producto que buscas",
        "order_help": "Para consultas sobre pedidos específicos",
        "technical_error": "Tuve un problema técnico al procesar tu consulta",
        "complex_query": "Tu consulta requiere atención personalizada",
        "stock_error": "No pude verificar la disponibilidad",
        "general": "No tengo esa información disponible",
        "complaint": "Entiendo tu situación",
        "refund": "Para gestionar devoluciones",
        "warranty": "Para temas de garantía",
        "custom_order": "Para pedidos especiales o al por mayor",
        "technical_support": "Para asistencia técnica especializada",
        "urgent": "Veo que es urgente",
        "frustrated": "Lamento no poder ayudarte como esperabas",
        "human_requested": "Por supuesto",
        "multiple_attempts": "Parece que estamos teniendo dificultades",
        "conversation_loop": "Necesitas ayuda más específica"
    }
    
    base_message = messages.get(reason, messages["general"])
    
    # Crear mensaje predefinido para WhatsApp basado en el contexto
    whatsapp_message = None
    if context:
        if context.get("suggested_message"):
            whatsapp_message = context["suggested_message"]
        elif context.get("product_search"):
            whatsapp_message = f"Hola, busco información sobre: {context['product_search']}"
        elif context.get("order_id"):
            whatsapp_message = f"Hola, necesito ayuda con el pedido #{context['order_id']}"
        elif reason == "technical_error":
            whatsapp_message = "Hola, el asistente tuvo un problema técnico. Necesito ayuda."
        elif reason == "urgent":
            whatsapp_message = "Hola, tengo una consulta URGENTE que necesita atención inmediata."
    
    # Si no hay mensaje específico, crear uno genérico
    if not whatsapp_message:
        whatsapp_message = "Hola, necesito ayuda con una consulta que el asistente no pudo resolver."
    
    # Crear enlace de WhatsApp
    wa_link = create_whatsapp_link(message=whatsapp_message)
    
    # Formatear mensaje completo según plataforma
    if platform == "wordpress":
        # Para WordPress, evitar asteriscos y usar formato simple
        escalation_msg = f"""
{base_message}.

💬 Un especialista te atenderá personalmente
👉 {wa_link}

Horario: Lunes a Viernes 9:00-18:00
"""
    else:
        # Para WhatsApp, usar formato con asteriscos
        escalation_msg = f"""
{base_message}. 

💬 *Un especialista te atenderá personalmente*
👉 {wa_link}

_Horario: Lunes a Viernes 9:00-18:00_
"""
    
    return escalation_msg.strip()

def should_escalate(query_type: str, error: Optional[Exception] = None, attempts: int = 0) -> bool:
    """
    Determina si una consulta debe ser escalada a un humano
    
    Args:
        query_type: Tipo de consulta
        error: Excepción si hubo error
        attempts: Número de intentos realizados
        
    Returns:
        True si debe escalar, False si no
    """
    # Escalar si hay múltiples errores
    if error and attempts >= 2:
        return True
    
    # Tipos de consulta que requieren escalamiento
    escalate_queries = [
        "complaint",
        "refund",
        "warranty_claim",
        "custom_order",
        "bulk_order",
        "technical_support",
        "installation_help"
    ]
    
    return query_type in escalate_queries

def format_product_help_footer(platform: str = "whatsapp") -> str:
    """
    Formatea el pie de mensaje para ayuda con productos
    
    Args:
        platform: Plataforma de destino (whatsapp o wordpress)
    
    Returns:
        Pie de mensaje con enlace de WhatsApp
    """
    wa_link = create_whatsapp_link(message="Hola, necesito ayuda con un producto")
    
    if platform == "wordpress":
        return f"""
💬 ¿Necesitas ayuda personalizada?
Chatea con un especialista: {wa_link}
"""
    else:
        return f"""
💬 *¿Necesitas ayuda personalizada?*
Chatea con un especialista: {wa_link}
"""