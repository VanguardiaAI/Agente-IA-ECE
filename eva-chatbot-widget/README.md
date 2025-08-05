# Eva Chatbot Widget para WordPress

Widget de chat inteligente que integra el asistente virtual Eva en tu sitio WordPress/WooCommerce.

## 🚀 Características

- ✨ **Chat en tiempo real** con WebSocket y fallback a REST API
- 🎨 **Interfaz personalizable** con colores y posiciones configurables
- 📱 **Totalmente responsivo** para dispositivos móviles
- 🔍 **Búsqueda inteligente** de productos en WooCommerce
- 💬 **Persistencia de conversaciones** en localStorage
- 🔔 **Notificaciones** cuando llegan mensajes nuevos
- 🔒 **Seguro** con validación de nonces y sanitización
- ⚡ **Reconexión automática** en caso de pérdida de conexión

## 📋 Requisitos

- WordPress 5.0+
- PHP 7.2+
- jQuery (incluido en WordPress)
- Servidor Eva funcionando (puerto 8080 por defecto)

## 🛠️ Instalación

### Método 1: Instalación manual

1. Descarga o clona este repositorio
2. Copia la carpeta `eva-chatbot-widget` a `/wp-content/plugins/`
3. Activa el plugin desde el panel de WordPress
4. Ve a "Eva Chatbot" en el menú de administración
5. Configura la URL de tu servidor Eva

### Método 2: ZIP desde WordPress

1. Comprime la carpeta `eva-chatbot-widget` en un archivo ZIP
2. En WordPress, ve a Plugins > Añadir nuevo
3. Haz clic en "Subir plugin"
4. Selecciona el archivo ZIP y haz clic en "Instalar ahora"
5. Activa el plugin

## ⚙️ Configuración

### Configuración básica

1. **URL del Servidor**: La URL donde está corriendo tu servidor Eva (ej: `http://localhost:8080`)
2. **Mensaje de Bienvenida**: El mensaje que verán los usuarios al abrir el chat
3. **Posición**: Esquina inferior derecha o izquierda
4. **Páginas**: Mostrar en todas las páginas o solo en páginas específicas

### Configuración de estilos

- **Color Principal**: Color del botón y encabezado
- **Color del Texto**: Color del texto en elementos principales
- **Tamaño del Botón**: Pequeño (50px), Mediano (60px), o Grande (70px)

## 🔧 Configuración del Servidor Eva

Asegúrate de que tu servidor Eva esté configurado correctamente:

```bash
# Iniciar el servidor Eva
cd /ruta/a/tu/servidor/eva
python app.py
```

El servidor debe exponer los siguientes endpoints:
- `GET /health` - Para verificar el estado
- `POST /api/chat` - Para mensajes REST
- `WS /ws/chat/{client_id}` - Para WebSocket

### Configuración CORS

Si tu WordPress está en un dominio diferente, configura CORS en el servidor Eva:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://tu-sitio-wordpress.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 🎨 Personalización avanzada

### Hooks disponibles

```php
// Modificar configuración
add_filter('eva_chatbot_config', function($config) {
    $config['welcome_message'] = 'Mi mensaje personalizado';
    return $config;
});

// Registrar interacciones
add_action('eva_chatbot_log_interaction', function($data) {
    // Guardar en base de datos, analytics, etc.
    error_log('Chat interaction: ' . json_encode($data));
});
```

### CSS personalizado

```css
/* Cambiar el z-index del widget */
.eva-chatbot-widget {
    z-index: 999999 !important;
}

/* Personalizar el botón */
.eva-chat-button {
    box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
}
```

## 🐛 Solución de problemas

### El widget no aparece

1. Verifica que el plugin esté activado
2. Revisa la consola del navegador (F12)
3. Comprueba que jQuery esté cargado
4. Verifica las reglas de visualización en la configuración

### Error de conexión

1. Usa el botón "Probar Conexión" en la configuración
2. Verifica que el servidor Eva esté funcionando
3. Comprueba que la URL sea correcta
4. Revisa los logs del servidor

### Mensajes no se envían

1. Verifica la consola para errores de JavaScript
2. Comprueba que el endpoint `/api/chat` responda
3. Verifica permisos CORS si es necesario

## 📊 Monitoreo

Para ver estadísticas del chat:

```php
$api = new Eva_API();
$stats = $api->get_stats();
print_r($stats);
```

## 🔐 Seguridad

El plugin implementa las siguientes medidas de seguridad:

- Validación de nonces en peticiones AJAX
- Sanitización de todas las entradas de usuario
- Escape de salidas HTML
- Validación de URLs del servidor
- Protección contra XSS

## 📜 Changelog

### v2.1.0 (2025-01-25)
- 🆕 Soporte para detección automática de plataforma (WordPress/WhatsApp)
- 🎨 Formato HTML enriquecido para respuestas en WordPress
- 🖼️ Previsualización de productos con imágenes en el chat
- 🔗 Enlaces con vista previa mejorada
- 🚀 Mejor experiencia de usuario en WordPress

### v2.0.0
- ✨ Personalización de avatar con WordPress Media Library
- 🎨 Diseño transparente con efecto glassmorphism
- 🔧 Mejoras en la configuración del admin
- 🐛 Correcciones de estilos y compatibilidad

## 🤝 Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está licenciado bajo GPL v2 o posterior - ver el archivo [LICENSE](LICENSE) para más detalles.

## 👥 Autores

- **Vanguardia.dev** - *Desarrollo inicial* - [vanguardia.dev](https://vanguardia.dev)

## 🙏 Agradecimientos

- Equipo de WordPress por la excelente documentación
- Comunidad de WooCommerce
- Todos los que han contribuido al proyecto