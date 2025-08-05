=== Eva Chatbot Widget ===
Contributors: vanguardiadev
Tags: chatbot, woocommerce, customer-service, ai, chat
Requires at least: 5.0
Tested up to: 6.4
Requires PHP: 7.2
Stable tag: 2.0.0
License: GPLv2 or later
License URI: https://www.gnu.org/licenses/gpl-2.0.html

Widget de chat inteligente para atención al cliente en tiendas WooCommerce con IA.

== Description ==

Eva Chatbot Widget integra un asistente virtual inteligente en tu tienda WooCommerce para brindar atención al cliente 24/7. El widget se conecta con el servidor de Eva para proporcionar respuestas inteligentes sobre productos, pedidos y consultas generales.

= Características principales =

* Chat en tiempo real con WebSocket
* Interfaz flotante personalizable
* Búsqueda inteligente de productos
* Gestión de pedidos
* Soporte multiidioma
* Panel de administración intuitivo
* Compatible con dispositivos móviles

= Requisitos =

* WordPress 5.0 o superior
* PHP 7.2 o superior
* Servidor Eva instalado y funcionando
* WooCommerce (opcional pero recomendado)

== Installation ==

1. Descarga el plugin y descomprime el archivo ZIP
2. Sube la carpeta `eva-chatbot-widget` al directorio `/wp-content/plugins/`
3. Activa el plugin desde el menú 'Plugins' en WordPress
4. Ve a 'Eva Chatbot' en el menú de administración
5. Configura la URL del servidor Eva (por defecto: http://localhost:8080)
6. Personaliza los colores y mensajes según tu preferencia
7. Guarda los cambios y el widget aparecerá en tu sitio

= Configuración del servidor =

Asegúrate de que tu servidor Eva esté funcionando correctamente:

1. El servidor debe estar accesible desde tu sitio WordPress
2. Los endpoints `/api/chat` y `/ws/chat/` deben estar disponibles
3. Si usas HTTPS en WordPress, configura SSL en el servidor Eva

== Frequently Asked Questions ==

= ¿Necesito WooCommerce para usar este plugin? =

No es obligatorio, pero el chatbot está optimizado para tiendas WooCommerce. Puede funcionar en cualquier sitio WordPress.

= ¿Cómo configuro el servidor Eva? =

Consulta la documentación completa en https://github.com/vanguardia/eva-chatbot-server

= ¿El widget funciona en dispositivos móviles? =

Sí, el widget es completamente responsivo y se adapta a pantallas móviles.

= ¿Puedo personalizar los colores del widget? =

Sí, desde el panel de administración puedes cambiar los colores principales y del texto.

= ¿Qué pasa si el servidor no está disponible? =

El widget maneja automáticamente las desconexiones y muestra mensajes apropiados al usuario.

== Screenshots ==

1. Widget flotante en la esquina inferior derecha
2. Ventana de chat abierta con conversación
3. Panel de administración con opciones de configuración
4. Personalización de colores y estilos
5. Vista móvil del widget

== Changelog ==

= 2.0.0 =
* Nuevo esquema de colores corporativo (verde)
* Añadido campo para personalizar el nombre del chatbot
* Mensajes personalizables (escribiendo, error)
* Control de tiempo de auto-apertura configurable
* Sistema de respuestas rápidas
* Mejorado el panel de administración
* Correcciones de caché y rendimiento
* Añadido archivo de desinstalación limpia

= 1.0.0 =
* Versión inicial
* Chat en tiempo real con WebSocket
* Panel de administración completo
* Soporte para personalización de estilos
* Compatible con WooCommerce

== Upgrade Notice ==

= 1.0.0 =
Primera versión estable del plugin.

== Configuration ==

= Configuración básica =

1. **URL del Servidor**: Ingresa la URL donde está alojado tu servidor Eva
2. **Mensaje de Bienvenida**: Personaliza el saludo inicial del chatbot
3. **Posición**: Elige entre esquina inferior derecha o izquierda
4. **Páginas**: Muestra el widget en todas las páginas o solo en páginas específicas

= Configuración avanzada =

Para configuraciones avanzadas, puedes usar los siguientes hooks:

`add_filter('eva_chatbot_config', 'mi_configuracion_personalizada');`

= Solución de problemas =

Si el widget no aparece:
1. Verifica que el plugin esté activado
2. Comprueba la conexión con el servidor usando el botón "Probar Conexión"
3. Revisa la consola del navegador para mensajes de error
4. Asegúrate de que no haya conflictos con otros plugins

== API Hooks ==

= Acciones disponibles =

* `eva_chatbot_before_render` - Antes de renderizar el widget
* `eva_chatbot_after_message_sent` - Después de enviar un mensaje
* `eva_chatbot_log_interaction` - Para registrar interacciones

= Filtros disponibles =

* `eva_chatbot_config` - Modificar la configuración del widget
* `eva_chatbot_welcome_message` - Personalizar mensaje de bienvenida
* `eva_chatbot_display_rules` - Modificar reglas de visualización