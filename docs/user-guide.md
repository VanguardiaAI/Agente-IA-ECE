# 📚 Guía de Usuario - Eva: Asistente Virtual para WooCommerce

## 🎯 ¿Qué es Eva?

Eva es tu asistente virtual inteligente que ayuda a tus clientes las 24 horas del día, los 7 días de la semana. Puede responder preguntas sobre productos, ayudar con pedidos, y ofrecer soporte al cliente de manera automática mientras tú te enfocas en hacer crecer tu negocio.

---

## 🚀 Inicio Rápido

### Acceso al Panel de Administración

1. Abre tu navegador web
2. Ingresa a: `http://tu-dominio.com:8080/admin`
3. Inicia sesión con tus credenciales de administrador
4. ¡Ya estás listo para configurar a Eva!

### Primeros Pasos Esenciales

✅ **Verifica el estado del sistema** en el Dashboard  
✅ **Configura el mensaje de bienvenida** en Configuración  
✅ **Agrega información de tu empresa** en Base de Conocimiento  
✅ **Prueba el chat** desde tu sitio web  

---

## 📊 Panel de Control (Dashboard)

### Vista General
El dashboard te muestra información básica sobre el uso del sistema:

- **💬 Conversaciones Hoy**: Total en las últimas 24 horas
- **👥 Usuarios Únicos**: Clientes diferentes que han usado Eva hoy
- **📚 Base de Conocimiento**: Total de documentos disponibles
- **📱 Plataformas**: Distribución entre WordPress y WhatsApp
- **📋 Registro de Actividad**: Acciones recientes de administradores

### Estado del Sistema
El indicador de estado muestra si Eva está:
- **Activo**: Sistema funcionando correctamente
- **Verificando**: Comprobando conexiones
- **Inactivo**: Requiere atención

### Información Disponible
- **Total conversaciones (30 días)**: Resumen mensual
- **Actividad administrativa**: Log de cambios y accesos
- **Estado de servicios**: Base de datos y conexiones

---

## ⚙️ Configuración

### 🤖 Personalidad del Bot

#### Configuración General
- **Nombre del Bot**: Cómo se presenta (por defecto: Eva)
- **Mensaje de Bienvenida**: Primera impresión para tus clientes
- **Nombre de la Empresa**: Tu marca
- **Idioma Principal**: Español, Inglés o Catalán

#### Estilo de Respuestas
Elige cómo quieres que Eva se comunique:

- **Profesional**: Formal y corporativo
- **Casual**: Relajado pero respetuoso  
- **Amigable**: Cálido y cercano

#### Longitud de Respuestas
- **Cortas**: Directas al punto
- **Balanceadas**: Información completa pero concisa
- **Detalladas**: Explicaciones extensas

### 🕐 Horario de Atención

#### Configuración de Horario
- **Días Laborables**: Selecciona qué días trabajas
- **Hora de Apertura**: Cuándo empieza la atención
- **Hora de Cierre**: Cuándo termina la atención
- **Zona Horaria**: Tu ubicación

#### Mensajes Especiales
- **Fuera de Horario**: Qué decir cuando está cerrado
- **Días Festivos**: Mensajes para fechas especiales
- **Vacaciones**: Avisos de períodos largos sin atención

### 🎯 Comportamiento Avanzado

#### Umbrales de Confianza
- **Alta Confianza (>80%)**: Eva responde con seguridad
- **Media (50-80%)**: Eva sugiere pero pide confirmación
- **Baja (<50%)**: Eva deriva a un humano

#### Escalamiento
Palabras que activan transferencia a humano:
- "hablar con persona"
- "agente humano"
- "queja"
- "problema urgente"

---

## 📚 Base de Conocimiento

### ¿Qué es la Base de Conocimiento?
Es la información que Eva usa para responder preguntas. Aquí guardas políticas, preguntas frecuentes, información de productos especiales, y cualquier dato importante de tu negocio.

### Categorías de Documentos

#### 📋 Políticas
- Políticas de devolución
- Términos y condiciones
- Garantías
- Métodos de pago aceptados
- Políticas de envío

#### ❓ Preguntas Frecuentes
- Cómo hacer un pedido
- Tiempos de entrega
- Costos de envío
- Cómo rastrear pedidos
- Métodos de contacto

#### ℹ️ Información General
- Sobre la empresa
- Ubicación y horarios
- Servicios especiales
- Promociones actuales

### Cómo Agregar Información

1. **Ve a "Base de Conocimiento"** en el menú
2. **Haz clic en "Nuevo Documento"**
3. **Escribe el título** (ej: "Política de Devoluciones")
4. **Selecciona la categoría** apropiada
5. **Escribe el contenido** en formato simple
6. **Guarda** y Eva lo aprenderá automáticamente

### Formato de Documentos

```markdown
# Título Principal

## Sección

Información clara y directa.

### Subsección

- Punto 1
- Punto 2
- Punto 3

**Importante**: Texto resaltado
```

### Consejos para Mejor Contenido

✅ **Sé claro y directo**: Evita jerga técnica  
✅ **Usa listas**: Facilitan la lectura  
✅ **Incluye ejemplos**: Ayudan a entender  
✅ **Actualiza regularmente**: Mantén información vigente  
❌ **Evita contradicciones**: Revisa consistencia  

---

## 💬 Información de Conversaciones

### Datos Registrados
El sistema registra información básica sobre las conversaciones:

- **ID de Usuario**: Identificador único del cliente
- **Plataforma**: WordPress o WhatsApp
- **Fecha y Hora**: Cuándo ocurrió la conversación
- **Cantidad de Mensajes**: Total de intercambios

### Configuración de Escalamiento
Puedes configurar palabras clave que activen respuestas especiales:

#### Palabras de Escalamiento
- "hablar con persona"
- "agente humano"
- "queja"
- "problema urgente"

Cuando los clientes usan estas palabras, Eva puede ofrecer información de contacto o instrucciones para atención personalizada.

### Limitaciones Importantes
⚠️ **Nota**: El sistema **NO** incluye:
- Monitor de conversaciones en tiempo real
- Historial detallado de conversaciones
- Sistema de escalamiento automático a humanos
- Métricas de satisfacción del cliente
- Análisis de sentimientos
- Intervención manual en conversaciones activas

---

## 🛍️ Integración WooCommerce

### Sincronización de Productos

#### Automática
- Eva sincroniza productos cada 6 horas
- Actualizaciones en tiempo real vía webhooks
- Detecta cambios automáticamente

#### Manual
1. Ve a "Configuración"
2. Sección "WooCommerce"
3. Haz clic en "Sincronizar Ahora"
4. Espera confirmación (puede tardar minutos)

### Información de Productos
Eva conoce de cada producto:
- Nombre y descripción
- Precio (con IVA incluido)
- Disponibilidad en stock
- Categorías
- Imágenes
- Variaciones (tallas, colores)
- Especificaciones técnicas

### Gestión de Pedidos

#### Consultas Seguras
Para ver información de pedidos, Eva solicita:
1. Número de pedido
2. Email del cliente
3. Validación de ambos

#### Información Disponible
- Estado del pedido
- Productos comprados
- Total pagado
- Dirección de envío
- Número de seguimiento

---

## 📱 WhatsApp Business

### Configuración Inicial

#### Requisitos
- Cuenta Business de WhatsApp
- Número verificado
- API de 360Dialog configurada

#### Activación
1. Ve a "Configuración" > "WhatsApp"
2. Ingresa tu número de teléfono
3. Configura las plantillas de mensajes
4. Activa las notificaciones

### Tipos de Mensajes

#### Respuestas Automáticas
- Mensaje de bienvenida
- Horario de atención
- Confirmación de recepción

#### Plantillas Aprobadas
- Recuperación de carrito abandonado
- Mensajes promocionales (si están configurados)

### Recuperación de Carritos Abandonados

#### Configuración
- **Tiempo de Espera**: 20 minutos por defecto
- **Mensaje**: Un solo mensaje personalizado con productos
- **Descuento**: Código "DESCUENTOEXPRESS" (fijo)
- **Frecuencia**: Un mensaje por carrito abandonado

#### Proceso Automático
1. Cliente abandona carrito
2. Eva espera el tiempo configurado (20 min por defecto)
3. Envía UN mensaje por WhatsApp con código DESCUENTOEXPRESS
4. Incluye lista de productos y enlace al carrito
5. No se envían mensajes adicionales

#### Configuración en WooCommerce
En "WooCommerce Cart Abandonment Recovery" puedes ajustar:
- **Tiempo de corte**: Cuándo considerar un carrito como abandonado
- **URL del webhook**: Para conectar con Eva
- **Otras opciones**: Configuraciones adicionales disponibles

**Nota**: El código de descuento "DESCUENTOEXPRESS" es fijo y no se puede modificar.

---

## 🌐 Widget de WordPress

### Instalación

#### En WordPress
1. Ve a Plugins > Añadir Nuevo
2. Sube el archivo `eva-chatbot-widget.zip`
3. Activa el plugin
4. Ve a "Eva Chatbot" en el menú

#### Configuración Básica
- **URL del Servidor**: Dirección de Eva
- **Mensaje de Bienvenida**: Saludo inicial
- **Posición**: Esquina inferior derecha/izquierda
- **Páginas**: Dónde mostrar el widget

### Personalización Visual

#### Colores
- **Color Principal**: Botón y encabezado
- **Color de Texto**: Mensajes y labels
- **Fondo**: Transparente o sólido

#### Tamaño y Posición
- **Tamaño del Botón**: Pequeño, Mediano, Grande
- **Posición**: 4 esquinas disponibles
- **Margen**: Distancia del borde

### Comportamiento

#### Auto-apertura
- Configura segundos de espera
- Muestra mensaje de invitación
- Solo primera visita o siempre

#### Respuestas Rápidas
Botones predefinidos:
- "Ver catálogo"
- "Estado de mi pedido"
- "Hablar con alguien"
- "Horario de atención"

---

## 📈 Métricas Básicas

### Información Disponible
El panel de administración muestra métricas básicas del sistema:

#### Métricas del Dashboard
- **Conversaciones hoy**: Total en las últimas 24 horas
- **Usuarios únicos hoy**: Clientes diferentes
- **Total conversaciones (30 días)**: Resumen mensual
- **Documentos en base de conocimiento**: Total disponible
- **Distribución por plataforma**: WordPress vs WhatsApp

### Registro de Actividad

#### Log de Administración
Se registran todas las acciones realizadas por administradores:
- Cambios en configuración
- Modificaciones en base de conocimiento
- Accesos al panel
- Fecha, hora e IP de cada acción

### Limitaciones
⚠️ **Importante**: El sistema **NO** incluye:
- Reportes avanzados o detallados
- Exportación de datos
- Análisis de tendencias
- Gráficos o visualizaciones
- Métricas de rendimiento del bot
- Cálculo de ROI
- Reportes programados

---

---

## 💡 Mejores Prácticas

### Para Mejor Rendimiento

#### Base de Conocimiento
✅ **Mantén información actualizada**  
✅ **Usa lenguaje simple y claro**  
✅ **Organiza por categorías lógicas**  
✅ **Incluye variaciones de preguntas**  

#### Configuración
✅ **Ajusta personalidad según tu marca**  
✅ **Define horarios realistas**  
✅ **Configura escalamiento apropiado**  
✅ **Personaliza mensajes de error**  

#### Monitoreo
✅ **Revisa métricas regularmente**  
✅ **Actúa sobre feedback de clientes**  
✅ **Identifica patrones y tendencias**  
✅ **Optimiza basándote en datos**  


---

## 🎯 Casos de Uso Exitosos

### Atención 24/7
Eva puede manejar:
- Consultas fuera de horario
- Días festivos y fines de semana
- Zonas horarias diferentes
- Picos de demanda inesperados

### Ventas Asistidas
- Recomendación de productos
- Comparación de opciones
- Explicación de características
- Cálculo de precios con descuentos

### Soporte Post-Venta
- Estado de pedidos
- Seguimiento de envíos
- Gestión de devoluciones
- Resolución de dudas

### Marketing Automatizado
- Recuperación de carritos
- Promociones personalizadas
- Recordatorios de recompra
- Solicitud de reseñas

---

## 📝 Notas Finales

### Actualizaciones
Eva se actualiza constantemente. Las nuevas funciones aparecerán automáticamente en tu panel.

### Feedback
Tu opinión es importante. Usa el botón de feedback en el panel para sugerir mejoras.

### Comunidad
Únete a otros usuarios de Eva para compartir experiencias y mejores prácticas.

### Recursos Adicionales
- Video tutoriales
- Webinars mensuales
- Blog con tips y casos de éxito
- Foro de usuarios

---

**Versión de la Guía**: 1.0  
**Última Actualización**: Agosto 2025  
**Desarrollado por**: Vanguardia.dev