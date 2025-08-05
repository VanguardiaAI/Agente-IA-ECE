#!/usr/bin/env python3
"""
Script para probar el endpoint de estadísticas
"""

import asyncio
import httpx
import json

async def test_stats():
    """Probar el endpoint /api/stats"""
    
    async with httpx.AsyncClient() as client:
        try:
            # Probar endpoint de stats
            print("🔍 Probando /api/stats...")
            response = await client.get("http://localhost:8080/api/stats")
            
            if response.status_code == 200:
                data = response.json()
                print("\n✅ Respuesta exitosa:")
                print(json.dumps(data, indent=2, default=str))
                
                # Verificar estructura
                if 'database' in data:
                    print("\n📊 Estructura de 'database':")
                    for key, value in data['database'].items():
                        print(f"  - {key}: {value}")
            else:
                print(f"❌ Error: Status {response.status_code}")
                print(response.text)
                
        except httpx.ConnectError:
            print("❌ No se pudo conectar. Asegúrate de que la aplicación esté ejecutándose.")
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("Nota: Asegúrate de que la aplicación esté ejecutándose (python3 app.py)")
    asyncio.run(test_stats())