# Comportamiento de Escalamiento - Eva Assistant

## Resumen
El sistema de escalamiento ha sido optimizado para evitar mensajes de error técnico innecesarios y proporcionar una transición fluida hacia agentes humanos cuando es necesario.

## Mejoras Implementadas

### 1. **Sin Mensajes de Error Técnico**
- Eliminados mensajes como "estoy teniendo dificultades técnicas"
- Transición directa a escalamiento cuando se detecta necesidad
- Mensajes claros y profesionales

### 2. **Detección Mejorada**
El sistema escala automáticamente cuando detecta:

#### Solicitudes Explícitas de Humano:
- "quiero hablar con alguien"
- "necesito hablar con una persona"
- "dame el contacto de un humano"
- "prefiero una persona real"
- "quiero hablar con un agente"

#### Problemas Específicos:
- "esto no funciona" + solicitud de ayuda
- Reclamaciones o quejas
- Solicitudes de devolución
- Problemas de garantía con productos defectuosos

#### Frustración Detectada:
- Múltiples intentos sin éxito
- Expresiones de frustración
- "no me ayudas", "no sirves"

### 3. **Comportamiento Inteligente**

#### SÍ Escala Inmediatamente:
```
Usuario: "quiero hablar con alguien por que tengo un problema"
Eva: "Por supuesto. 
💬 *Un especialista te atenderá personalmente*
👉 https://wa.me/34614218122?text=El%20cliente%20solicita%20atención%20humana"
```

#### NO Escala (Intenta Ayudar Primero):
```
Usuario: "tengo un problema y necesito ayuda"
Eva: "¡Hola! Soy Eva, encantada de ayudarte. ¿Podrías contarme qué problema tienes?"
```

### 4. **Mensajes de Escalamiento Contextuales**

Cada tipo de escalamiento tiene un mensaje apropiado:

- **Solicitud humana**: "Por supuesto."
- **Frustración**: "Lamento no poder ayudarte como esperabas."
- **Problema técnico**: "Tu consulta requiere atención personalizada."
- **Garantía/Devolución**: "Para gestionar [tipo]."

### 5. **Enlaces de WhatsApp Inteligentes**

Los enlaces incluyen contexto predefinido:
- Solicitud de humano → "El cliente solicita atención humana"
- Problema específico → Incluye detalles del problema
- Urgente → "Consulta URGENTE que necesita atención inmediata"

## Flujo de Decisión

```
Mensaje del Usuario
    ↓
¿Solicita explícitamente un humano?
    SÍ → Escalar inmediatamente
    NO ↓
¿Tiene palabras clave de problemas graves?
    SÍ → Escalar con contexto
    NO ↓
¿Es ambiguo pero menciona problema?
    SÍ → Intentar ayudar primero
    NO ↓
Procesar normalmente
```

## Casos de Uso

### ✅ Escalamiento Inmediato
- "quiero hablar con una persona"
- "no funciona, necesito un humano"
- "dame el contacto de soporte"

### 🤔 Intenta Ayudar Primero
- "tengo un problema"
- "necesito ayuda"
- "no sé qué hacer"

### ❌ No Escala
- Búsquedas de productos normales
- Preguntas sobre información
- Consultas generales

## Configuración

El comportamiento se controla en:
- `/src/agent/escalation_detector.py` - Patrones de detección
- `/src/agent/hybrid_agent.py` - Lógica de procesamiento
- `/src/utils/whatsapp_utils.py` - Formato de mensajes

## Métricas de Éxito

1. **Reducción de escalamientos innecesarios**: Solo escala cuando realmente se necesita
2. **Eliminación de mensajes de error**: No más "dificultades técnicas"
3. **Transición fluida**: Enlaces directos de WhatsApp con contexto
4. **Satisfacción del usuario**: Respuesta apropiada a cada situación