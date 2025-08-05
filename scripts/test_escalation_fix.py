#!/usr/bin/env python3
"""
Script para probar que el escalamiento funciona correctamente
cuando el usuario pide hablar con alguien
"""

import asyncio
import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service
from services.embedding_service import embedding_service
from src.agent.hybrid_agent import HybridCustomerAgent

async def test_escalation_fix():
    """Probar diferentes formas de pedir ayuda humana"""
    
    try:
        # Inicializar servicios
        await db_service.initialize()
        await embedding_service.initialize()
        
        print("=" * 80)
        print("🧪 PRUEBA DE ESCALAMIENTO MEJORADO")
        print("=" * 80)
        
        # Diferentes formas de pedir ayuda
        test_messages = [
            "quiero hablar con alguien por que tengo un problema",
            "necesito hablar con una persona",
            "tengo un problema y necesito ayuda",
            "esto no funciona, quiero hablar con alguien",
            "dame el contacto de un humano"
        ]
        
        for i, message in enumerate(test_messages, 1):
            print(f"\n\n{'='*60}")
            print(f"PRUEBA {i}: {message}")
            print(f"{'='*60}")
            
            # Crear nuevo agente para cada prueba
            agent = HybridCustomerAgent()
            
            # Procesar mensaje
            response = await agent.process_message(
                message=message,
                user_id=f"test_user_{i}"
            )
            
            print(f"\n🤖 Eva:\n{response}")
            
            # Verificar que escaló correctamente
            if "wa.me" in response:
                print("\n✅ CORRECTO: Escaló apropiadamente")
            else:
                print("\n❌ ERROR: Debería haber escalado")
            
            # Verificar que no dice "dificultades técnicas"
            if "dificultades técnicas" in response:
                print("⚠️ ALERTA: Mostró mensaje de error técnico innecesario")
            
            await asyncio.sleep(0.5)
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await db_service.close()

if __name__ == "__main__":
    asyncio.run(test_escalation_fix())