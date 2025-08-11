# Cambios realizados para desactivar auto-apertura del widget

## Resumen
El widget ahora permanece siempre cerrado por defecto y solo se abre cuando el usuario hace clic explícitamente en el botón. Al cambiar de página, el widget se cierra automáticamente.

## Cambios en archivos:

### 1. eva-chatbot-widget/assets/js/eva-widget.js
- **Líneas 29-36**: Eliminada la funcionalidad de auto-apertura en primera visita
- **Líneas 150-154**: Desactivada la restauración del estado abierto entre páginas
- **Línea 125**: Eliminado el guardado del estado "abierto" en localStorage
- **Línea 134**: Eliminado el guardado del estado "cerrado" en localStorage

### 2. eva-chatbot-widget/eva-chatbot-widget.php
- **Línea 120**: Cambiado `autoOpenDelay` a '0' (deshabilitado permanentemente)
- **Línea 234**: Valor por defecto en instalación cambiado de '3' a '0'

### 3. eva-chatbot-widget/includes/class-eva-admin.php
- **Línea 31**: Valor por defecto cambiado de '3' a '0' con comentario explicativo

## Comportamiento actual:
1. ✅ El widget NUNCA se abre automáticamente
2. ✅ Solo se abre con clic explícito del usuario
3. ✅ Al cambiar de página, siempre se inicia cerrado
4. ✅ No se guarda ni restaura el estado entre páginas
5. ✅ La opción sigue disponible en el panel de administración pero con "Nunca" como valor por defecto

## Notas para el administrador:
- Si deseas reactivar la auto-apertura, puedes hacerlo desde:
  WordPress Admin > Eva Chatbot > Configuración > Auto-apertura
- Selecciona el tiempo deseado (3, 5, 10 o 30 segundos)
- Para mantenerlo siempre cerrado, déjalo en "Nunca"