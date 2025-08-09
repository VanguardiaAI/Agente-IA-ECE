#!/usr/bin/env python3
"""
Script para arreglar la ruta /admin agregando manejo para /admin/
"""

fix_code = '''
# Agregar después de la ruta @app.get("/admin", response_class=HTMLResponse)

@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard_slash(request: Request):
    """Manejar /admin/ para evitar redirecciones infinitas"""
    # Simplemente llamar a la misma función que maneja /admin
    return await admin_dashboard(request)
'''

print("""
Para arreglar el problema de redirección, necesitas agregar una ruta adicional en app.py

Busca la línea que dice:
@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):

Y justo después, agrega:

@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard_slash(request: Request):
    return await admin_dashboard(request)

Esto hará que tanto /admin como /admin/ funcionen sin redirecciones.
""")