# Panel de Administración Eva AI Assistant

## 📋 Descripción
Panel de control completo para administrar y configurar el chatbot Eva sin necesidad de tocar código.

## 🚀 Instalación

### 1. Configurar el panel
```bash
python scripts/setup_admin_panel.py
```

Este script:
- Crea las tablas necesarias en PostgreSQL
- Configura un usuario administrador inicial
- Prepara las configuraciones por defecto

### 2. Iniciar la aplicación
```bash
python app.py
```

### 3. Acceder al panel
Abre tu navegador en: `http://localhost:8080/admin/login`

## 🔐 Autenticación

### Login
- URL: `/admin/login`
- Usa las credenciales configuradas durante la instalación
- La sesión se mantiene por 24 horas

### Crear administradores adicionales
1. Accede al panel como administrador
2. Usa la API `/api/admin/create-admin`
3. O ejecuta nuevamente `python scripts/setup_admin_panel.py`

## 📱 Secciones del Panel

### 1. Dashboard
- **Estadísticas en tiempo real**: Conversaciones, usuarios únicos, documentos
- **Actividad reciente**: Log de acciones administrativas
- **Estado del sistema**: Verificación de servicios activos

### 2. Configuración del Bot

#### Identidad
- **Nombre del bot**: Personaliza el nombre (default: Eva)
- **Nombre de empresa**: Configura el nombre de tu empresa
- **Mensaje de bienvenida**: Personaliza el saludo inicial

#### Personalidad
- **Estilo de respuesta**: Profesional, amigable o casual
- **Longitud de respuestas**: Breve, balanceada o detallada
- **Idioma**: Español, inglés o catalán

#### Configuración IA
- **Modelo LLM**: GPT-4, GPT-4 Mini, GPT-3.5 Turbo
- **Temperatura**: Control de creatividad (0-1)
- **Máximo de tokens**: Límite de respuesta
- **Pesos de búsqueda**: Balance entre búsqueda vectorial y textual

#### Características
- **Escalamiento a humano**: Activar/desactivar
- **Búsqueda de pedidos**: Habilitar consultas de pedidos
- **Búsqueda de productos**: Activar catálogo
- **Base de conocimiento**: Usar documentos de conocimiento
- **Palabras clave de escalamiento**: Configurar triggers

#### Negocio
- **Horario de atención**: Configurar días y horas
- **Mensaje fuera de horario**: Respuesta automática
- **Productos a mostrar**: Límite en resultados

### 3. Base de Conocimiento

#### Gestión de Documentos
- **Ver documentos**: Lista completa con categorías
- **Crear nuevo**: Editor markdown integrado
- **Editar**: Modificar contenido existente
- **Eliminar**: Borrar documentos
- **Recargar**: Regenerar embeddings

#### Categorías
- `general`: Información general
- `policies`: Políticas de la empresa
- `faqs`: Preguntas frecuentes

#### Editor Markdown
- Sintaxis completa de Markdown
- Vista previa en tiempo real
- Auto-guardado
- Regeneración automática de embeddings

### 4. Métricas y Analytics

#### Gráficos disponibles
- **Conversaciones por hora**: Actividad del día
- **Temas populares**: Consultas más frecuentes
- **Tasa de satisfacción**: Feedback de usuarios
- **Tiempo de respuesta**: Performance del bot

### 5. Probar Bot
- Chat de prueba integrado
- Usa la configuración actual
- Permite validar cambios antes de producción

## 🔧 APIs del Panel

### Autenticación
- `POST /api/admin/login` - Iniciar sesión
- `POST /api/admin/logout` - Cerrar sesión
- `GET /api/admin/verify` - Verificar token
- `GET /api/admin/me` - Info del usuario actual
- `POST /api/admin/change-password` - Cambiar contraseña

### Configuraciones
- `GET /api/admin/settings/` - Obtener todas
- `GET /api/admin/settings/category/{category}` - Por categoría
- `GET /api/admin/settings/{key}` - Configuración específica
- `PUT /api/admin/settings/` - Actualizar una
- `PUT /api/admin/settings/bulk` - Actualizar varias
- `POST /api/admin/settings/reset` - Restablecer a defaults
- `GET /api/admin/settings/export/json` - Exportar configuración
- `POST /api/admin/settings/import` - Importar configuración

### Knowledge Base
- `GET /api/admin/knowledge/documents` - Listar documentos
- `GET /api/admin/knowledge/document/{filename}` - Obtener documento
- `PUT /api/admin/knowledge/document/{filename}` - Actualizar
- `POST /api/admin/knowledge/document` - Crear nuevo
- `DELETE /api/admin/knowledge/document/{filename}` - Eliminar
- `POST /api/admin/knowledge/reload` - Recargar todos
- `POST /api/admin/knowledge/search` - Buscar en KB

### Logs y Actividad
- `GET /api/admin/activity-logs` - Obtener logs de actividad

## 🎨 Personalización

### Modificar estilos
Edita el CSS en `/templates/admin_dashboard.html`:
```css
:root {
    --primary-color: #2563eb;
    --sidebar-width: 250px;
    --primary-gradient: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### Agregar nuevas secciones
1. Añade el menú en el sidebar
2. Crea la sección en el HTML
3. Implementa la lógica en `/static/admin.js`
4. Crea las APIs necesarias

## 🔒 Seguridad

### Características implementadas
- **JWT Authentication**: Tokens seguros con expiración
- **Bcrypt hashing**: Passwords encriptados
- **Session management**: Control de sesiones activas
- **Activity logging**: Registro de todas las acciones
- **CORS protection**: Configurado para producción

### Recomendaciones
1. Cambia `JWT_SECRET_KEY` en producción
2. Usa HTTPS siempre
3. Configura CORS apropiadamente
4. Implementa rate limiting
5. Realiza backups regulares

## 📊 Base de Datos

### Tablas creadas
- `admin_users`: Usuarios administradores
- `bot_settings`: Configuraciones clave-valor
- `conversation_metrics`: Métricas agregadas
- `admin_activity_logs`: Logs de actividad
- `admin_sessions`: Sesiones activas

### Vistas
- `conversation_stats_summary`: Estadísticas diarias
- `recent_admin_activity`: Actividad reciente

## 🐛 Solución de Problemas

### Error de login
1. Verifica las credenciales
2. Revisa que las tablas existan
3. Comprueba los logs del servidor

### No se guardan configuraciones
1. Verifica permisos en la base de datos
2. Revisa la consola del navegador
3. Comprueba los logs de la API

### Knowledge Base no se actualiza
1. Verifica que el servicio de embeddings esté activo
2. Revisa la API key de OpenAI
3. Comprueba el formato de los archivos markdown

## 📝 Notas

- Los cambios en configuración se aplican inmediatamente
- Los documentos de knowledge base se procesan al guardar
- El cache de configuración se actualiza cada 5 minutos
- Las métricas se agregan cada hora

## 🚀 Próximas Mejoras

- [ ] Dashboard con más métricas detalladas
- [ ] Editor visual de flujos de conversación
- [ ] Gestión de templates de respuesta
- [ ] Sistema de roles y permisos
- [ ] Backup automático de configuraciones
- [ ] Integración con analytics externos
- [ ] Modo oscuro
- [ ] Multi-idioma en la interfaz