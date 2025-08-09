#!/usr/bin/env python3
"""
Script seguro para iniciar los servicios con verificación de configuración
"""

import os
import sys
import subprocess
import time
from pathlib import Path

def run_config_check():
    """Ejecutar verificación de configuración"""
    print("🔍 Verificando configuración del sistema...\n")
    
    result = subprocess.run(
        [sys.executable, "scripts/check_config.py"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print("\n❌ La configuración no está completa.")
        print("Por favor, sigue las sugerencias anteriores antes de continuar.\n")
        
        response = input("¿Deseas continuar de todos modos? (s/N): ")
        if response.lower() != 's':
            sys.exit(1)
    
    return True

def check_docker():
    """Verificar si Docker está ejecutándose"""
    try:
        result = subprocess.run(
            ["docker", "ps"],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("⚠️  Docker no está ejecutándose.")
            print("   Por favor, inicia Docker Desktop primero.\n")
            return False
        return True
    except FileNotFoundError:
        print("❌ Docker no está instalado.")
        print("   Instala Docker desde: https://www.docker.com/get-started\n")
        return False

def start_postgres():
    """Iniciar PostgreSQL si no está ejecutándose"""
    print("🐘 Verificando PostgreSQL...")
    
    # Verificar si ya está ejecutándose
    result = subprocess.run(
        ["docker", "ps", "--filter", "name=eva-postgres", "--format", "{{.Names}}"],
        capture_output=True,
        text=True
    )
    
    if "eva-postgres" in result.stdout:
        print("   ✅ PostgreSQL ya está ejecutándose\n")
        return True
    
    print("   Iniciando PostgreSQL con Docker...")
    subprocess.run([
        "docker", "run", "-d",
        "--name", "eva-postgres",
        "-e", "POSTGRES_USER=eva_user",
        "-e", "POSTGRES_PASSWORD=eva_password",
        "-e", "POSTGRES_DB=eva_db",
        "-p", "5432:5432",
        "-v", "eva_postgres_data:/var/lib/postgresql/data",
        "pgvector/pgvector:pg16"
    ])
    
    # Esperar a que esté listo
    print("   Esperando a que PostgreSQL esté listo...")
    time.sleep(5)
    print("   ✅ PostgreSQL iniciado\n")
    return True

def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 INICIANDO SERVICIOS EVA AI - MODO SEGURO")
    print("=" * 60)
    print()
    
    # Verificar configuración
    if not run_config_check():
        sys.exit(1)
    
    # Verificar Docker
    if not check_docker():
        print("No se puede continuar sin Docker.\n")
        sys.exit(1)
    
    # Iniciar PostgreSQL si es necesario
    if not start_postgres():
        print("Error al iniciar PostgreSQL.\n")
        sys.exit(1)
    
    print("✅ Todas las verificaciones pasadas!\n")
    print("Iniciando servicios...\n")
    
    # Ejecutar el script de inicio normal
    try:
        subprocess.run([sys.executable, "start_services.py"])
    except KeyboardInterrupt:
        print("\n\n👋 Servicios detenidos por el usuario.")
    except Exception as e:
        print(f"\n❌ Error al iniciar servicios: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()