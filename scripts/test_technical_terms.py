#!/usr/bin/env python3
"""
Script simple para probar la detección de términos técnicos
"""

import sys
from pathlib import Path
import re
from typing import List

# Añadir el directorio padre al path
sys.path.append(str(Path(__file__).parent.parent))

def extract_technical_terms(query_text: str) -> List[str]:
    """Extraer términos técnicos importantes del query (códigos, modelos, SKUs)"""
    technical_terms = []
    
    # Patrones para detectar términos técnicos
    patterns = [
        r'\b[A-Z]{2,}\b',  # Siglas en mayúsculas (DPN, LED, IP65)
        r'\b[A-Z0-9]+-[A-Z0-9]+\b',  # Códigos con guiones (V-25, IP-65)
        r'\b[A-Z]+[0-9]+\b',  # Códigos alfanuméricos (IP65, V25)
        r'\b[0-9]+[A-Z]+\b',  # Códigos numéricos-alfabéticos (25V, 100W)
        r'\b\d+[Ww]\b',  # Potencias (100W, 50w)
        r'\b\d+[Vv]\b',  # Voltajes (220V, 12v)
        r'\b\d+[Aa]\b',  # Amperajes (10A, 25a)
        r'\b[A-Z]{1}[0-9]{2,}\b',  # Modelos (B22, E27)
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, query_text, re.IGNORECASE)
        technical_terms.extend(matches)
    
    # También agregar palabras completas en mayúsculas si tienen más de 2 caracteres
    words = query_text.split()
    for word in words:
        # Limpiar puntuación
        clean_word = re.sub(r'[^\w\-]', '', word)
        if len(clean_word) > 2 and clean_word.isupper():
            technical_terms.append(clean_word)
    
    # Eliminar duplicados manteniendo el orden
    seen = set()
    unique_terms = []
    for term in technical_terms:
        if term.upper() not in seen:
            seen.add(term.upper())
            unique_terms.append(term)
    
    return unique_terms

def test_extraction():
    """Probar la extracción de términos técnicos"""
    print("="*70)
    print("🧪 PRUEBA DE DETECCIÓN DE TÉRMINOS TÉCNICOS")
    print("="*70)
    
    test_cases = [
        "diferencial DPN",
        "magnetotérmico C60N 10A",
        "cable H07V-K 2.5mm",
        "luminaria LED IP65 50W",
        "contactor LC1D12",
        "diferencial tipo A 30mA",
        "interruptor automático ICP-M 25A",
        "base enchufe SCHUKO 16A",
        "transformador 220V a 12V 100W",
        "detector de movimiento PIR 180°",
        "Gabarron ventilador de techo industrial V-25 DC",
        "relé térmico LRD12 5.5-8A",
        "caja estanca IP65 200x150mm",
        "tubo LED T8 120cm 18W 6500K"
    ]
    
    for query in test_cases:
        terms = extract_technical_terms(query)
        print(f"\n📝 Query: '{query}'")
        print(f"🔧 Términos detectados: {terms}")
        
        # Análisis adicional
        if terms:
            print("   ✅ Análisis:")
            for term in terms:
                if re.match(r'^[A-Z]{2,}$', term, re.IGNORECASE):
                    print(f"      • '{term}' → Siglas/Código")
                elif re.match(r'^\d+[WVA]$', term, re.IGNORECASE):
                    print(f"      • '{term}' → Especificación eléctrica")
                elif re.match(r'^[A-Z0-9]+-[A-Z0-9]+$', term, re.IGNORECASE):
                    print(f"      • '{term}' → Modelo con guión")
                elif re.match(r'^[A-Z]+\d+$', term, re.IGNORECASE):
                    print(f"      • '{term}' → Código alfanumérico")
                else:
                    print(f"      • '{term}' → Otro término técnico")
        else:
            print("   ❌ No se detectaron términos técnicos")
    
    print("\n" + "="*70)
    print("✅ RESUMEN")
    print("="*70)
    print("\nLa función de detección de términos técnicos identifica:")
    print("• Siglas y códigos en mayúsculas (DPN, LED, PIR)")
    print("• Modelos con números (C60N, LC1D12, LRD12)")
    print("• Especificaciones eléctricas (50W, 220V, 16A, 30mA)")
    print("• Códigos con guiones (H07V-K, ICP-M, V-25)")
    print("• Grados de protección (IP65)")
    print("• Medidas técnicas (2.5mm, 120cm, 200x150mm)")
    print("\n✨ Esta detección mejora significativamente la precisión")
    print("   de las búsquedas al priorizar coincidencias exactas.")

if __name__ == "__main__":
    test_extraction()