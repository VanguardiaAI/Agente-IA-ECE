# Guía para Crear Plantilla de Recuperación de Carritos en Meta Business

## Configuración de la Plantilla en Meta Business Suite

### 1. Información Básica
- **Nombre de plantilla**: `carrito_abandono_multimedia`
- **Categoría**: Marketing
- **Tipo de plantilla**: Media & Interactive  
- **Idioma**: Español (es)

### 2. Componentes de la Plantilla

#### HEADER (Encabezado)
- **Tipo**: Image
- **Formato**: Static
- **Archivo**: Subir logo de El Corte Eléctrico (fondo negro con texto verde)
- **Resolución recomendada**: 800x418 px o proporción similar

#### BODY (Cuerpo del mensaje)
```
¡Hola {{1}}! 👋

No te olvides de completar tu compra. Hemos guardado estos productos para ti:

{{2}}

💰 Total: {{3}}

🎁 ¡OFERTA ESPECIAL!
Usa el código {{4}} y obtén un 5% de descuento

⏰ Válido solo por 24 horas

¿Necesitas ayuda? Responde a este mensaje.
```

**Variables del Body:**
- `{{1}}`: Nombre del cliente (solo primer nombre)
- `{{2}}`: Lista de productos con formato "- Nombre SKU"
- `{{3}}`: Total del carrito en formato "13,81 €"
- `{{4}}`: Código de descuento (ej: DESCUENTOEXPRESS)

#### FOOTER (Pie de mensaje) - Opcional
```
El Corte Eléctrico - Tu tienda de confianza
```

#### BUTTONS (Botones)
- **Tipo**: Call to Action (CTA)
- **Subtipo**: Visit Website
- **Texto del botón**: `🛒 Completar Compra`
- **URL**: Dynamic (Dinámica)
- **Variable URL**: `{{5}}`

### 3. Ejemplo de Vista Previa

Así se verá el mensaje final:

```
[IMAGEN: Logo El Corte Eléctrico]

¡Hola Juan! 👋

No te olvides de completar tu compra. Hemos guardado estos productos para ti:

- Schneider A9P53616 IC40F 1P+N 16A C 6kA Mini (DPN) A9P53616

💰 Total: 13,81 €

🎁 ¡OFERTA ESPECIAL!
Usa el código DESCUENTOEXPRESS y obtén un 5% de descuento

⏰ Válido solo por 24 horas

¿Necesitas ayuda? Responde a este mensaje.

El Corte Eléctrico - Tu tienda de confianza

[🛒 Completar Compra]
```

## Implementación en el Código

Una vez aprobada la plantilla (24-48 horas), usar la función:

```python
# En tu script de recuperación de carritos
await template_manager.send_cart_recovery_multimedia(
    phone_number="525610830260",
    cart_data={
        "customer_name": "Juan Pérez",
        "items": [
            {
                "name": "Schneider A9P53616 IC40F 1P+N 16A C 6kA Mini (DPN)",
                "sku": "A9P53616",
                "quantity": 1
            }
        ],
        "total": 13.81,
        "discount_code": "DESCUENTOEXPRESS",
        "cart_url": "https://elcorteelectrico.es/checkout/?recover=cart_123"
    }
)
```

## Verificación de Variables

El código genera exactamente 5 variables que coinciden con la plantilla:

1. **{{1}}**: Primer nombre del cliente
2. **{{2}}**: Lista de productos formateada con saltos de línea
3. **{{3}}**: Total con formato español (coma decimal + €)
4. **{{4}}**: Código de descuento
5. **{{5}}**: URL completa del carrito para el botón

## Notas Importantes

1. **Aprobación**: La plantilla debe ser aprobada por Meta antes de poder usarse (24-48 horas)
2. **Límites**: Máximo 1024 caracteres en el body, incluyendo variables
3. **Emojis**: Son permitidos y recomendados para mejor engagement
4. **Botón CTA**: El botón con URL dinámica mejora significativamente la conversión
5. **Idioma**: Asegúrate de seleccionar "Español (es)" exactamente

## Alternativa Temporal

Mientras se aprueba la plantilla, puedes seguir usando:
- La plantilla actual `carrito_recuperacion_descuento` (3 variables)
- Mensajes de sesión activa (si el cliente escribió en las últimas 24 horas)

## Proceso de Aprobación

1. Crear la plantilla en Meta Business Suite
2. Enviar para revisión
3. Esperar aprobación (24-48 horas)
4. Una vez aprobada, actualizar el nombre en el código si es diferente
5. Comenzar a usar con `send_cart_recovery_multimedia()`