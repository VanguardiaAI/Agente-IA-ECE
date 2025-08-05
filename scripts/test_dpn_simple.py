#!/usr/bin/env python3
"""
Script simple para probar la detección de términos técnicos
"""

import sys
from pathlib import Path

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

from services.database import db_service

# Probar la función de extracción de términos
queries = [
    "diferencial DPN",
    "Busco un diferencial DPN",
    "diferencial con protección DPN",
    "quiero un diferencial tipo DPN",
    "DPN diferencial",
    "diferencial",
    "magnetotérmico C60N"
]

print("="*70)
print("PRUEBA DE DETECCIÓN DE TÉRMINOS TÉCNICOS")
print("="*70)

for query in queries:
    terms = db_service._extract_technical_terms(query)
    print(f"\n📝 Query: '{query}'")
    print(f"🔧 Términos detectados: {terms}")
    print(f"   ¿Detecta DPN?: {'✅ SÍ' if 'DPN' in terms else '❌ NO'}")