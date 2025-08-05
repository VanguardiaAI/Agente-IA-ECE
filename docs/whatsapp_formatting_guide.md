# Guía de Formato para WhatsApp - Eva Assistant

## Resumen
Esta guía describe cómo Eva formatea las respuestas para WhatsApp, optimizando la experiencia del usuario con formato claro, profesional y fácil de leer.

## Formato de Productos

### Estructura de Producto Individual
```
📦 *Nombre del Producto*
💰 ~Precio Original€~ *Precio Oferta€* ¡OFERTA!
✅ Disponible / ❌ Sin stock
📋 Ref: SKU12345
🔗 Ver producto: https://tienda.com/producto

```

### Ejemplo Real
```
📦 *Gabarron ventilador de techo v-25 dc*
💰 ~266.2€~ *206.31€* ¡OFERTA!
✅ Disponible
📋 Ref: 90920070
🔗 Ver producto: https://staging.elcorteelectrico.com/producto/gabarron-v25-dc/
```

## Componentes del Formato

### 1. Emojis Informativos
- 🔍 - Resultados de búsqueda
- 📦 - Producto
- 💰 - Precio
- ✅ - Disponible
- ❌ - Sin stock
- 📋 - Referencia/SKU
- 🔗 - Enlace
- 🏷️ - Categorías
- 📞 - Contacto de ayuda

### 2. Formato de Texto
- `*Texto*` - Negrita para nombres y precios importantes
- `~Texto~` - Tachado para precios originales
- Enlaces completos para fácil acceso

### 3. Información Incluida
- Nombre completo del producto
- Precio con IVA incluido (21%)
- Precio original y precio de oferta si aplica
- Estado del stock
- SKU/Referencia para búsquedas precisas
- Link directo al producto
- Categorías cuando sea relevante

## Ejemplos de Respuestas

### Búsqueda de Productos
```
🔍 *Productos encontrados:*

📦 *Producto 1*
💰 *99.99€* (IVA incluido)
✅ Disponible
📋 Ref: ABC123
🔗 Ver producto: https://tienda.com/producto1

📦 *Producto 2*
💰 ~149.99€~ *119.99€* ¡OFERTA!
❌ Sin stock
📋 Ref: DEF456
🔗 Ver producto: https://tienda.com/producto2

📞 *¿Necesitas ayuda?*
Escribe el número del producto o llama al (+34) 614 21 81 22
```

### Producto Individual Detallado
```
📦 **Ventilador de techo Gabarron V-25 DC**

💰 ~266.2€~ **206.31€** ¡OFERTA!
✅ Disponible (3 unidades)
🏷️ Ventiladores, Climatización
📋 Ref: 90920070

📝 Ventilador industrial de gran potencia, ideal para espacios amplios...

🔗 Ver producto:
https://tienda.com/gabarron-v25-dc

📞 ¿Necesitas ayuda? (+34) 614 21 81 22
```

## Mejores Prácticas

### 1. Claridad
- Información más importante primero (nombre, precio, disponibilidad)
- Enlaces al final de cada producto
- Separación clara entre productos

### 2. Concisión
- Máximo 3-5 productos por respuesta
- Descripciones breves (máximo 150 caracteres)
- Solo información esencial

### 3. Accesibilidad
- Enlaces completos (no acortados)
- Emojis descriptivos pero no excesivos
- Formato consistente

### 4. Llamadas a la Acción
- Siempre incluir número de teléfono de ayuda
- Invitar a la interacción ("¿Necesitas más información?")
- Facilitar siguiente paso

## Consideraciones Técnicas

### Limitaciones de WhatsApp
- No soporta HTML o Markdown complejo
- Solo negrita (*texto*) y tachado (~texto~)
- Los enlaces deben ser URLs completas
- Límite de caracteres por mensaje

### Optimización
- Productos con ofertas primero
- Información de precio siempre con IVA incluido
- SKU para facilitar pedidos telefónicos
- Enlaces directos sin redirecciones

## Actualizaciones del Sistema

Los siguientes archivos han sido actualizados para implementar este formato:

1. `/src/agent/hybrid_agent.py` - Método `_handle_product_search()`
2. `/tools/product_tools.py` - Función de búsqueda híbrida
3. `/services/woocommerce.py` - Método `format_product()`

Todos los precios mostrados incluyen el 21% de IVA aplicado durante la sincronización.