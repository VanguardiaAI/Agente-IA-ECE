#!/usr/bin/env python3
"""
Script para probar el sistema de escalamiento a WhatsApp
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.whatsapp_utils import format_escalation_message, create_whatsapp_link
from src.agent.escalation_detector import escalation_detector

def test_whatsapp_links():
    """Probar generación de enlaces de WhatsApp"""
    print("=" * 80)
    print("🔗 PRUEBA DE ENLACES DE WHATSAPP")
    print("=" * 80)
    
    # Enlaces básicos
    print("\n1. Enlace básico sin mensaje:")
    link = create_whatsapp_link()
    print(f"   {link}")
    
    print("\n2. Enlace con mensaje predefinido:")
    link = create_whatsapp_link(message="Hola, necesito ayuda con un producto")
    print(f"   {link}")
    
    print("\n3. Enlace con caracteres especiales:")
    link = create_whatsapp_link(message="¿Cuál es el precio del ventilador Gavarrón V-25?")
    print(f"   {link}")

def test_escalation_messages():
    """Probar mensajes de escalamiento"""
    print("\n" + "=" * 80)
    print("💬 PRUEBA DE MENSAJES DE ESCALAMIENTO")
    print("=" * 80)
    
    test_cases = [
        ("product_not_found", {"product_search": "ventilador industrial 500W"}),
        ("technical_error", {"error": "Connection timeout"}),
        ("complaint", {"suggested_message": "Cliente molesto con el servicio"}),
        ("refund", None),
        ("urgent", None),
        ("human_requested", None)
    ]
    
    for reason, context in test_cases:
        print(f"\n📌 Caso: {reason}")
        print("-" * 40)
        message = format_escalation_message(reason=reason, context=context)
        print(message)
        print()

def test_escalation_detection():
    """Probar detección de escalamiento"""
    print("\n" + "=" * 80)
    print("🚨 PRUEBA DE DETECCIÓN DE ESCALAMIENTO")
    print("=" * 80)
    
    test_messages = [
        # Quejas
        "Este servicio es pésimo, quiero hacer una reclamación",
        "Estoy muy molesto, esto es inaceptable",
        
        # Devoluciones
        "Quiero devolver el producto y que me devuelvan mi dinero",
        "Necesito cancelar mi pedido urgentemente",
        
        # Garantía
        "El producto llegó roto, necesito la garantía",
        "No funciona, está defectuoso",
        
        # Pedidos especiales
        "Necesito 1000 unidades, ¿hay descuento por volumen?",
        "Quiero un presupuesto para pedido especial",
        
        # Soporte técnico
        "¿Cómo instalo esto? Necesito el manual técnico",
        "Necesito ayuda con la configuración",
        
        # Urgente
        "Es urgente, lo necesito hoy mismo",
        "EMERGENCIA! Necesito ayuda inmediata",
        
        # Frustración
        "No me ayudas en nada, quiero hablar con una persona real",
        "Prefiero hablar con un humano",
        
        # Normal (no debería escalar)
        "¿Cuál es el precio del ventilador?",
        "Buenos días",
        "Gracias por la información"
    ]
    
    for message in test_messages:
        should_escalate, reason, suggested = escalation_detector.should_escalate(
            message=message,
            session_id="test_session"
        )
        
        if should_escalate:
            print(f"\n🔴 ESCALAR: '{message[:50]}...'")
            print(f"   Razón: {reason}")
            if suggested:
                print(f"   Sugerencia: {suggested}")
        else:
            print(f"\n🟢 NO ESCALAR: '{message[:50]}...'")

def test_conversation_quality():
    """Probar análisis de calidad de conversación"""
    print("\n" + "=" * 80)
    print("📊 PRUEBA DE CALIDAD DE CONVERSACIÓN")
    print("=" * 80)
    
    # Conversación con problemas
    problematic_conversation = [
        {"role": "user", "content": "necesito el ventilador v25"},
        {"role": "assistant", "content": "No entiendo tu consulta"},
        {"role": "user", "content": "ventilador gabarron v-25"},
        {"role": "assistant", "content": "No tengo esa información"},
        {"role": "user", "content": "el ventilador gabarron!!!"},
    ]
    
    result = escalation_detector.analyze_conversation_quality(problematic_conversation)
    print("\nConversación problemática:")
    print(f"Calidad: {result['quality']}")
    print(f"¿Escalar?: {result.get('should_escalate', False)}")
    
    # Conversación normal
    normal_conversation = [
        {"role": "user", "content": "buenos días"},
        {"role": "assistant", "content": "¡Hola! ¿En qué puedo ayudarte?"},
        {"role": "user", "content": "precio del ventilador"},
        {"role": "assistant", "content": "El ventilador cuesta 206.31€"},
    ]
    
    result = escalation_detector.analyze_conversation_quality(normal_conversation)
    print("\nConversación normal:")
    print(f"Calidad: {result['quality']}")
    print(f"¿Escalar?: {result.get('should_escalate', False)}")

if __name__ == "__main__":
    test_whatsapp_links()
    test_escalation_messages()
    test_escalation_detection()
    test_conversation_quality()
    
    print("\n" + "=" * 80)
    print("✅ PRUEBAS COMPLETADAS")
    print("=" * 80)