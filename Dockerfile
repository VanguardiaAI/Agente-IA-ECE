# Dockerfile multi-stage para Eva AI Assistant
# Producción optimizada con capas separadas

# Stage 1: Base con Python y dependencias del sistema
FROM python:3.10-slim AS base

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requerimientos
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: MCP Server
FROM base AS mcp-server

# Copiar código de la aplicación
COPY main.py .
COPY config/ ./config/
COPY tools/ ./tools/
COPY services/ ./services/
COPY src/ ./src/

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/knowledge

# Variables de entorno para MCP Server
ENV PYTHONUNBUFFERED=1
ENV SERVICE_TYPE=mcp

# Exponer puerto
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Comando de inicio
CMD ["python", "main.py"]

# Stage 3: Web Application
FROM base AS web-app

# Copiar código de la aplicación
COPY app.py .
COPY config/ ./config/
COPY services/ ./services/
COPY src/ ./src/
COPY templates/ ./templates/
COPY static/ ./static/

# Crear directorios necesarios
RUN mkdir -p /app/logs /app/knowledge

# Variables de entorno para Web App
ENV PYTHONUNBUFFERED=1
ENV SERVICE_TYPE=web

# Exponer puerto
EXPOSE 8080

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Comando de inicio con Uvicorn para producción
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "4", "--loop", "uvloop"]

# Stage 4: Imagen completa (desarrollo)
FROM base AS development

# Copiar todo el código
COPY . .

# Instalar dependencias de desarrollo adicionales
RUN pip install --no-cache-dir pytest pytest-asyncio black flake8 ipython

# Variables de entorno para desarrollo
ENV PYTHONUNBUFFERED=1
ENV DEVELOPMENT=true

# Exponer ambos puertos
EXPOSE 8000 8080

# Comando por defecto (puede ser sobrescrito)
CMD ["python", "start_services.py"]