#!/usr/bin/env python3
"""
Aplicación Principal - Sistema de Atención al Cliente con Búsqueda Híbrida
Incluye webhooks, sincronización WooCommerce, y gestión completa
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

# Agregar el directorio raíz al path para las importaciones
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, Depends, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import json
from json import JSONEncoder

# Importar servicios
from services.database import db_service
from services.embedding_service import embedding_service
from services.woocommerce_sync import wc_sync_service
from services.webhook_handler import webhook_handler
from services.conversation_logger import conversation_logger
from services.whatsapp_webhook_handler import whatsapp_webhook_handler
from services.whatsapp_360dialog_service import whatsapp_service
from services.knowledge_base import knowledge_service
from services.conversation_memory import memory_service
from config.settings import settings

# FASE 3: Importar nuevo sistema multi-agente inteligente
# from src.agent.intelligent_multi_agent import IntelligentMultiAgent
# FASE 4: Usar el nuevo agente GPT-5
from src.agent.eva_gpt5_agent import EvaGPT5Agent

# Importar servicios de administración
from services.admin_auth import admin_auth_service
from services.bot_config_service import bot_config_service
from services.metrics_service import MetricsService

# Importar routers de admin
from api.admin import auth as admin_auth_router
from api.admin import settings as admin_settings_router
from api.admin import knowledge as admin_knowledge_router

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Custom JSON encoder para manejar datetime objects
class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Crear aplicación FastAPI
app = FastAPI(
    title="Sistema de Atención al Cliente - Recambios Eléctricos",
    description="API completa con búsqueda híbrida, webhooks y sincronización WooCommerce",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    default_response_class=JSONResponse
)

# Configurar CORS
cors_origins = os.getenv("CORS_ORIGINS", "").split(",") if os.getenv("CORS_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Per-Page"]
)

# Templates y archivos estáticos
templates = Jinja2Templates(directory="templates")
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# Incluir routers de administración
app.include_router(admin_auth_router.router)
app.include_router(admin_settings_router.router)
app.include_router(admin_knowledge_router.router)

# FASE 3: Instancia global del sistema multi-agente inteligente
intelligent_agent: Optional[EvaGPT5Agent] = None

# Instancia global del servicio de métricas
metrics_service: Optional[MetricsService] = None

# Gestión de conexiones WebSocket
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"Cliente {client_id} conectado via WebSocket")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"Cliente {client_id} desconectado")
    
    async def send_personal_message(self, message: str, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            await websocket.send_text(message)

manager = ConnectionManager()

# Modelos Pydantic
class WebhookPayload(BaseModel):
    """Modelo para payloads de webhooks"""
    event: str
    data: Dict[str, Any]

class SyncRequest(BaseModel):
    """Modelo para solicitudes de sincronización"""
    force_update: bool = False
    product_id: Optional[int] = None

class SearchRequest(BaseModel):
    """Modelo para solicitudes de búsqueda"""
    query: str
    limit: int = 10
    content_types: Optional[list] = None
    search_type: str = "hybrid"  # hybrid, vector, text

class ChatMessage(BaseModel):
    """Modelo para mensajes de chat"""
    message: str
    user_id: str = "anonymous"
    platform: str = "wordpress"  # "whatsapp" o "wordpress" - default wordpress para web

# Eventos de inicio y cierre
@app.on_event("startup")
async def startup_event():
    """Inicializar servicios al arrancar"""
    global intelligent_agent, metrics_service
    logger.info("🚀 Iniciando aplicación Fase 3...")
    
    try:
        # Inicializar base de datos
        await db_service.initialize()
        logger.info("✅ Base de datos inicializada")
        
        # Inicializar servicio de embeddings
        await embedding_service.initialize()
        logger.info("✅ Servicio de embeddings inicializado")
        
        # Inicializar servicio de knowledge base
        await knowledge_service.initialize()
        logger.info("✅ Servicio de knowledge base inicializado")
        
        # Inicializar servicio de memoria de conversación
        await memory_service.initialize()
        logger.info("✅ Servicio de memoria inicializado")
        
        # Inicializar logger de conversaciones
        await conversation_logger.initialize()
        logger.info("✅ Logger de conversaciones inicializado")
        
        # FASE 3: Inicializar sistema multi-agente inteligente
        intelligent_agent = EvaGPT5Agent()
        await intelligent_agent.initialize()
        logger.info("✅ Sistema Multi-Agente Inteligente con GPT-5 inicializado")
        
        # Inicializar servicios de administración
        await admin_auth_service.initialize()
        logger.info("✅ Servicio de autenticación admin inicializado")
        
        await bot_config_service.initialize()
        logger.info("✅ Servicio de configuración del bot inicializado")
        
        # Inicializar servicio de métricas
        metrics_service = MetricsService(settings.DATABASE_URL)
        await metrics_service.initialize()
        logger.info("✅ Servicio de métricas inicializado")
        
        # Iniciar scheduler de limpieza automática en segundo plano
        asyncio.create_task(metrics_service.start_cleanup_scheduler())
        logger.info("✅ Scheduler de limpieza de métricas iniciado")
        
        logger.info("🎉 Aplicación Fase 3 iniciada correctamente")
        
    except Exception as e:
        logger.error(f"❌ Error iniciando aplicación: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Limpiar recursos al cerrar"""
    logger.info("🛑 Cerrando aplicación...")
    
    try:
        await db_service.close()
        logger.info("✅ Base de datos cerrada")
        
        if metrics_service:
            await metrics_service.close()
            logger.info("✅ Servicio de métricas cerrado")
        
    except Exception as e:
        logger.error(f"❌ Error cerrando aplicación: {e}")

# Rutas principales
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard principal del sistema"""
    try:
        # Obtener estadísticas
        db_stats = await db_service.get_statistics()
        sync_status = await wc_sync_service.get_sync_status()
        webhook_stats = await webhook_handler.get_webhook_stats()
        
        # FASE 3: Estadísticas del agente
        agent_stats = None
        if intelligent_agent:
            try:
                agent_stats = intelligent_agent.get_conversation_stats()
            except:
                agent_stats = {"status": "error"}
        
        # Función auxiliar para convertir datetime a string recursivamente
        def serialize_dates(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize_dates(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize_dates(item) for item in obj]
            return obj
        
        # Serializar todas las fechas en los objetos antes de pasarlos al template
        db_stats = serialize_dates(db_stats) if db_stats else {}
        sync_status = serialize_dates(sync_status) if sync_status else {}
        webhook_stats = serialize_dates(webhook_stats) if webhook_stats else {}
        agent_stats = serialize_dates(agent_stats) if agent_stats else {}
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "db_stats": db_stats,
            "sync_status": sync_status,
            "webhook_stats": webhook_stats,
            "agent_stats": agent_stats,
            "active_connections": len(manager.active_connections),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error en dashboard: {e}")
        return HTMLResponse(f"<h1>Error: {str(e)}</h1>", status_code=500)

@app.get("/chat", response_class=HTMLResponse)
async def chat_interface(request: Request):
    """Interfaz de chat independiente"""
    return templates.TemplateResponse("enhanced_chat.html", {
        "request": request
    })

# Rutas del panel de administración
@app.get("/admin/login", response_class=HTMLResponse)
async def admin_login_page(request: Request):
    """Página de login del panel de administración"""
    return templates.TemplateResponse("admin_login.html", {
        "request": request
    })

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    """Dashboard del panel de administración"""
    return templates.TemplateResponse("admin_dashboard.html", {
        "request": request
    })

@app.get("/admin/", response_class=HTMLResponse)
async def admin_dashboard_slash(request: Request):
    """Dashboard del panel de administración - maneja /admin/ para evitar redirecciones"""
    return await admin_dashboard(request)

@app.get("/admin/user-guide", response_class=HTMLResponse)
async def admin_user_guide(request: Request):
    """Guía de usuario para administradores"""
    return templates.TemplateResponse("admin_user_guide.html", {
        "request": request
    })

@app.get("/api/bot/config")
async def get_bot_public_config():
    """Obtener configuración pública básica del bot"""
    try:
        # Obtener configuración básica que es segura para mostrar públicamente
        bot_name = await bot_config_service.get_setting("bot_name", "Eva")
        company_name = await bot_config_service.get_setting("company_name", "El Corte Eléctrico")
        welcome_message = await bot_config_service.get_setting("welcome_message", "Hola, ¿en qué puedo ayudarte hoy?")
        
        # Reemplazar "Eva" con el nombre configurado del bot en el mensaje de bienvenida
        if "Eva" in welcome_message and bot_name != "Eva":
            welcome_message = welcome_message.replace("Eva", bot_name)
        
        return {
            "bot_name": bot_name,
            "company_name": company_name,
            "welcome_message": welcome_message,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo configuración pública del bot: {e}")
        # Devolver valores por defecto en caso de error
        return {
            "bot_name": "Eva",
            "company_name": "El Corte Eléctrico", 
            "welcome_message": "Hola, ¿en qué puedo ayudarte hoy?",
            "timestamp": datetime.now().isoformat()
        }

@app.get("/health")
async def health_check():
    """Verificación de salud del sistema"""
    try:
        # Verificar servicios críticos
        db_ok = db_service.initialized
        embedding_ok = embedding_service.initialized
        
        return {
            "status": "healthy" if db_ok and embedding_ok else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": {
                "database": "ok" if db_ok else "error",
                "embeddings": "ok" if embedding_ok else "error"
            }
        }
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "error": str(e)}
        )

# Endpoints de búsqueda híbrida
@app.post("/api/search")
async def hybrid_search(request: SearchRequest):
    """Realizar búsqueda híbrida en la base de conocimiento"""
    try:
        if not db_service.initialized:
            raise HTTPException(status_code=503, detail="Base de datos no inicializada")
        
        # Generar embedding para la consulta
        embedding = await embedding_service.generate_embedding(request.query)
        
        # Realizar búsqueda según el tipo
        if request.search_type == "hybrid":
            results = await db_service.hybrid_search(
                query_text=request.query,
                query_embedding=embedding,
                content_types=request.content_types,
                limit=request.limit
            )
        elif request.search_type == "vector":
            results = await db_service.vector_search(
                query_embedding=embedding,
                content_types=request.content_types,
                limit=request.limit
            )
        elif request.search_type == "text":
            results = await db_service.text_search(
                query_text=request.query,
                content_types=request.content_types,
                limit=request.limit
            )
        else:
            raise HTTPException(status_code=400, detail="Tipo de búsqueda no válido")
        
        return {
            "query": request.query,
            "search_type": request.search_type,
            "results_count": len(results),
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error en búsqueda: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/search/similar/{external_id}")
async def find_similar(external_id: str, limit: int = 5):
    """Encontrar elementos similares por ID externo"""
    try:
        if not db_service.initialized:
            raise HTTPException(status_code=503, detail="Base de datos no inicializada")
        
        # Obtener el elemento original
        original = await db_service.get_knowledge_by_external_id(external_id)
        if not original:
            raise HTTPException(status_code=404, detail="Elemento no encontrado")
        
        # Buscar similares usando el embedding del elemento original
        if original.get('embedding'):
            results = await db_service.vector_search(
                query_embedding=original['embedding'],
                limit=limit + 1  # +1 porque el original aparecerá en resultados
            )
            
            # Filtrar el elemento original de los resultados
            filtered_results = [
                r for r in results 
                if r.get('external_id') != external_id
            ][:limit]
            
            return {
                "original_id": external_id,
                "original_title": original.get('title', ''),
                "similar_count": len(filtered_results),
                "similar_items": filtered_results,
                "timestamp": datetime.now().isoformat()
            }
        else:
            raise HTTPException(status_code=400, detail="Elemento sin embedding disponible")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error buscando similares: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints de sincronización
@app.post("/api/sync/products")
async def sync_products(request: SyncRequest, background_tasks: BackgroundTasks):
    """Sincronizar productos de WooCommerce"""
    try:
        if request.product_id:
            # Sincronizar producto específico
            success = await wc_sync_service.sync_single_product(request.product_id)
            return {
                "action": "sync_single_product",
                "product_id": request.product_id,
                "success": success,
                "timestamp": datetime.now().isoformat()
            }
        else:
            # Sincronizar todos los productos en segundo plano
            background_tasks.add_task(_background_sync_all_products, request.force_update)
            return {
                "action": "sync_all_products",
                "status": "started",
                "force_update": request.force_update,
                "message": "Sincronización iniciada en segundo plano",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error en sincronización: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/sync/status")
async def get_sync_status():
    """Obtener estado de la sincronización"""
    try:
        status = await wc_sync_service.get_sync_status()
        return status
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de sync: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints de webhooks
@app.post("/api/webhooks/woocommerce")
async def woocommerce_webhook(request: Request):
    """Procesar webhooks de WooCommerce"""
    try:
        # Obtener headers y body
        headers = dict(request.headers)
        body = await request.body()
        
        # Procesar webhook
        result = await webhook_handler.process_webhook(headers, body)
        
        return {
            "status": "processed",
            "result": result,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error procesando webhook: {e}")
        return JSONResponse(
            status_code=200,  # Siempre devolver 200 para webhooks
            content={
                "status": "error", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )

@app.get("/api/webhooks/stats")
async def get_webhook_stats():
    """Obtener estadísticas de webhooks"""
    try:
        stats = await webhook_handler.get_webhook_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error obteniendo stats de webhooks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoint de webhook de WhatsApp
@app.get("/api/webhooks/whatsapp")
async def whatsapp_webhook_verify(request: Request):
    """Verificar webhook de WhatsApp (360Dialog)"""
    try:
        # Obtener parámetros de verificación
        mode = request.query_params.get("hub.mode")
        token = request.query_params.get("hub.verify_token")
        challenge = request.query_params.get("hub.challenge")
        
        logger.info(f"📱 WhatsApp webhook verification request: mode={mode}, token={token[:10]}..., challenge={challenge}")
        
        # Verificar webhook
        result = whatsapp_webhook_handler.verify_webhook(mode, token, challenge)
        
        if result:
            # Devolver el challenge para verificación exitosa
            # 360Dialog espera el challenge como string, no int
            logger.info("✅ WhatsApp webhook verified successfully")
            return result
        else:
            logger.warning("❌ WhatsApp webhook verification failed")
            raise HTTPException(status_code=403, detail="Verificación fallida")
            
    except Exception as e:
        logger.error(f"Error verificando webhook de WhatsApp: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/webhooks/whatsapp")
async def whatsapp_webhook(request: Request, background_tasks: BackgroundTasks):
    """Procesar webhooks de WhatsApp (360Dialog)"""
    try:
        # Obtener body del request
        body = await request.json()
        
        # Log para debugging
        logger.info(f"WhatsApp webhook recibido: {json.dumps(body, indent=2, cls=DateTimeEncoder)}")
        
        # Procesar webhook en segundo plano para responder rápido
        background_tasks.add_task(_process_whatsapp_webhook, body)
        
        # Responder inmediatamente a 360Dialog
        return JSONResponse(
            status_code=200,
            content={"status": "received"}
        )
        
    except Exception as e:
        logger.error(f"Error procesando webhook de WhatsApp: {e}")
        # Siempre devolver 200 para evitar reintentos
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)}
        )

@app.post("/webhook/cart-abandoned")
async def cart_abandoned_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Procesar webhook de carritos abandonados desde WooCommerce Cart Abandonment Recovery
    URL para configurar en el plugin: https://tu-ngrok.ngrok-free.app/webhook/cart-abandoned
    """
    try:
        # Log headers para debugging
        content_type = request.headers.get("content-type", "")
        logger.info(f"🛒 Webhook recibido - Content-Type: {content_type}")
        logger.info(f"Headers: {dict(request.headers)}")
        
        # Intentar obtener datos según el Content-Type
        body = None
        
        if "application/json" in content_type:
            # Es JSON
            body = await request.json()
            logger.info(f"JSON Body: {json.dumps(body, indent=2, cls=DateTimeEncoder)}")
            
        elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            # Es form data
            form_data = await request.form()
            body = dict(form_data)
            logger.info(f"Form Data: {body}")
            
            # Si hay un campo que contiene JSON, parsearlo
            for key, value in body.items():
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        body[key] = json.loads(value)
                    except:
                        pass
        else:
            # Intentar leer como texto plano
            raw_body = await request.body()
            logger.info(f"Raw Body: {raw_body.decode('utf-8', errors='ignore')}")
            
            # Intentar parsear como JSON de todos modos
            try:
                body = json.loads(raw_body)
            except:
                # Si no es JSON, intentar parsear como query string
                from urllib.parse import parse_qs
                parsed = parse_qs(raw_body.decode('utf-8', errors='ignore'))
                body = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
        
        if not body:
            logger.warning("No se pudo parsear el body del webhook")
            return JSONResponse(
                status_code=200,
                content={"status": "error", "message": "No data received"}
            )
        
        # Log completo para debugging
        logger.info(f"Datos procesados del webhook: {json.dumps(body, indent=2, cls=DateTimeEncoder)}")
        
        # Procesar en segundo plano para responder rápido al webhook
        background_tasks.add_task(_process_cart_abandoned, body)
        
        # Responder inmediatamente al plugin
        return JSONResponse(
            status_code=200,
            content={"status": "received", "timestamp": datetime.now().isoformat()}
        )
        
    except Exception as e:
        logger.error(f"Error procesando webhook de carrito abandonado: {e}", exc_info=True)
        # Siempre devolver 200 para evitar reintentos del plugin
        return JSONResponse(
            status_code=200,
            content={"status": "error", "message": str(e)}
        )

# Endpoints de estadísticas
@app.get("/api/stats")
async def get_system_stats():
    """Obtener estadísticas generales del sistema"""
    try:
        db_stats = await db_service.get_statistics()
        sync_status = await wc_sync_service.get_sync_status()
        webhook_stats = await webhook_handler.get_webhook_stats()
        
        # Obtener métricas del dashboard si el servicio está disponible
        metrics_stats = {}
        if metrics_service:
            metrics_stats = await metrics_service.get_dashboard_stats()
        
        return {
            "database": db_stats,
            "sync": sync_status,
            "webhooks": webhook_stats,
            "metrics": metrics_stats,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/knowledge/{external_id}")
async def get_knowledge_item(external_id: str):
    """Obtener un elemento específico de la base de conocimiento"""
    try:
        item = await db_service.get_knowledge_by_external_id(external_id)
        if not item:
            raise HTTPException(status_code=404, detail="Elemento no encontrado")
        
        return item
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo elemento: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# FASE 3: Endpoints del Agente de IA
@app.post("/api/chat")
async def chat_endpoint(chat_message: ChatMessage, request: Request):
    """Endpoint REST para chat con el agente IA"""
    try:
        if not hybrid_agent:
            raise HTTPException(status_code=503, detail="Agente no inicializado")
        
        # Detectar plataforma si no se especifica
        # Por defecto, usar "wordpress" para la interfaz web
        if not chat_message.platform or chat_message.platform == "whatsapp":
            # Check headers for platform detection
            user_agent = request.headers.get("user-agent", "").lower()
            x_platform = request.headers.get("x-platform", "").lower()
            
            # Si viene del endpoint /api/chat sin especificar plataforma, es WordPress
            if not chat_message.platform:
                chat_message.platform = "wordpress"
            elif x_platform == "wordpress" or "wordpress" in user_agent:
                chat_message.platform = "wordpress"
        
        # Iniciar tracking de conversación si hay servicio de métricas
        conversation_id = None
        start_time = datetime.now()
        
        if metrics_service:
            conversation_id = await metrics_service.find_or_create_conversation(
                user_id=chat_message.user_id,
                platform=chat_message.platform,
                channel_details={
                    "source": "api",
                    "user_agent": request.headers.get("user-agent", ""),
                    "ip": request.client.host if request.client else None
                },
                timeout_minutes=30  # Conversations timeout after 30 minutes of inactivity
            )
            
            # Registrar mensaje del usuario
            await metrics_service.track_message(
                conversation_id=conversation_id,
                sender_type="user",
                content=chat_message.message
            )
        
        # Procesar mensaje con el agente
        # IMPORTANTE: Incluir session_id para mantener contexto
        session_id = f"{chat_message.platform}_{chat_message.user_id}_{conversation_id or 'default'}"
        
        response = await intelligent_agent.process_message(
            message=chat_message.message,
            user_id=chat_message.user_id,
            platform=chat_message.platform,
            session_id=session_id
        )
        
        # Registrar respuesta del bot si hay métricas
        if metrics_service and conversation_id:
            response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
            
            await metrics_service.track_message(
                conversation_id=conversation_id,
                sender_type="bot",
                content=response,
                response_time_ms=response_time_ms
            )
            
            # Detectar intención y entidades (básico por ahora)
            intent = "general"  # TODO: Extraer del agente
            if "producto" in chat_message.message.lower() or "precio" in chat_message.message.lower():
                intent = "product_inquiry"
            elif "pedido" in chat_message.message.lower() or "orden" in chat_message.message.lower():
                intent = "order_inquiry"
            elif "envío" in chat_message.message.lower():
                intent = "shipping_inquiry"
            
            await metrics_service.track_topic(
                topic=intent,
                category="chat",
                query=chat_message.message[:200],
                resolution_time_minutes=(datetime.now() - start_time).total_seconds() / 60,
                success=True
            )
        
        return {
            "response": response,
            "user_id": chat_message.user_id,
            "platform": chat_message.platform,
            "timestamp": datetime.now().isoformat(),
            "agent_status": "active",
            "conversation_id": conversation_id
        }
        
    except Exception as e:
        logger.error(f"Error en chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/chat/{client_id}")
async def websocket_chat(websocket: WebSocket, client_id: str):
    """WebSocket para chat en tiempo real"""
    await manager.connect(websocket, client_id)
    
    # Enviar mensaje de bienvenida automático
    try:
        welcome_message = await bot_config_service.get_setting("welcome_message", "Hola, ¿en qué puedo ayudarte hoy?")
        bot_name = await bot_config_service.get_setting("bot_name", "Eva")
        
        # Reemplazar "Eva" con el nombre configurado del bot en el mensaje de bienvenida
        if "Eva" in welcome_message and bot_name != "Eva":
            welcome_message = welcome_message.replace("Eva", bot_name)
        
        welcome_data = {
            "type": "welcome",
            "message": welcome_message,
            "bot_name": bot_name,
            "timestamp": datetime.now().isoformat()
        }
        
        await manager.send_personal_message(
            json.dumps(welcome_data, cls=DateTimeEncoder), 
            client_id
        )
        
    except Exception as e:
        logger.warning(f"Error enviando mensaje de bienvenida: {e}")
    
    try:
        while True:
            # Recibir mensaje del cliente
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            user_message = message_data.get("message", "")
            platform = message_data.get("platform", "wordpress")
            
            if not user_message:
                continue
            
            # Procesar con el sistema multi-agente inteligente
            if intelligent_agent:
                try:
                    # Iniciar tracking de conversación si hay servicio de métricas
                    conversation_id = None
                    start_time = datetime.now()
                    
                    if metrics_service:
                        conversation_id = await metrics_service.find_or_create_conversation(
                            user_id=client_id,
                            platform=platform,
                            channel_details={
                                "source": "websocket",
                                "client_id": client_id,
                                "connection_type": "websocket"
                            },
                            timeout_minutes=30  # Conversations timeout after 30 minutes of inactivity
                        )
                        
                        # Registrar mensaje del usuario
                        await metrics_service.track_message(
                            conversation_id=conversation_id,
                            sender_type="user",
                            content=user_message
                        )
                    
                    # IMPORTANTE: Incluir session_id para mantener contexto
                    session_id = f"{platform}_{client_id}_{conversation_id or 'default'}"
                    
                    response = await intelligent_agent.process_message(
                        message=user_message,
                        user_id=client_id,
                        platform=platform,
                        session_id=session_id
                    )
                    
                    # Debug log para verificar formato HTML
                    logger.info(f"Response preview (first 500 chars): {response[:500]}")
                    logger.info(f"Platform used: {platform}")
                    logger.info(f"Contains HTML tags: {bool('<div' in response or '<p' in response)}")
                    
                    # Registrar respuesta del bot si hay métricas
                    if metrics_service and conversation_id:
                        response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                        
                        await metrics_service.track_message(
                            conversation_id=conversation_id,
                            sender_type="bot",
                            content=response,
                            response_time_ms=response_time_ms
                        )
                    
                    # Enviar respuesta
                    response_data = {
                        "type": "agent_response",
                        "message": response,
                        "timestamp": datetime.now().isoformat(),
                        "client_id": client_id
                    }
                    
                    await manager.send_personal_message(
                        json.dumps(response_data, cls=DateTimeEncoder), 
                        client_id
                    )
                    
                except Exception as e:
                    logger.error(f"Error procesando mensaje: {e}")
                    error_response = {
                        "type": "error",
                        "message": "Disculpa, ocurrió un error. ¿Podrías intentar de nuevo?",
                        "timestamp": datetime.now().isoformat()
                    }
                    await manager.send_personal_message(
                        json.dumps(error_response, cls=DateTimeEncoder), 
                        client_id
                    )
            else:
                # Agente no disponible
                fallback_response = {
                    "type": "fallback",
                    "message": "El agente no está disponible en este momento. Por favor, inténtalo más tarde.",
                    "timestamp": datetime.now().isoformat()
                }
                await manager.send_personal_message(
                    json.dumps(fallback_response, cls=DateTimeEncoder), 
                    client_id
                )
                
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info(f"Cliente {client_id} desconectado del chat")

@app.get("/api/chat/stats")
async def get_chat_stats():
    """Obtener estadísticas del agente de chat"""
    try:
        if not hybrid_agent:
            raise HTTPException(status_code=503, detail="Agente no inicializado")
        
        stats = hybrid_agent.get_conversation_stats()
        
        # Agregar métricas si están disponibles
        metrics_data = {}
        if metrics_service:
            metrics_data = await metrics_service.get_dashboard_stats()
        
        return {
            "agent_stats": stats,
            "active_connections": len(manager.active_connections),
            "metrics": metrics_data,
            "system_status": "operational",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/reset/{user_id}")
async def reset_user_conversation(user_id: str):
    """Reiniciar conversación de un usuario específico"""
    try:
        if not hybrid_agent:
            raise HTTPException(status_code=503, detail="Agente no inicializado")
        
        # Por ahora reseteamos toda la conversación 
        # En el futuro se puede hacer por usuario específico
        hybrid_agent.reset_conversation()
        
        return {
            "message": f"Conversación reiniciada para usuario {user_id}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error reiniciando conversación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Endpoints de métricas para el panel de administración
@app.get("/api/admin/conversations")
async def get_conversations(
    limit: int = 20,
    offset: int = 0,
    platform: Optional[str] = None
):
    """Obtener detalles de conversaciones recientes"""
    try:
        # Usar el singleton para obtener el servicio
        from services.metrics_singleton import get_metrics_service
        ms = await get_metrics_service()
        
        conversations = await ms.get_conversation_details(
            limit=limit,
            offset=offset,
            platform=platform
        )
        
        return {
            "conversations": conversations,
            "total": len(conversations),
            "limit": limit,
            "offset": offset,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo conversaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/metrics/summary")
async def get_metrics_summary():
    """Obtener resumen de métricas para el dashboard de admin"""
    try:
        # Usar el singleton para obtener el servicio
        from services.metrics_singleton import get_metrics_service
        ms = await get_metrics_service()
        
        metrics = await ms.get_dashboard_stats()
        
        return {
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo métricas: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/conversations/{conversation_id}/messages")
async def get_conversation_messages(conversation_id: str):
    """Obtener todos los mensajes de una conversación específica"""
    try:
        # Usar el singleton para obtener el servicio
        from services.metrics_singleton import get_metrics_service
        ms = await get_metrics_service()
        
        # Obtener detalles de la conversación
        conversation_details = await ms.get_conversation_by_id(conversation_id)
        if not conversation_details:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        
        # Obtener mensajes de la conversación
        messages = await ms.get_conversation_messages(conversation_id)
        
        return {
            "conversation": conversation_details,
            "messages": messages,
            "total_messages": len(messages),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo mensajes de conversación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/conversations/search")
async def search_conversations(
    query: Optional[str] = None,
    user_id: Optional[str] = None,
    platform: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 50,
    offset: int = 0
):
    """Buscar conversaciones con filtros avanzados"""
    try:
        # Usar el singleton para obtener el servicio
        from services.metrics_singleton import get_metrics_service
        ms = await get_metrics_service()
        
        # Convertir fechas si se proporcionan
        date_from_dt = datetime.fromisoformat(date_from) if date_from else None
        date_to_dt = datetime.fromisoformat(date_to) if date_to else None
        
        # Buscar conversaciones
        results = await ms.search_conversations(
            query=query,
            user_id=user_id,
            platform=platform,
            date_from=date_from_dt,
            date_to=date_to_dt,
            limit=limit,
            offset=offset
        )
        
        return {
            "conversations": results['conversations'],
            "total": results['total'],
            "limit": limit,
            "offset": offset,
            "filters": {
                "query": query,
                "user_id": user_id,
                "platform": platform,
                "date_from": date_from,
                "date_to": date_to
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error buscando conversaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/admin/conversations/{conversation_id}/analytics")
async def get_conversation_analytics(conversation_id: str):
    """Obtener análisis detallado de una conversación"""
    try:
        # Usar el singleton para obtener el servicio
        from services.metrics_singleton import get_metrics_service
        ms = await get_metrics_service()
        
        analytics = await ms.get_conversation_analytics(conversation_id)
        if not analytics:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        
        return {
            "analytics": analytics,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo análisis de conversación: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/conversations/export")
async def export_conversations(
    format: str = "json",
    include_messages: bool = True,
    conversation_ids: Optional[list] = None
):
    """Exportar conversaciones en formato JSON o CSV"""
    try:
        # Usar el singleton para obtener el servicio
        from services.metrics_singleton import get_metrics_service
        ms = await get_metrics_service()
        
        if format not in ["json", "csv"]:
            raise HTTPException(status_code=400, detail="Formato debe ser 'json' o 'csv'")
        
        result = await ms.export_conversations(
            conversation_ids=conversation_ids,
            format=format,
            include_messages=include_messages
        )
        
        if result.get('error'):
            raise HTTPException(status_code=500, detail=result['error'])
        
        if format == "csv":
            from fastapi.responses import Response
            return Response(
                content=result['data'],
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=conversations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
                }
            )
        else:
            return JSONResponse(
                content=result['data'],
                headers={
                    "Content-Disposition": f"attachment; filename=conversations_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                }
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error exportando conversaciones: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Funciones auxiliares
async def _background_sync_all_products(force_update: bool = False):
    """Sincronizar todos los productos en segundo plano"""
    try:
        logger.info(f"🔄 Iniciando sincronización en segundo plano (force_update={force_update})")
        stats = await wc_sync_service.sync_all_products(force_update=force_update)
        logger.info(f"✅ Sincronización completada: {stats}")
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización en segundo plano: {e}")

async def _process_cart_abandoned(webhook_data: Dict[str, Any]):
    """
    Procesar carrito abandonado y enviar mensaje de WhatsApp
    """
    try:
        logger.info("🛒 Procesando carrito abandonado en segundo plano")
        
        # Importar servicios necesarios
        from services.whatsapp_templates import template_manager
        
        # Extraer datos del webhook
        # El formato puede variar según el plugin, vamos a loggear primero
        email = webhook_data.get('email') or webhook_data.get('customer_email')
        phone = webhook_data.get('billing_phone') or webhook_data.get('customer_phone') or webhook_data.get('phone')
        cart_total = webhook_data.get('cart_total') or webhook_data.get('total')
        cart_contents = webhook_data.get('cart_contents') or webhook_data.get('cart_items') or webhook_data.get('items')
        customer_name = webhook_data.get('customer_name') or webhook_data.get('billing_first_name', '')
        checkout_url = webhook_data.get('checkout_url') or webhook_data.get('cart_url')
        
        # Log de datos recibidos
        logger.info(f"📧 Email: {email}")
        logger.info(f"📱 Teléfono: {phone}")
        logger.info(f"💰 Total: {cart_total}")
        logger.info(f"👤 Cliente: {customer_name}")
        
        # Validar teléfono español
        if not phone:
            logger.warning("No se encontró número de teléfono en el webhook")
            return
        
        # Formatear teléfono español
        phone = ''.join(filter(str.isdigit, str(phone)))
        if len(phone) == 9 and phone[0] in '679':
            phone = f'+34{phone}'
        elif not phone.startswith('+34'):
            logger.warning(f"Teléfono no válido para España: {phone}")
            return
        
        # Usar código de descuento fijo EXPRESS (ya existe en WooCommerce)
        discount_code = "DESCUENTOEXPRESS"
        logger.info(f"📌 Usando cupón existente: {discount_code}")
        
        # Función auxiliar para limpiar valores monetarios
        def clean_price(price_str):
            if not price_str:
                return 0
            # Convertir a string y limpiar
            price_clean = str(price_str).replace('€', '').replace(',', '.').strip()
            try:
                return float(price_clean)
            except:
                return 0
        
        # Formatear items del carrito
        formatted_items = []
        
        if isinstance(cart_contents, list):
            for item in cart_contents:
                name = item.get('name') or item.get('product_name') or 'Producto'
                sku = item.get('sku') or item.get('product_sku') or ''
                quantity = item.get('quantity', 1)
                price = item.get('price') or item.get('line_total', 0)
                
                if isinstance(quantity, str):
                    try:
                        quantity = int(quantity)
                    except:
                        quantity = 1
                
                price = clean_price(price)
                total = price * quantity if quantity > 1 else price
                
                formatted_items.append({
                    'name': name,
                    'sku': sku,
                    'quantity': quantity,
                    'total': total
                })
        elif isinstance(cart_contents, dict):
            # Si es un diccionario, intentar extraer items
            for key, item in cart_contents.items():
                if isinstance(item, dict):
                    name = item.get('name') or item.get('product_name') or 'Producto'
                    sku = item.get('sku') or item.get('product_sku') or ''
                    quantity = item.get('quantity', 1)
                    price = item.get('price') or item.get('line_total', 0)
                    
                    if isinstance(quantity, str):
                        try:
                            quantity = int(quantity)
                        except:
                            quantity = 1
                    
                    formatted_items.append({
                        'name': name,
                        'sku': sku,
                        'quantity': quantity,
                        'total': clean_price(price)
                    })
        
        # URL fija del checkout
        checkout_url = "https://elcorteelectrico.com/checkout"
        
        # Limpiar el total del carrito (quitar símbolo de moneda y convertir a float)
        if cart_total:
            # Quitar símbolo de euro y espacios
            cart_total_clean = str(cart_total).replace('€', '').replace(',', '.').strip()
            try:
                cart_total_float = float(cart_total_clean)
            except:
                cart_total_float = 0
        else:
            cart_total_float = 0
        
        # Preparar datos para la plantilla
        cart_data = {
            "discount_code": discount_code,
            "items": formatted_items if formatted_items else [{"name": "Productos del carrito", "quantity": 1, "total": cart_total_float}],
            "total": cart_total_float,
            "cart_url": checkout_url,
            "customer_name": customer_name
        }
        
        # Enviar mensaje de WhatsApp
        result = await template_manager.send_cart_recovery(
            phone_number=phone,
            cart_data=cart_data
        )
        
        if result and result.get('messages'):
            logger.info(f"✅ Mensaje de recuperación enviado a {phone}")
            logger.info(f"   Código de descuento: {discount_code}")
            logger.info(f"   Message ID: {result['messages'][0].get('id')}")
        else:
            logger.error(f"Error enviando mensaje de recuperación: {result}")
        
    except Exception as e:
        logger.error(f"Error procesando carrito abandonado: {e}", exc_info=True)

async def _process_whatsapp_webhook(webhook_data: Dict[str, Any]):
    """Procesar webhook de WhatsApp en segundo plano"""
    try:
        logger.info("📱 Procesando webhook de WhatsApp en segundo plano")
        
        # Procesar el webhook
        result = await whatsapp_webhook_handler.process_webhook(webhook_data)
        
        # Si hay mensajes entrantes, procesarlos con el agente
        if "entry" in webhook_data:
            for entry in webhook_data.get("entry", []):
                for change in entry.get("changes", []):
                    value = change.get("value", {})
                    
                    # Procesar mensajes entrantes
                    if "messages" in value:
                        for message in value["messages"]:
                            await _process_whatsapp_message(message, value)
        
        logger.info(f"✅ Webhook de WhatsApp procesado: {result}")
        
    except Exception as e:
        logger.error(f"❌ Error procesando webhook de WhatsApp: {e}")

async def _process_whatsapp_message(message_data: Dict[str, Any], value_data: Dict[str, Any]):
    """Procesar mensaje individual de WhatsApp con el agente"""
    try:
        if not hybrid_agent:
            logger.error("Agente no inicializado para procesar mensaje de WhatsApp")
            return
        
        # Extraer información del mensaje
        from_number = message_data.get("from", "")
        message_type = message_data.get("type", "")
        
        # Por ahora solo procesamos mensajes de texto
        if message_type == "text":
            text_content = message_data.get("text", {}).get("body", "")
            
            # Iniciar tracking de conversación si hay servicio de métricas
            conversation_id = None
            start_time = datetime.now()
            
            if metrics_service:
                conversation_id = await metrics_service.start_conversation(
                    user_id=from_number,
                    platform="whatsapp",
                    channel_details={
                        "source": "360dialog",
                        "message_id": message_data.get("id"),
                        "phone": from_number
                    }
                )
                
                # Registrar mensaje del usuario
                await metrics_service.track_message(
                    conversation_id=conversation_id,
                    sender_type="user",
                    content=text_content
                )
            
            # Procesar con el agente
            response = await hybrid_agent.process_message(
                message=text_content,
                user_id=from_number,
                platform="whatsapp"
            )
            
            # Enviar respuesta
            await whatsapp_service.send_text_message(
                to=from_number,
                text=response,
                reply_to=message_data.get("id")
            )
            
            # Registrar respuesta del bot si hay métricas
            if metrics_service and conversation_id:
                response_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
                
                await metrics_service.track_message(
                    conversation_id=conversation_id,
                    sender_type="bot",
                    content=response,
                    response_time_ms=response_time_ms
                )
                
                # Detectar intención básica
                intent = "general"
                if "producto" in text_content.lower() or "precio" in text_content.lower():
                    intent = "product_inquiry"
                elif "pedido" in text_content.lower() or "orden" in text_content.lower():
                    intent = "order_inquiry"
                elif "envío" in text_content.lower():
                    intent = "shipping_inquiry"
                
                await metrics_service.track_topic(
                    topic=intent,
                    category="whatsapp",
                    query=text_content[:200],
                    resolution_time_minutes=(datetime.now() - start_time).total_seconds() / 60,
                    success=True
                )
            
            logger.info(f"✅ Mensaje de WhatsApp procesado y respondido: {from_number}")
        
    except Exception as e:
        logger.error(f"Error procesando mensaje de WhatsApp: {e}")

# Manejadores de errores globales
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Manejador global de excepciones"""
    logger.error(f"Error no manejado en {request.url}: {exc}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Error interno del servidor",
            "detail": str(exc) if settings.DEBUG else "Error interno",
            "timestamp": datetime.now().isoformat()
        }
    )

# Función principal
if __name__ == "__main__":
    print("🚀 Iniciando Sistema de Atención al Cliente IA - FASE 3")
    print("🔍 Búsqueda Híbrida + Webhooks + Sincronización + AGENTE IA")
    print("=" * 70)
    print("🌐 Dashboard: http://localhost:8080/")
    print("📚 API Docs: http://localhost:8080/docs")
    print("🔗 Webhooks WooCommerce: http://localhost:8080/api/webhooks/woocommerce")
    print("📱 Webhooks WhatsApp: http://localhost:8080/api/webhooks/whatsapp")
    print("💬 Chat API: http://localhost:8080/api/chat")
    print("🔌 WebSocket: ws://localhost:8080/ws/chat/{client_id}")
    print("=" * 70)
    
    uvicorn.run(
        "app:app",
        host="0.0.0.0", 
        port=8080,
        reload=True,
        log_level="info"
    ) 