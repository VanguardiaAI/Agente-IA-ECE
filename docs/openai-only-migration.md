# Migración a OpenAI Exclusivo

## Resumen de Cambios

Se ha migrado el sistema para usar exclusivamente modelos de OpenAI, eliminando todas las dependencias de Anthropic/Claude.

### Configuración de Modelos

1. **Modelo Principal**: `gpt-5`
   - Usado para todas las respuestas principales del chatbot
   - Configurado en `env.agent` como `MODEL_NAME=gpt-5`
   - Costo: $2/millón tokens entrada, $8/millón tokens salida

2. **Modelo Rápido**: `gpt-5-mini`
   - Usado para respuestas rápidas y tareas simples
   - Configurado en `_initialize_quick_llm()` y `_initialize_cheap_llm()`
   - Costo: $0.40/millón tokens entrada, $1.60/millón tokens salida

3. **Modelo para Estrategias**: `gpt-5-nano` 
   - Usado para determinar qué herramienta/estrategia usar
   - El más económico para decisiones simples
   - Configurado en `hybrid_agent.py` línea 259
   - Costo: $0.10/millón tokens entrada, $0.40/millón tokens salida

4. **Modelo para Embeddings**: `text-embedding-3-small`
   - Ya estaba configurado correctamente
   - No requirió cambios

### Archivos Modificados

1. **`env.agent`**
   - `LLM_PROVIDER=openai` (antes: anthropic)
   - `MODEL_NAME=gpt-4o-mini` (antes: claude-3-5-sonnet-20241022)
   - Comentada la API key de Anthropic

2. **`src/agent/hybrid_agent.py`**
   - Eliminado import de `ChatAnthropic`
   - Actualizado `_initialize_llm()` para usar solo OpenAI
   - Actualizado `_initialize_quick_llm()` para usar `gpt-4o-mini`
   - Actualizado modelo de estrategias de `gpt-5-nano` a `gpt-5-mini`

3. **`src/agent/multi_agent_system.py`**
   - Eliminado import de `ChatAnthropic`
   - Actualizado `_initialize_llm()` para usar solo OpenAI
   - Actualizado `_initialize_cheap_llm()` para usar `gpt-4o-mini`

### Beneficios

1. **Reducción de Costos**: 
   - `gpt-5-nano` ($0.10/M entrada) para decisiones de herramientas
   - `gpt-5-mini` ($0.40/M entrada) para respuestas simples
   - `gpt-5` ($2/M entrada) solo para respuestas complejas
2. **Mejor Rendimiento**: GPT-4.1 tiene mejoras significativas en coding e instrucciones
3. **Consistencia**: Un solo proveedor de LLM simplifica el mantenimiento
4. **Contexto Largo**: Soporte hasta 1 millón de tokens de contexto

### Verificación

Para verificar que todo está funcionando correctamente:

```bash
# Activar entorno virtual
source venv/bin/activate

# Probar el agente
python src/agent/hybrid_agent.py

# O iniciar los servicios completos
python start_services.py
```

### Notas Importantes

- No se requieren cambios en el código de embeddings
- La funcionalidad del chatbot permanece igual
- Solo cambia el modelo subyacente de IA