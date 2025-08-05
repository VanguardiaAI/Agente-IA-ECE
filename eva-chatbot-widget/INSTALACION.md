# INSTRUCCIONES DE INSTALACIÓN - IMPORTANTE

## Pasos para una instalación limpia:

### 1. DESINSTALAR LA VERSIÓN ANTERIOR
- Ve a **Plugins** en WordPress
- Busca "Eva Chatbot Widget"
- **Desactivar** el plugin
- **Eliminar** el plugin completamente

### 2. LIMPIAR CACHÉ
- Limpia la caché de tu navegador (Ctrl+F5 o Cmd+Shift+R)
- Si usas un plugin de caché en WordPress (WP Rocket, W3 Total Cache, etc.), límpialo
- Si usas un CDN (Cloudflare, etc.), purga la caché

### 3. INSTALAR LA NUEVA VERSIÓN
- Ve a **Plugins → Añadir nuevo → Subir plugin**
- Selecciona el archivo `eva-chatbot-widget.zip`
- Instalar y **Activar**

### 4. CONFIGURAR EL PLUGIN
- Ve al menú **Eva Chatbot** en el panel de WordPress
- Deberías ver las siguientes opciones nuevas:
  - **Nombre del Chatbot**: Cambia "Eva" por el nombre que prefieras
  - **Mensaje "Escribiendo"**: Personaliza el texto cuando el bot está escribiendo
  - **Mensaje de Error**: Personaliza el mensaje de error de conexión
  - **Auto-apertura**: Configura cuándo se abre automáticamente
  - **Respuestas Rápidas**: Añade botones personalizados (opcional)

### 5. VERIFICAR LOS CAMBIOS
Los cambios visuales que deberías ver:
- Botón de chat color **verde oscuro** (#54841e)
- Header del chat color **verde oscuro**
- Mensajes del usuario en **verde**
- Mensajes del bot con fondo **gris claro** (#f1f1f1)
- NO deberían aparecer botones de respuesta rápida por defecto

## SOLUCIÓN DE PROBLEMAS

### Si NO ves el menú "Eva Chatbot":
1. Verifica que eres administrador
2. Desactiva y reactiva el plugin
3. Verifica en **Configuración → Enlaces permanentes** y guarda sin cambios

### Si los colores siguen siendo azules:
1. Fuerza recarga con Ctrl+F5
2. Abre el chat en modo incógnito/privado
3. Revisa la consola del navegador (F12) por errores

### Si aparecen los botones grises:
1. Ve a **Eva Chatbot → Respuestas Rápidas**
2. Elimina todas las respuestas rápidas
3. Guarda cambios

## VERIFICACIÓN TÉCNICA
En la consola del navegador (F12), ejecuta:
```javascript
console.log(evaChat.primaryColor); // Debería mostrar: #54841e
console.log(evaChat.chatbotName); // Debería mostrar el nombre configurado
```

Si necesitas ayuda adicional, verifica que la versión del plugin sea **2.0.0**.