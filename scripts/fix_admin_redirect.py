#!/usr/bin/env python3
"""
Script para diagnosticar y arreglar el problema de redirección infinita en /admin/
"""

print("""
🔍 El problema de redirección infinita en /admin/ generalmente ocurre cuando:

1. La ruta /admin/ redirige a /admin/ (bucle infinito)
2. Falta la ruta del dashboard de admin

Para solucionarlo en el VPS, ejecuta:

# 1. Verificar las rutas del admin
docker exec eva-web-prod grep -n "@app.get.*admin" /app/app.py

# 2. Si ves una redirección de /admin/ a /admin/, el problema está ahí.

# 3. La solución rápida es acceder directamente a:
#    http://ia.elcorteelectrico.com:8080/admin/dashboard

# 4. Para arreglar permanentemente, necesitamos cambiar la redirección
#    de /admin/ para que vaya a /admin/dashboard

El código correcto en app.py debería ser:

@app.get("/admin/")
async def admin_redirect():
    return RedirectResponse(url="/admin/dashboard", status_code=303)

O simplemente remover la redirección y mostrar el dashboard directamente.
""")