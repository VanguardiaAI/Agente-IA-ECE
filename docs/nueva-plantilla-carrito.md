# Plantilla de Recuperación de Carritos Multimedia

## Estado: ✅ FUNCIONANDO

### Configuración Probada

**Nombre de plantilla**: `carrito_abandono_multimedia`
**Idioma**: `es` (español)
**Estado**: Aprobada y funcionando

### Componentes

1. **Header**: 
   - Tipo: Imagen
   - URL que funciona: `https://i.imgur.com/HP7WXrY.png`
   - ⚠️ IMPORTANTE: La imagen DEBE ser accesible públicamente desde WhatsApp

2. **Body con 4 variables**:
   - `{{1}}`: Nombre del cliente (primer nombre)
   - `{{2}}`: Lista de productos
   - `{{3}}`: Total del carrito (formato: "13,81 €")
   - `{{4}}`: Código de descuento

3. **Footer**: Texto estático (opcional)

4. **Botón**: URL estática (configurada en Meta)

### Problemas Resueltos

1. **Imagen no accesible**: Las URLs de El Corte Eléctrico y placeholder.com no funcionaban
2. **Formato correcto**: Sin incluir parámetros para el botón (es URL estática)
3. **Sin fallback**: Quitamos el fallback automático para detectar errores

### Uso en Código

```python
await template_manager.send_cart_recovery_multimedia(
    phone_number="525612720431",
    cart_data={
        "customer_name": "Juan Pérez",
        "items": [
            {
                "name": "Schneider A9P53616 IC40F 1P+N 16A C 6kA Mini",
                "sku": "A9P53616",
                "quantity": 1
            }
        ],
        "total": 13.81,
        "discount_code": "DESCUENTOEXPRESS",
        "header_image_url": "https://i.imgur.com/HP7WXrY.png"  # Opcional
    }
)
```

### Recomendaciones

1. **Subir la imagen del logo a Imgur** o servicio similar que sea 100% público
2. **Verificar siempre** que la imagen sea accesible con curl o wget
3. **No usar** imágenes de:
   - Facebook CDN (expiran)
   - Sitios con protección CloudFlare
   - URLs temporales o con tokens

### Script de Prueba

```bash
python scripts/test_cart_recovery_mx_auto.py
```

### Próximos Pasos

1. Subir el logo real de El Corte Eléctrico a un CDN confiable
2. Actualizar la URL por defecto en el código
3. Probar con carritos reales de WooCommerce