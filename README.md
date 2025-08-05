# 🤖 Agente de Atención al Cliente con WooCommerce y MCP

Un agente de inteligencia artificial avanzado para atención al cliente que se integra con WooCommerce utilizando el protocolo MCP (Model Context Protocol).

## 🚀 Características

- **Integración con WooCommerce**: Acceso directo a productos, pedidos y clientes
- **Protocolo MCP**: Comunicación eficiente con el servidor de WooCommerce
- **Memoria de conversación**: Mantiene contexto entre sesiones
- **Detección de escalación**: Transfiere automáticamente a humanos cuando es necesario
- **Búsqueda híbrida**: Combina información de la base de datos y WooCommerce
- **Interfaz web**: Dashboard para monitoreo y gestión
- **Logging completo**: Registro detallado de todas las conversaciones

## 📋 Requisitos Previos

- Python 3.10+
- PostgreSQL
- Docker y Docker Compose
- Cuenta de OpenAI o Anthropic
- Tienda WooCommerce configurada

## 🛠️ Instalación

### 1. Clonar el repositorio

```bash
git clone https://github.com/tu-usuario/mcp-wc-agent.git
cd mcp-wc-agent
```

### 2. Configurar el entorno virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar variables de entorno

```bash
cp env.agent.example env.agent
```

Edita `env.agent` con tus credenciales:

```bash
# Configuración de OpenAI
OPENAI_API_KEY=tu_api_key_aqui
MODEL_NAME=gpt-4.1

# Configuración de WooCommerce
WOOCOMMERCE_API_URL=https://tu-tienda.com/wp-json/wc/v3
WOOCOMMERCE_CONSUMER_KEY=tu_consumer_key
WOOCOMMERCE_CONSUMER_SECRET=tu_consumer_secret

# Base de datos PostgreSQL
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/knowledge_base
```

### 4. Configurar la base de datos

```bash
# Iniciar PostgreSQL con Docker
docker-compose up -d postgres

# Crear la base de datos
docker exec -it mcp-wc-postgres psql -U postgres -c "CREATE DATABASE knowledge_base;"
```

### 5. Inicializar la base de datos

```bash
python scripts/init_database.py
```

## 🚀 Uso

### Iniciar el servidor MCP de WooCommerce

```bash
python -m mcp_woocommerce_server
```

### Iniciar el agente de atención al cliente

```bash
python app.py
```

### Acceder a la interfaz web

Abre tu navegador en `http://localhost:8000`

## 📁 Estructura del Proyecto

```
MCP-WC/
├── app.py                          # Aplicación principal
├── config/                         # Configuraciones
├── docker/                         # Configuración de Docker
├── docs/                          # Documentación
├── eva-chat-widget/               # Widget de chat para WordPress
├── knowledge/                     # Base de conocimiento
├── scripts/                       # Scripts de utilidad
├── services/                      # Servicios del agente
├── src/                          # Código fuente principal
├── templates/                     # Plantillas HTML
├── tests/                        # Pruebas
└── tools/                        # Herramientas del agente
```

## 🔧 Configuración

### Variables de Entorno Principales

| Variable | Descripción | Ejemplo |
|----------|-------------|---------|
| `LLM_PROVIDER` | Proveedor de LLM | `openai` o `anthropic` |
| `OPENAI_API_KEY` | API Key de OpenAI | `sk-...` |
| `WOOCOMMERCE_API_URL` | URL de la API de WooCommerce | `https://tienda.com/wp-json/wc/v3` |
| `DATABASE_URL` | URL de conexión a PostgreSQL | `postgresql://user:pass@host:port/db` |

### Configuración del Agente

- **Tiempo máximo de conversación**: 30 minutos
- **Máximo de turnos**: 50 por conversación
- **Transferencia automática**: Habilitada
- **Logging**: Completo con nivel INFO

## 🧪 Pruebas

Ejecutar todas las pruebas:

```bash
python -m pytest tests/
```

Ejecutar pruebas específicas:

```bash
python -m pytest tests/test_agent_tools.py -v
```

## 📊 Monitoreo

### Logs de Conversación

Las conversaciones se registran automáticamente en:
- Base de datos PostgreSQL
- Archivos de log (si está habilitado)

### Métricas Disponibles

- Tiempo promedio de respuesta
- Tasa de resolución automática
- Frecuencia de escalación
- Satisfacción del cliente

## 🔒 Seguridad

### Archivos Sensibles

Los siguientes archivos NO se incluyen en el repositorio:
- `env.agent` (contiene credenciales)
- `docker/postgres/data/` (datos de base de datos)
- `venv/` (entorno virtual)

### Mejores Prácticas

1. **Nunca** subir credenciales al repositorio
2. Usar variables de entorno para configuraciones sensibles
3. Rotar regularmente las API keys
4. Monitorear logs de acceso

## 🤝 Contribución

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver el archivo `LICENSE` para más detalles.

## 🆘 Soporte

Si tienes problemas o preguntas:

1. Revisa la [documentación](docs/)
2. Busca en los [issues existentes](https://github.com/tu-usuario/mcp-wc-agent/issues)
3. Crea un nuevo issue con detalles del problema

## 🔄 Roadmap

- [ ] Integración con WhatsApp Business API
- [ ] Análisis de sentimientos en tiempo real
- [ ] Dashboard de analytics avanzado
- [ ] Soporte multiidioma
- [ ] Integración con CRM externos
- [ ] Automatización de respuestas por email

## 📞 Contacto

- **Desarrollador**: Tu Nombre
- **Email**: tu-email@ejemplo.com
- **Proyecto**: [https://github.com/tu-usuario/mcp-wc-agent](https://github.com/tu-usuario/mcp-wc-agent)

---

⭐ Si este proyecto te ayuda, ¡déjanos una estrella!