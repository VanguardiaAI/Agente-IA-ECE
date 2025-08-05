#!/usr/bin/env python3
"""
Interfaz Web Mejorada para el Agente de Atención al Cliente
Con mejor UX y funcionalidades adicionales
"""

import asyncio
import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

from src.agent.hybrid_agent import HybridCustomerAgent
from dotenv import load_dotenv

# Cargar configuración
load_dotenv("env.agent")

# Configuración de FastAPI
app = FastAPI(
    title="Asistente Virtual Eva - El Corteelectrico.com",
    description="Interfaz web para el agente de atención al cliente",
    version="2.0.0"
)

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Almacenar sesiones de conversación
conversation_sessions: Dict[str, HybridCustomerAgent] = {}

# Estadísticas globales
global_stats = {
    "total_conversations": 0,
    "total_messages": 0,
    "most_common_intents": {},
    "start_time": datetime.now()
}

@app.on_event("startup")
async def startup_event():
    """Eventos de inicio de la aplicación"""
    print("🚀 Iniciando interfaz web mejorada...")
    print("🌐 Eva - Asistente Virtual de Atención al Cliente")
    print("=" * 50)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal con interfaz mejorada"""
    return templates.TemplateResponse("enhanced_chat.html", {
        "request": request,
        "title": "Eva - Asistente Virtual"
    })

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Endpoint para conversación mejorada"""
    try:
        data = await request.json()
        message = data.get("message", "").strip()
        session_id = data.get("session_id")
        
        if not message:
            raise HTTPException(status_code=400, detail="Mensaje vacío")
        
        # Crear o recuperar sesión
        if not session_id or session_id not in conversation_sessions:
            session_id = str(uuid.uuid4())
            agent = HybridCustomerAgent()
            await agent.initialize()
            conversation_sessions[session_id] = agent
            global_stats["total_conversations"] += 1
            print(f"🆕 Nueva sesión: {session_id}")
        else:
            agent = conversation_sessions[session_id]
        
        # Procesar mensaje
        response = await agent.process_message(message, user_id=session_id)
        
        # Actualizar estadísticas
        global_stats["total_messages"] += 1
        intent = getattr(agent.conversation_state.context, 'current_intent', 'unknown')
        if intent in global_stats["most_common_intents"]:
            global_stats["most_common_intents"][intent] += 1
        else:
            global_stats["most_common_intents"][intent] = 1
        
        # Obtener estadísticas de la conversación
        conversation_stats = agent.get_conversation_stats()
        
        return JSONResponse({
            "success": True,
            "response": response,
            "session_id": session_id,
            "conversation_stats": conversation_stats,
            "detected_intent": intent,
            "confidence": getattr(agent.conversation_state.context, 'confidence', 0.0),
            "entities": agent.conversation_state.context.extracted_entities,
            "turn_count": agent.conversation_state.context.turn_count
        })
        
    except Exception as e:
        print(f"❌ Error en chat: {e}")
        return JSONResponse({
            "success": False,
            "error": str(e),
            "response": "Lo siento, ocurrió un error técnico. ¿Podrías intentar de nuevo?"
        }, status_code=500)

@app.post("/api/reset")
async def reset_conversation(request: Request):
    """Reset de conversación"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if session_id and session_id in conversation_sessions:
            del conversation_sessions[session_id]
            print(f"🗑️ Sesión eliminada: {session_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Conversación reiniciada"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/stats")
async def get_stats():
    """Estadísticas del sistema"""
    active_sessions = len(conversation_sessions)
    uptime = datetime.now() - global_stats["start_time"]
    
    return JSONResponse({
        "global_stats": global_stats,
        "active_sessions": active_sessions,
        "uptime_seconds": uptime.total_seconds(),
        "avg_messages_per_conversation": (
            global_stats["total_messages"] / max(global_stats["total_conversations"], 1)
        )
    })

@app.get("/api/health")
async def health_check():
    """Verificación de salud del sistema"""
    # Probar una sesión de ejemplo
    test_agent = HybridCustomerAgent()
    try:
        await test_agent.initialize()
        mcp_connected = test_agent.mcp_tools is not None
    except Exception as e:
        print(f"⚠️ Error en health check: {e}")
        mcp_connected = False
    
    return JSONResponse({
        "status": "healthy",
        "mcp_connected": mcp_connected,
        "active_sessions": len(conversation_sessions),
        "timestamp": datetime.now().isoformat()
    })

# Crear el template HTML
@app.on_event("startup")
async def create_template():
    """Crear template HTML si no existe"""
    os.makedirs("templates", exist_ok=True)
    
    template_html = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .chat-container {
            width: 90%;
            max-width: 800px;
            height: 600px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            background: linear-gradient(45deg, #ff6b6b, #ffa726);
            color: white;
            padding: 20px;
            text-align: center;
            position: relative;
        }
        
        .chat-header h1 {
            font-size: 1.5rem;
            margin-bottom: 5px;
        }
        
        .chat-header p {
            opacity: 0.9;
            font-size: 0.9rem;
        }
        
        .status-indicator {
            position: absolute;
            top: 20px;
            right: 20px;
            width: 12px;
            height: 12px;
            background: #4CAF50;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            animation: fadeInUp 0.3s ease;
        }
        
        @keyframes fadeInUp {
            from {
                opacity: 0;
                transform: translateY(10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .message.user {
            justify-content: flex-end;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: #007bff;
            color: white;
            border-bottom-right-radius: 5px;
        }
        
        .message.bot .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 5px;
        }
        
        .message-info {
            font-size: 0.7rem;
            color: #666;
            margin-top: 5px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .intent-badge {
            background: #e3f2fd;
            color: #1976d2;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 0.6rem;
        }
        
        .chat-input-container {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .chat-input-form {
            display: flex;
            gap: 10px;
        }
        
        .chat-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 1rem;
            outline: none;
            transition: border-color 0.3s ease;
        }
        
        .chat-input:focus {
            border-color: #007bff;
        }
        
        .send-button {
            background: #007bff;
            color: white;
            border: none;
            border-radius: 50%;
            width: 45px;
            height: 45px;
            cursor: pointer;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .send-button:hover {
            background: #0056b3;
            transform: scale(1.1);
        }
        
        .send-button:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        .typing-indicator {
            display: none;
            align-items: center;
            gap: 5px;
            padding: 10px 16px;
            background: white;
            border-radius: 18px;
            border: 1px solid #e0e0e0;
            margin-bottom: 15px;
        }
        
        .typing-dots {
            display: flex;
            gap: 3px;
        }
        
        .typing-dot {
            width: 6px;
            height: 6px;
            background: #007bff;
            border-radius: 50%;
            animation: typing 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes typing {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .stats-panel {
            background: rgba(255,255,255,0.1);
            padding: 10px;
            margin: 10px 20px;
            border-radius: 10px;
            font-size: 0.8rem;
            color: white;
        }
        
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .control-btn {
            background: rgba(255,255,255,0.2);
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 15px;
            cursor: pointer;
            font-size: 0.7rem;
            transition: background 0.3s ease;
        }
        
        .control-btn:hover {
            background: rgba(255,255,255,0.3);
        }
        
        .welcome-message {
            text-align: center;
            color: #666;
            font-style: italic;
            margin: 20px 0;
        }
        
        @media (max-width: 768px) {
            .chat-container {
                width: 95%;
                height: 90vh;
                border-radius: 10px;
            }
            
            .message-content {
                max-width: 85%;
            }
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            <div class="status-indicator" id="statusIndicator"></div>
            <h1>🌟 Eva - Asistente Virtual</h1>
            <p>Especializada en velas aromáticas y perfumes</p>
            <div class="stats-panel" id="statsPanel" style="display: none;">
                <div>Sesión: <span id="sessionId">Nueva</span></div>
                <div>Mensajes: <span id="messageCount">0</span> | Intención: <span id="currentIntent">general</span></div>
                <div class="controls">
                    <button class="control-btn" onclick="resetConversation()">🔄 Nueva Conversación</button>
                    <button class="control-btn" onclick="toggleStats()">📊 Estadísticas</button>
                </div>
            </div>
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="welcome-message">
                ¡Hola! Soy Eva, tu asistente virtual. Estoy aquí para ayudarte con todo lo relacionado con nuestra tienda de velas aromáticas y perfumes. ¿En qué puedo ayudarte hoy? 😊
            </div>
        </div>
        
        <div class="typing-indicator" id="typingIndicator">
            <span>Eva está escribiendo</span>
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
        
        <div class="chat-input-container">
            <form class="chat-input-form" id="chatForm">
                <input 
                    type="text" 
                    class="chat-input" 
                    id="messageInput" 
                    placeholder="Escribe tu mensaje aquí..."
                    autocomplete="off"
                    maxlength="500"
                >
                <button type="submit" class="send-button" id="sendButton">
                    ➤
                </button>
            </form>
        </div>
    </div>

    <script>
        let sessionId = null;
        let messageCount = 0;
        let statsVisible = false;
        
        const chatMessages = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const typingIndicator = document.getElementById('typingIndicator');
        const chatForm = document.getElementById('chatForm');
        
        // Enfocar input al cargar
        messageInput.focus();
        
        // Manejar envío de formulario
        chatForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await sendMessage();
        });
        
        // Enviar mensaje
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            // Deshabilitar input
            messageInput.disabled = true;
            sendButton.disabled = true;
            
            // Mostrar mensaje del usuario
            addMessage('user', message);
            messageInput.value = '';
            
            // Mostrar indicador de escritura
            showTypingIndicator();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    sessionId = data.session_id;
                    messageCount = data.turn_count;
                    
                    // Mostrar respuesta del bot
                    addMessage('bot', data.response, {
                        intent: data.detected_intent,
                        confidence: data.confidence,
                        entities: data.entities
                    });
                    
                    // Actualizar estadísticas
                    updateStats(data);
                } else {
                    addMessage('bot', data.response || 'Error al procesar el mensaje');
                }
                
            } catch (error) {
                console.error('Error:', error);
                addMessage('bot', 'Lo siento, ocurrió un error de conexión. ¿Podrías intentar de nuevo?');
            } finally {
                // Rehabilitar input
                hideTypingIndicator();
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
            }
        }
        
        // Agregar mensaje al chat
        function addMessage(sender, content, metadata = {}) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const contentDiv = document.createElement('div');
            contentDiv.className = 'message-content';
            contentDiv.textContent = content;
            
            messageDiv.appendChild(contentDiv);
            
            // Agregar información adicional para mensajes del bot
            if (sender === 'bot' && metadata.intent) {
                const infoDiv = document.createElement('div');
                infoDiv.className = 'message-info';
                
                const intentBadge = document.createElement('span');
                intentBadge.className = 'intent-badge';
                intentBadge.textContent = metadata.intent;
                
                const confidenceText = document.createElement('span');
                confidenceText.textContent = `Confianza: ${Math.round(metadata.confidence * 100)}%`;
                
                infoDiv.appendChild(intentBadge);
                infoDiv.appendChild(confidenceText);
                
                if (metadata.entities && Object.keys(metadata.entities).length > 0) {
                    const entitiesText = document.createElement('span');
                    entitiesText.textContent = `Entidades: ${Object.keys(metadata.entities).join(', ')}`;
                    infoDiv.appendChild(entitiesText);
                }
                
                messageDiv.appendChild(infoDiv);
            }
            
            chatMessages.appendChild(messageDiv);
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        // Mostrar/ocultar indicador de escritura
        function showTypingIndicator() {
            typingIndicator.style.display = 'flex';
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        function hideTypingIndicator() {
            typingIndicator.style.display = 'none';
        }
        
        // Actualizar estadísticas
        function updateStats(data) {
            document.getElementById('sessionId').textContent = data.session_id.substring(0, 8);
            document.getElementById('messageCount').textContent = data.turn_count;
            document.getElementById('currentIntent').textContent = data.detected_intent;
        }
        
        // Toggle estadísticas
        function toggleStats() {
            const statsPanel = document.getElementById('statsPanel');
            statsVisible = !statsVisible;
            statsPanel.style.display = statsVisible ? 'block' : 'none';
        }
        
        // Reset conversación
        async function resetConversation() {
            if (sessionId) {
                try {
                    await fetch('/api/reset', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({
                            session_id: sessionId
                        })
                    });
                } catch (error) {
                    console.error('Error resetting conversation:', error);
                }
            }
            
            // Limpiar chat
            chatMessages.innerHTML = `
                <div class="welcome-message">
                    ¡Hola! Soy Eva, tu asistente virtual. Estoy aquí para ayudarte con todo lo relacionado con nuestra tienda de velas aromáticas y perfumes. ¿En qué puedo ayudarte hoy? 😊
                </div>
            `;
            
            sessionId = null;
            messageCount = 0;
            document.getElementById('sessionId').textContent = 'Nueva';
            document.getElementById('messageCount').textContent = '0';
            document.getElementById('currentIntent').textContent = 'general';
            
            messageInput.focus();
        }
        
        // Verificar estado del servidor
        async function checkHealth() {
            try {
                const response = await fetch('/api/health');
                const data = await response.json();
                
                const indicator = document.getElementById('statusIndicator');
                if (data.mcp_connected) {
                    indicator.style.background = '#4CAF50';
                    indicator.title = 'Conectado a WooCommerce';
                } else {
                    indicator.style.background = '#FF9800';
                    indicator.title = 'Modo demostración';
                }
            } catch (error) {
                const indicator = document.getElementById('statusIndicator');
                indicator.style.background = '#f44336';
                indicator.title = 'Error de conexión';
            }
        }
        
        // Verificar estado cada 30 segundos
        checkHealth();
        setInterval(checkHealth, 30000);
        
        // Manejar Enter para enviar
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    </script>
</body>
</html>"""
    
    with open("templates/enhanced_chat.html", "w", encoding="utf-8") as f:
        f.write(template_html)

if __name__ == "__main__":
    print("🚀 Iniciando interfaz web mejorada...")
    print("🌐 Accede a: http://localhost:8001")
    print("📱 Interfaz responsiva para móviles")
    print("🎯 Con detección inteligente de intenciones")
    print("=" * 50)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        log_level="info"
    )