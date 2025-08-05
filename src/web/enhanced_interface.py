#!/usr/bin/env python3
"""
Interfaz Web Mejorada para el Sistema Híbrido de Atención al Cliente
Con capacidades multi-agente y mejor experiencia de usuario
"""

import asyncio
import os
import uuid
import json
from datetime import datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import uvicorn

from src.agent.hybrid_agent import HybridCustomerAgent
from dotenv import load_dotenv

# Cargar configuración
load_dotenv("env.agent")

# Configuración de FastAPI
app = FastAPI(
    title="Eva - Asistente Virtual Híbrido",
    description="Sistema avanzado de atención al cliente con IA multi-agente",
    version="3.0.0"
)

# Configurar templates
templates = Jinja2Templates(directory="templates")

# Almacenar sesiones de conversación
conversation_sessions: Dict[str, HybridCustomerAgent] = {}

# Estadísticas globales mejoradas
global_stats = {
    "total_conversations": 0,
    "total_messages": 0,
    "strategy_usage": {
        "quick_response": 0,
        "tool_assisted": 0,
        "multi_agent": 0,
        "standard_response": 0
    },
    "most_common_intents": {},
    "avg_response_time": 0.0,
    "start_time": datetime.now(),
    "tools_used": {},
    "customer_satisfaction": []
}

@app.on_event("startup")
async def startup_event():
    """Eventos de inicio de la aplicación"""
    print("🚀 Iniciando interfaz web híbrida...")
    print("🤖 Eva - Sistema Multi-Agente de Atención al Cliente")
    print("=" * 60)
    
    # Crear directorio de templates si no existe
    os.makedirs("templates", exist_ok=True)
    await create_enhanced_template()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Página principal con interfaz híbrida"""
    return templates.TemplateResponse("hybrid_chat.html", {
        "request": request,
        "title": "Eva - Asistente Virtual Híbrido"
    })

@app.post("/api/chat")
async def chat_endpoint(request: Request):
    """Endpoint para conversación híbrida"""
    try:
        data = await request.json()
        message = data.get("message", "").strip()
        session_id = data.get("session_id")
        user_id = data.get("user_id", "web_user")
        
        if not message:
            raise HTTPException(status_code=400, detail="Mensaje vacío")
        
        # Crear o recuperar sesión
        if not session_id or session_id not in conversation_sessions:
            session_id = str(uuid.uuid4())
            agent = HybridCustomerAgent()
            await agent.initialize()
            conversation_sessions[session_id] = agent
            global_stats["total_conversations"] += 1
            print(f"🆕 Nueva sesión híbrida: {session_id}")
        else:
            agent = conversation_sessions[session_id]
        
        # Medir tiempo de respuesta
        start_time = datetime.now()
        
        # Procesar mensaje con el agente híbrido
        response = await agent.process_message(message, user_id=user_id)
        
        # Calcular tiempo de respuesta
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Actualizar estadísticas globales
        global_stats["total_messages"] += 1
        
        # Actualizar tiempo promedio de respuesta
        if global_stats["avg_response_time"] == 0:
            global_stats["avg_response_time"] = response_time
        else:
            global_stats["avg_response_time"] = (
                global_stats["avg_response_time"] * 0.9 + response_time * 0.1
            )
        
        # Obtener estadísticas de la conversación
        conversation_stats = agent.get_conversation_stats()
        
        # Obtener la última estrategia usada
        last_strategy = "standard_response"
        if agent.conversation_state.conversation_history:
            last_entry = agent.conversation_state.conversation_history[-1]
            last_strategy = last_entry.get("strategy", "standard_response")
        
        # Actualizar estadísticas de estrategia
        if last_strategy in global_stats["strategy_usage"]:
            global_stats["strategy_usage"][last_strategy] += 1
        
        return JSONResponse({
            "success": True,
            "response": response,
            "session_id": session_id,
            "conversation_stats": conversation_stats,
            "strategy_used": last_strategy,
            "response_time": response_time,
            "multi_agent_enabled": agent.enable_multi_agent,
            "tools_available": conversation_stats.get("tools_available", 0),
            "turn_count": conversation_stats.get("turn_count", 0)
        })
        
    except Exception as e:
        print(f"❌ Error en chat híbrido: {e}")
        import traceback
        traceback.print_exc()
        
        return JSONResponse({
            "success": False,
            "error": str(e),
            "response": "Disculpa, estoy teniendo dificultades técnicas. ¿Podrías intentar de nuevo? 😊"
        }, status_code=500)

@app.post("/api/reset")
async def reset_conversation(request: Request):
    """Reset de conversación"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        
        if session_id and session_id in conversation_sessions:
            agent = conversation_sessions[session_id]
            agent.reset_conversation()
            print(f"🔄 Conversación reiniciada: {session_id}")
        
        return JSONResponse({
            "success": True,
            "message": "Conversación reiniciada exitosamente"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.post("/api/feedback")
async def submit_feedback(request: Request):
    """Recibir feedback del usuario"""
    try:
        data = await request.json()
        session_id = data.get("session_id")
        rating = data.get("rating", 3)  # 1-5
        comment = data.get("comment", "")
        
        # Guardar feedback
        feedback_entry = {
            "session_id": session_id,
            "rating": rating,
            "comment": comment,
            "timestamp": datetime.now().isoformat()
        }
        
        global_stats["customer_satisfaction"].append(feedback_entry)
        
        # Mantener solo los últimos 100 feedbacks
        if len(global_stats["customer_satisfaction"]) > 100:
            global_stats["customer_satisfaction"] = global_stats["customer_satisfaction"][-100:]
        
        return JSONResponse({
            "success": True,
            "message": "Gracias por tu feedback"
        })
        
    except Exception as e:
        return JSONResponse({
            "success": False,
            "error": str(e)
        }, status_code=500)

@app.get("/api/stats")
async def get_stats():
    """Estadísticas del sistema híbrido"""
    active_sessions = len(conversation_sessions)
    uptime = datetime.now() - global_stats["start_time"]
    
    # Calcular satisfacción promedio
    avg_satisfaction = 0.0
    if global_stats["customer_satisfaction"]:
        avg_satisfaction = sum(f["rating"] for f in global_stats["customer_satisfaction"]) / len(global_stats["customer_satisfaction"])
    
    return JSONResponse({
        "global_stats": global_stats,
        "active_sessions": active_sessions,
        "uptime_seconds": uptime.total_seconds(),
        "avg_messages_per_conversation": (
            global_stats["total_messages"] / max(global_stats["total_conversations"], 1)
        ),
        "avg_satisfaction": avg_satisfaction,
        "system_type": "hybrid_multi_agent"
    })

@app.get("/api/health")
async def health_check():
    """Verificación de salud del sistema híbrido"""
    try:
        # Probar una sesión de ejemplo
        test_agent = HybridCustomerAgent()
        await test_agent.initialize()
        
        health_status = {
            "status": "healthy",
            "mcp_connected": test_agent.mcp_tools is not None,
            "multi_agent_enabled": test_agent.enable_multi_agent,
            "active_sessions": len(conversation_sessions),
            "timestamp": datetime.now().isoformat(),
            "tools_count": len(test_agent.mcp_tools) if test_agent.mcp_tools else 0
        }
        
        return JSONResponse(health_status)
        
    except Exception as e:
        return JSONResponse({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }, status_code=500)

@app.get("/api/session/{session_id}/stats")
async def get_session_stats(session_id: str):
    """Estadísticas de una sesión específica"""
    if session_id not in conversation_sessions:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    
    agent = conversation_sessions[session_id]
    stats = agent.get_conversation_stats()
    
    return JSONResponse({
        "session_id": session_id,
        "stats": stats,
        "conversation_history_length": len(agent.conversation_state.conversation_history),
        "multi_agent_enabled": agent.enable_multi_agent
    })

async def create_enhanced_template():
    """Crear template HTML mejorado para el sistema híbrido"""
    
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
            padding: 20px;
        }
        
        .chat-container {
            width: 100%;
            max-width: 900px;
            height: 700px;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        
        .chat-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
            position: relative;
        }
        
        .chat-header h1 {
            font-size: 24px;
            margin-bottom: 5px;
        }
        
        .chat-header p {
            opacity: 0.9;
            font-size: 14px;
        }
        
        .status-indicator {
            position: absolute;
            top: 20px;
            right: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .status-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% { opacity: 1; }
            50% { opacity: 0.5; }
            100% { opacity: 1; }
        }
        
        .chat-stats {
            background: rgba(255,255,255,0.1);
            padding: 10px 20px;
            display: flex;
            justify-content: space-between;
            font-size: 12px;
        }
        
        .chat-messages {
            flex: 1;
            padding: 20px;
            overflow-y: auto;
            background: #f8f9fa;
        }
        
        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
            gap: 10px;
        }
        
        .message.user {
            flex-direction: row-reverse;
        }
        
        .message-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: bold;
            color: white;
            font-size: 14px;
        }
        
        .message.user .message-avatar {
            background: #667eea;
        }
        
        .message.assistant .message-avatar {
            background: #764ba2;
        }
        
        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            position: relative;
        }
        
        .message.user .message-content {
            background: #667eea;
            color: white;
            border-bottom-right-radius: 4px;
        }
        
        .message.assistant .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
            border-bottom-left-radius: 4px;
        }
        
        .message-meta {
            font-size: 11px;
            opacity: 0.7;
            margin-top: 5px;
        }
        
        .strategy-badge {
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 2px 6px;
            border-radius: 10px;
            font-size: 10px;
            margin-left: 5px;
        }
        
        .chat-input {
            padding: 20px;
            background: white;
            border-top: 1px solid #e0e0e0;
        }
        
        .input-container {
            display: flex;
            gap: 10px;
            align-items: flex-end;
        }
        
        .message-input {
            flex: 1;
            padding: 12px 16px;
            border: 2px solid #e0e0e0;
            border-radius: 25px;
            font-size: 14px;
            resize: none;
            max-height: 100px;
            min-height: 44px;
        }
        
        .message-input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .send-button {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 50%;
            width: 44px;
            height: 44px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: transform 0.2s;
        }
        
        .send-button:hover {
            transform: scale(1.05);
        }
        
        .send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        
        .typing-indicator {
            display: none;
            padding: 10px 16px;
            background: white;
            border: 1px solid #e0e0e0;
            border-radius: 18px;
            margin-bottom: 15px;
            max-width: 70%;
        }
        
        .typing-dots {
            display: flex;
            gap: 4px;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: #999;
            animation: typing 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) { animation-delay: 0.2s; }
        .typing-dot:nth-child(3) { animation-delay: 0.4s; }
        
        @keyframes typing {
            0%, 60%, 100% { transform: translateY(0); }
            30% { transform: translateY(-10px); }
        }
        
        .action-buttons {
            display: flex;
            gap: 10px;
            margin-top: 10px;
        }
        
        .action-button {
            background: #f0f0f0;
            border: 1px solid #ddd;
            border-radius: 20px;
            padding: 8px 16px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .action-button:hover {
            background: #e0e0e0;
        }
        
        .feedback-modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1000;
            align-items: center;
            justify-content: center;
        }
        
        .feedback-content {
            background: white;
            padding: 30px;
            border-radius: 15px;
            max-width: 400px;
            width: 90%;
        }
        
        .rating-stars {
            display: flex;
            gap: 5px;
            justify-content: center;
            margin: 20px 0;
        }
        
        .star {
            font-size: 24px;
            color: #ddd;
            cursor: pointer;
            transition: color 0.2s;
        }
        
        .star.active {
            color: #ffd700;
        }
        
        @media (max-width: 768px) {
            .chat-container {
                height: 100vh;
                border-radius: 0;
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
            <h1>🌟 Eva - Asistente Virtual Híbrido</h1>
            <p>Sistema Multi-Agente de Atención al Cliente</p>
            <div class="status-indicator">
                <div class="status-dot"></div>
                <span>En línea</span>
            </div>
        </div>
        
        <div class="chat-stats">
            <span>Estrategia: <span id="current-strategy">Adaptativa</span></span>
            <span>Herramientas: <span id="tools-count">0</span></span>
            <span>Tiempo: <span id="response-time">0ms</span></span>
        </div>
        
        <div class="chat-messages" id="chat-messages">
            <div class="message assistant">
                <div class="message-avatar">C</div>
                <div class="message-content">
                    ¡Hola! Soy Eva, tu asistente virtual híbrido 🌟<br><br>
                    Estoy aquí para ayudarte con todo lo relacionado con nuestra tienda de velas aromáticas y perfumes. 
                    Puedo ayudarte con:
                    <br>• 🛍️ Búsqueda de productos
                    <br>• 📦 Estado de pedidos
                    <br>• 💳 Información de pagos y envíos
                    <br>• 🔄 Devoluciones y cambios
                    <br>• ❓ Cualquier duda que tengas
                    <br><br>¿En qué puedo ayudarte hoy?
                    <div class="message-meta">
                        Sistema híbrido activado <span class="strategy-badge">multi-agent</span>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="typing-indicator" id="typing-indicator">
            <div class="typing-dots">
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
                <div class="typing-dot"></div>
            </div>
        </div>
        
        <div class="chat-input">
            <div class="input-container">
                <textarea 
                    id="message-input" 
                    class="message-input" 
                    placeholder="Escribe tu mensaje aquí..."
                    rows="1"
                ></textarea>
                <button id="send-button" class="send-button">
                    ➤
                </button>
            </div>
            <div class="action-buttons">
                <button class="action-button" onclick="resetConversation()">🔄 Nueva conversación</button>
                <button class="action-button" onclick="showFeedback()">⭐ Calificar</button>
                <button class="action-button" onclick="showStats()">📊 Estadísticas</button>
            </div>
        </div>
    </div>
    
    <!-- Modal de feedback -->
    <div class="feedback-modal" id="feedback-modal">
        <div class="feedback-content">
            <h3>¿Cómo fue tu experiencia?</h3>
            <div class="rating-stars" id="rating-stars">
                <span class="star" data-rating="1">⭐</span>
                <span class="star" data-rating="2">⭐</span>
                <span class="star" data-rating="3">⭐</span>
                <span class="star" data-rating="4">⭐</span>
                <span class="star" data-rating="5">⭐</span>
            </div>
            <textarea id="feedback-comment" placeholder="Comentarios opcionales..." style="width: 100%; height: 80px; margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 5px;"></textarea>
            <div style="display: flex; gap: 10px; justify-content: flex-end;">
                <button onclick="closeFeedback()" style="padding: 8px 16px; border: 1px solid #ddd; background: white; border-radius: 5px; cursor: pointer;">Cancelar</button>
                <button onclick="submitFeedback()" style="padding: 8px 16px; background: #667eea; color: white; border: none; border-radius: 5px; cursor: pointer;">Enviar</button>
            </div>
        </div>
    </div>

    <script>
        let sessionId = null;
        let selectedRating = 0;
        
        // Elementos del DOM
        const messagesContainer = document.getElementById('chat-messages');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        const typingIndicator = document.getElementById('typing-indicator');
        
        // Event listeners
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        messageInput.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 100) + 'px';
        });
        
        sendButton.addEventListener('click', sendMessage);
        
        // Configurar rating stars
        document.querySelectorAll('.star').forEach(star => {
            star.addEventListener('click', function() {
                selectedRating = parseInt(this.dataset.rating);
                updateStars();
            });
        });
        
        function updateStars() {
            document.querySelectorAll('.star').forEach((star, index) => {
                star.classList.toggle('active', index < selectedRating);
            });
        }
        
        async function sendMessage() {
            const message = messageInput.value.trim();
            if (!message) return;
            
            // Deshabilitar input
            messageInput.disabled = true;
            sendButton.disabled = true;
            
            // Agregar mensaje del usuario
            addMessage(message, 'user');
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Mostrar indicador de escritura
            showTyping();
            
            try {
                const response = await fetch('/api/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        message: message,
                        session_id: sessionId,
                        user_id: 'web_user'
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    sessionId = data.session_id;
                    
                    // Actualizar estadísticas en la UI
                    updateStats(data);
                    
                    // Agregar respuesta del asistente
                    addMessage(data.response, 'assistant', data.strategy_used, data.response_time);
                } else {
                    addMessage(data.response || 'Error en la comunicación', 'assistant', 'error');
                }
                
            } catch (error) {
                console.error('Error:', error);
                addMessage('Lo siento, ocurrió un error de conexión. ¿Podrías intentar de nuevo?', 'assistant', 'error');
            } finally {
                hideTyping();
                messageInput.disabled = false;
                sendButton.disabled = false;
                messageInput.focus();
            }
        }
        
        function addMessage(content, sender, strategy = null, responseTime = null) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${sender}`;
            
            const avatar = sender === 'user' ? 'U' : 'C';
            const avatarClass = sender === 'user' ? 'user' : 'assistant';
            
            let metaInfo = '';
            if (strategy && sender === 'assistant') {
                const strategyBadge = `<span class="strategy-badge">${strategy}</span>`;
                const timeInfo = responseTime ? ` • ${(responseTime * 1000).toFixed(0)}ms` : '';
                metaInfo = `<div class="message-meta">Estrategia: ${strategy}${timeInfo}</div>`;
            }
            
            messageDiv.innerHTML = `
                <div class="message-avatar">${avatar}</div>
                <div class="message-content">
                    ${content}
                    ${metaInfo}
                </div>
            `;
            
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function updateStats(data) {
            document.getElementById('current-strategy').textContent = data.strategy_used || 'Adaptativa';
            document.getElementById('tools-count').textContent = data.tools_available || 0;
            document.getElementById('response-time').textContent = data.response_time ? 
                `${(data.response_time * 1000).toFixed(0)}ms` : '0ms';
        }
        
        function showTyping() {
            typingIndicator.style.display = 'block';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
        
        function hideTyping() {
            typingIndicator.style.display = 'none';
        }
        
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
            
            // Limpiar UI
            messagesContainer.innerHTML = `
                <div class="message assistant">
                    <div class="message-avatar">C</div>
                    <div class="message-content">
                        ¡Hola! Soy Eva, tu asistente virtual híbrido 🌟<br><br>
                        ¿En qué puedo ayudarte hoy?
                        <div class="message-meta">
                            Nueva conversación iniciada <span class="strategy-badge">hybrid</span>
                        </div>
                    </div>
                </div>
            `;
            
            sessionId = null;
            updateStats({ strategy_used: 'Adaptativa', tools_available: 0, response_time: 0 });
        }
        
        function showFeedback() {
            document.getElementById('feedback-modal').style.display = 'flex';
        }
        
        function closeFeedback() {
            document.getElementById('feedback-modal').style.display = 'none';
            selectedRating = 0;
            updateStars();
            document.getElementById('feedback-comment').value = '';
        }
        
        async function submitFeedback() {
            if (selectedRating === 0) {
                alert('Por favor selecciona una calificación');
                return;
            }
            
            try {
                await fetch('/api/feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        session_id: sessionId,
                        rating: selectedRating,
                        comment: document.getElementById('feedback-comment').value
                    })
                });
                
                closeFeedback();
                addMessage('¡Gracias por tu feedback! Nos ayuda a mejorar 😊', 'assistant', 'feedback');
                
            } catch (error) {
                console.error('Error submitting feedback:', error);
                alert('Error al enviar feedback');
            }
        }
        
        async function showStats() {
            try {
                const response = await fetch('/api/stats');
                const data = await response.json();
                
                const statsMessage = `
📊 **Estadísticas del Sistema:**
• Conversaciones activas: ${data.active_sessions}
• Total de mensajes: ${data.global_stats.total_messages}
• Tiempo promedio de respuesta: ${(data.global_stats.avg_response_time * 1000).toFixed(0)}ms
• Satisfacción promedio: ${data.avg_satisfaction.toFixed(1)}/5
• Sistema: ${data.system_type}
                `;
                
                addMessage(statsMessage, 'assistant', 'stats');
                
            } catch (error) {
                console.error('Error fetching stats:', error);
                addMessage('Error al obtener estadísticas', 'assistant', 'error');
            }
        }
        
        // Inicializar
        messageInput.focus();
    </script>
</body>
</html>"""
    
    # Guardar template
    with open("templates/hybrid_chat.html", "w", encoding="utf-8") as f:
        f.write(template_html)
    
    print("✅ Template híbrido creado exitosamente")

if __name__ == "__main__":
    uvicorn.run(
        "src.web.enhanced_interface:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    ) 