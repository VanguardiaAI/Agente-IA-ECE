# AUDITORÍA DE CÓDIGO MECÁNICO, REGEX Y TRIGGERS

## RESUMEN EJECUTIVO
El sistema está PLAGADO de código mecánico, regex y patrones hardcodeados. Esto es una bomba de tiempo que causará problemas de mantenimiento y errores impredecibles.

## 1. TRIGGERS EN BASE DE DATOS

### ❌ ENCONTRADOS (aunque ya eliminados en el código nuevo):
- **Archivo**: `services/database.py` líneas 100-120
- **Función**: `update_search_vector()` 
- **Trigger**: `trigger_update_search_vector`
- **Problema**: Actualiza automáticamente el search_vector, lo cual puede causar comportamientos inesperados
- **Estado**: Script creado para eliminarlos (`scripts/remove_triggers.py`)

## 2. REGEX ENCONTRADOS (19 archivos!)

### 2.1 CRÍTICOS - En servicios core:

#### `services/database.py`
- **Línea 911**: `import re` en `_extract_technical_terms`
- **Líneas 1199-1230**: Patrones regex para detectar códigos técnicos:
  ```python
  r'\b[A-Z]{2,}[0-9]*\b'  # Siglas/códigos
  r'\b[A-Z0-9]+-[A-Z0-9]+\b'  # Códigos con guiones
  r'\b\d+[Ww]\b'  # Potencias
  r'\b\d+[Vv]\b'  # Voltajes
  # ... y muchos más
  ```
- **¿SE USA?**: SÍ - En `hybrid_search()` línea 310

#### `src/agent/hybrid_agent.py`
- **Líneas 1331-1337**: Extrae números de pedido y emails con regex
- **¿SE USA?**: SÍ - En `_handle_order_inquiry()`

### 2.2 EN AGENTES:
- `src/agent/escalation_detector.py`
- `src/agent/search_refiner_agent.py`
- `src/agent/multi_agent_system.py`
- Y muchos más...

## 3. CÓDIGO MECÁNICO / PATRONES HARDCODEADOS

### 3.1 PEOR OFENSOR: `services/database.py`

#### `_extract_technical_terms()` (líneas 909-1276)
- **934-973**: Lista GIGANTE de términos técnicos hardcodeados
- **976-1190**: Diccionario ENORME de sinónimos hardcodeados (200+ líneas!)
- **PROBLEMA**: Cualquier término nuevo requiere modificar código
- **¿SE USA?**: SÍ - En `hybrid_search()`

#### `_detect_brand_terms()` (líneas 883-907)
- **886-892**: Lista hardcodeada de marcas
- **PROBLEMA**: Nuevas marcas requieren modificar código
- **¿SE USA?**: SÍ - En `hybrid_search()`

#### `hybrid_search()` (líneas 288-552)
- **321-448**: Lógica compleja con queries SQL hardcodeadas para marcas
- **449-535**: Más lógica para términos técnicos
- **PROBLEMA**: 250+ líneas de lógica mecánica que debería ser IA

### 3.2 LISTAS HARDCODEADAS EN TODA LA APP:

#### `src/agent/hybrid_agent.py`
- **Línea 1347-1350**: Frases hardcodeadas para detectar referencias a pedidos
- **Línea 1779-1783**: Respuestas fallback hardcodeadas

#### `services/search_optimizer.py`
- **Líneas 34-83**: Lista de sinónimos del sector eléctrico (DUPLICADA!)
- **PROBLEMA**: La misma información está en múltiples lugares

## 4. CÓDIGO SPAGHETTI IDENTIFICADO

### 4.1 DUPLICACIÓN MASIVA:
- Los sinónimos técnicos están en:
  - `services/database.py` (líneas 976-1190)
  - `services/search_optimizer.py` (líneas 34-83)
  - Probablemente en más lugares

### 4.2 MÉTODOS GIGANTES:
- `hybrid_search()`: 264 líneas!
- `_extract_technical_terms()`: 367 líneas!
- `_process_with_multi_agent()`: 200+ líneas

### 4.3 DEPENDENCIAS CIRCULARES:
- `hybrid_agent.py` importa de `services/`
- Los servicios a veces importan de `src/agent/`

## 5. ANÁLISIS DE USO REAL

### ✅ SE USAN ACTIVAMENTE:
1. `_extract_technical_terms()` - Llamado en `hybrid_search()`
2. `_detect_brand_terms()` - Llamado en `hybrid_search()`
3. `hybrid_search()` - Usado en múltiples lugares:
   - `src/agent/hybrid_agent.py`
   - `tools/product_tools.py` (aunque actualizado para usar IA)
   - `app.py`

### ❓ USO DUDOSO:
1. Muchos de los agentes en `src/agent/pipeline/` parecen no usarse
2. Hay múltiples implementaciones de lo mismo (ej: varios validadores de resultados)

## 6. IMPACTO Y RIESGOS

### RIESGOS INMEDIATOS:
1. **Mantenimiento imposible**: Agregar una marca nueva requiere tocar código
2. **Inconsistencias**: Los sinónimos están duplicados y pueden divergir
3. **Escalabilidad**: Las listas hardcodeadas crecerán infinitamente
4. **Bugs ocultos**: Regex complejos son propensos a errores

### PROBLEMAS YA VISIBLES:
1. El mismo término puede tener diferentes sinónimos en diferentes archivos
2. Lógica de negocio mezclada con implementación técnica
3. Imposible testear todas las combinaciones

## 7. RECOMENDACIONES

### URGENTE:
1. **NO AGREGAR MÁS TÉRMINOS** a las listas hardcodeadas
2. **Mover todos los sinónimos a una base de datos o archivo de configuración**
3. **Reemplazar `hybrid_search()` con una versión que use solo IA**

### MEDIO PLAZO:
1. Eliminar TODOS los regex gradualmente
2. Consolidar la lógica duplicada
3. Separar la lógica de negocio del código

### LARGO PLAZO:
1. Reescribir los componentes críticos usando solo IA
2. Implementar tests para cada componente
3. Documentar las dependencias reales

## CONCLUSIÓN

El código está en un estado crítico. Hay tanto código mecánico que:
- Es imposible mantenerlo sin introducir bugs
- La IA está limitada por las listas hardcodeadas
- El sistema no puede adaptarse a nuevos productos/marcas sin tocar código

**Mi error fue asumir que el código existente seguía buenas prácticas. Debí auditar todo desde el principio.**