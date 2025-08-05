# Configuración de WhatsApp Business API con 360Dialog

## 📋 Prerrequisitos

1. **Cuenta de 360Dialog**: Regístrate en [360dialog.com](https://360dialog.com)
2. **Número de WhatsApp Business**: Un número de teléfono que no esté registrado en WhatsApp
3. **Servidor con HTTPS**: Para recibir webhooks (el proyecto ya incluye esto)

## 🔧 Configuración Paso a Paso

### 1. Configurar Variables de Entorno

Edita tu archivo `.env` y agrega las siguientes variables:

```env
# Configuración de WhatsApp 360Dialog
WHATSAPP_360DIALOG_API_KEY=tu_api_key_de_360dialog
WHATSAPP_360DIALOG_API_URL=https://waba-v2.360dialog.io
WHATSAPP_PHONE_NUMBER=34123456789  # Sin + ni espacios
WHATSAPP_WEBHOOK_VERIFY_TOKEN=un_token_seguro_aleatorio
WHATSAPP_BUSINESS_ACCOUNT_ID=tu_business_account_id

# Plantillas de WhatsApp (nombres exactos de las plantillas aprobadas)
WHATSAPP_CART_RECOVERY_TEMPLATE=cart_recovery_es
WHATSAPP_ORDER_CONFIRMATION_TEMPLATE=order_confirmation_es
WHATSAPP_WELCOME_TEMPLATE=welcome_message_es
```

### 2. Obtener API Key de 360Dialog

1. Inicia sesión en tu [Panel de 360Dialog](https://hub.360dialog.com/)
2. Ve a **Settings** → **API Keys**
3. Crea una nueva API Key o copia la existente
4. Guárdala en `WHATSAPP_360DIALOG_API_KEY`

### 3. Configurar Webhook en 360Dialog

1. En el panel de 360Dialog, ve a **Settings** → **Webhooks**
2. Configura la URL del webhook:
   ```
   https://tu-dominio.com/api/webhooks/whatsapp
   ```
3. Configura el Verify Token (debe coincidir con `WHATSAPP_WEBHOOK_VERIFY_TOKEN`)
4. Selecciona los eventos a recibir:
   - ✅ Messages
   - ✅ Message Status
   - ✅ Errors

### 4. Crear Plantillas de Mensajes

Las plantillas deben ser aprobadas por WhatsApp antes de usarlas.

#### Plantilla de Recuperación de Carrito

**Nombre**: `cart_recovery_es`

**Contenido**:
```
Hola {{1}},

Notamos que dejaste estos productos en tu carrito:
{{2}}

Total: {{3}}

¿Te gustaría completar tu compra? Haz clic aquí: {{4}}

Si tienes alguna pregunta, estoy aquí para ayudarte.

Saludos,
Eva - Tu asistente virtual
```

#### Plantilla de Confirmación de Pedido

**Nombre**: `order_confirmation_es`

**Contenido**:
```
¡Gracias por tu compra, {{1}}!

Tu pedido {{2}} ha sido confirmado.
Total: {{3}}
Entrega estimada: {{4}}

Puedes seguir tu pedido aquí: {{5}}

¿Necesitas ayuda? Responde a este mensaje.
```

#### Plantilla de Bienvenida

**Nombre**: `welcome_message_es`

**Contenido**:
```
¡Hola {{1}}! 👋

Soy Eva, tu asistente virtual de El Corte Eléctrico.

Puedo ayudarte con:
• 🔍 Buscar productos
• 📦 Consultar tus pedidos
• 💡 Recomendaciones personalizadas
• ❓ Resolver tus dudas

¿En qué puedo ayudarte hoy?
```

### 5. Verificar la Configuración

Ejecuta el script de prueba para verificar que todo esté configurado correctamente:

```bash
python tests/test_whatsapp_integration.py
```

## 🚀 Uso

### Recepción de Mensajes

Los mensajes de WhatsApp se reciben automáticamente en el webhook y son procesados por Eva.

### Envío de Mensajes

#### Mensajes dentro de la ventana de 24 horas:
```python
await whatsapp_service.send_text_message(
    to="34612345678",
    text="Hola, gracias por contactarnos. ¿En qué puedo ayudarte?"
)
```

#### Mensajes fuera de la ventana de 24 horas (requieren plantilla):
```python
await template_manager.send_welcome_message(
    phone_number="34612345678",
    customer_name="María"
)
```

### Recuperación de Carritos Abandonados

Ejecutar manualmente:
```bash
python scripts/whatsapp_cart_recovery.py
```

Ejecutar en modo prueba (sin enviar mensajes reales):
```bash
python scripts/whatsapp_cart_recovery.py --dry-run
```

Ver estadísticas:
```bash
python scripts/whatsapp_cart_recovery.py --stats --days 30
```

### Configurar Cron Job para Recuperación Automática

Añadir a crontab para ejecutar diariamente a las 10:00 AM:
```bash
0 10 * * * cd /ruta/a/tu/proyecto && /usr/bin/python scripts/whatsapp_cart_recovery.py >> logs/cart_recovery.log 2>&1
```

## 📊 Monitoreo

### Logs de WhatsApp

Los logs específicos de WhatsApp se pueden filtrar:
```bash
grep "WhatsApp" logs/app.log
```

### Métricas en el Dashboard

Accede a `http://localhost:8080/` para ver:
- Mensajes enviados/recibidos
- Tasa de respuesta
- Carritos recuperados
- Errores de API

## 🔒 Seguridad

1. **Verificación de Webhook**: Todos los webhooks se verifican con el token configurado
2. **Rate Limiting**: La API de 360Dialog tiene límites que se respetan automáticamente
3. **Encriptación**: Todos los mensajes viajan encriptados end-to-end
4. **Logs**: No se guardan mensajes completos, solo metadatos

## 🐛 Solución de Problemas

### El webhook no se verifica

1. Verifica que la URL sea HTTPS
2. Confirma que el token coincide exactamente
3. Revisa los logs: `grep "webhook" logs/app.log`

### No se envían mensajes

1. Verifica el formato del número (sin espacios ni +)
2. Confirma que el número tiene WhatsApp Business
3. Revisa el saldo en tu cuenta 360Dialog

### Las plantillas no funcionan

1. Asegúrate de que están aprobadas en el Business Manager
2. Verifica que el nombre coincide exactamente
3. Confirma que los parámetros son correctos

## 📚 Referencias

- [Documentación de 360Dialog](https://docs.360dialog.com/)
- [WhatsApp Business API](https://developers.facebook.com/docs/whatsapp/cloud-api)
- [Mejores Prácticas](https://www.whatsapp.com/business/api-best-practices)