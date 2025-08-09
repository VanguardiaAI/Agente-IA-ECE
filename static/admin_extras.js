// Funciones adicionales para el panel de administración

// Toggle password visibility
function togglePasswordVisibility(inputId) {
    const input = document.getElementById(inputId);
    const toggle = document.getElementById(inputId + 'Toggle');
    
    if (input.type === 'password') {
        input.type = 'text';
        toggle.classList.remove('bi-eye');
        toggle.classList.add('bi-eye-slash');
    } else {
        input.type = 'password';
        toggle.classList.remove('bi-eye-slash');
        toggle.classList.add('bi-eye');
    }
}

// Check password strength
function checkPasswordStrength() {
    const password = document.getElementById('newPassword').value;
    const strengthBar = document.getElementById('passwordStrengthBar');
    const progressBar = strengthBar?.querySelector('.progress-bar');
    
    if (!progressBar) return;
    
    let strength = 0;
    let color = 'bg-danger';
    
    // Length check
    if (password.length >= 8) strength += 25;
    if (password.length >= 12) strength += 10;
    
    // Contains lowercase
    if (/[a-z]/.test(password)) strength += 20;
    
    // Contains uppercase
    if (/[A-Z]/.test(password)) strength += 20;
    
    // Contains numbers
    if (/[0-9]/.test(password)) strength += 20;
    
    // Contains special characters
    if (/[^A-Za-z0-9]/.test(password)) strength += 15;
    
    // Set color based on strength
    if (strength < 40) {
        color = 'bg-danger';
    } else if (strength < 70) {
        color = 'bg-warning';
    } else {
        color = 'bg-success';
    }
    
    // Update progress bar
    progressBar.className = 'progress-bar ' + color;
    progressBar.style.width = strength + '%';
    
    if (password.length > 0) {
        strengthBar.style.display = 'block';
    } else {
        strengthBar.style.display = 'none';
    }
}

// Check if passwords match
function checkPasswordMatch() {
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const feedback = document.getElementById('confirmPasswordFeedback');
    
    if (confirmPassword.length === 0) {
        feedback.textContent = 'Repite la nueva contraseña';
        feedback.className = 'text-muted';
    } else if (newPassword === confirmPassword) {
        feedback.textContent = '✅ Las contraseñas coinciden';
        feedback.className = 'text-success';
    } else {
        feedback.textContent = '❌ Las contraseñas no coinciden';
        feedback.className = 'text-danger';
    }
}

// Variables globales para conversaciones
let currentConversationPage = 1;
let conversationsPerPage = 20;
let totalConversations = 0;
let currentConversationId = null;

// Función para cargar conversaciones
async function loadConversations(page = 1) {
    try {
        const offset = (page - 1) * conversationsPerPage;
        const response = await fetch(`/api/admin/conversations?limit=${conversationsPerPage}&offset=${offset}`);
        const data = await response.json();
        
        displayConversations(data.conversations);
        totalConversations = data.total;
        updateConversationsPagination(page);
        
    } catch (error) {
        console.error('Error cargando conversaciones:', error);
        showAlert('Error al cargar conversaciones', 'danger');
    }
}

// Función para mostrar conversaciones en la tabla
function displayConversations(conversations) {
    const tbody = document.getElementById('conversationsList');
    
    if (!conversations || conversations.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center text-muted">
                    No se encontraron conversaciones
                </td>
            </tr>
        `;
        return;
    }
    
    tbody.innerHTML = conversations.map(conv => `
        <tr>
            <td>${new Date(conv.started_at).toLocaleString('es-ES')}</td>
            <td>${conv.user_id}</td>
            <td>
                <span class="badge bg-${conv.platform === 'whatsapp' ? 'success' : 'primary'}">
                    ${conv.platform.toUpperCase()}
                </span>
            </td>
            <td>${conv.messages_count}</td>
            <td>${conv.duration_minutes ? `${conv.duration_minutes.toFixed(1)} min` : '-'}</td>
            <td>
                <span class="badge bg-${conv.status === 'completed' ? 'success' : 'warning'}">
                    ${conv.status}
                </span>
            </td>
            <td>
                <button class="btn btn-sm btn-outline-primary" onclick="viewConversation('${conv.conversation_id}')">
                    <i class="bi bi-eye"></i> Ver
                </button>
            </td>
        </tr>
    `).join('');
}

// Función para buscar conversaciones
async function searchConversations() {
    try {
        const query = document.getElementById('searchQuery').value;
        const platform = document.getElementById('filterPlatform').value;
        const userId = document.getElementById('filterUserId').value;
        const dateFrom = document.getElementById('filterDateFrom').value;
        const dateTo = document.getElementById('filterDateTo').value;
        
        let url = '/api/admin/conversations/search?';
        const params = new URLSearchParams();
        
        if (query) params.append('query', query);
        if (platform) params.append('platform', platform);
        if (userId) params.append('user_id', userId);
        if (dateFrom) params.append('date_from', dateFrom);
        if (dateTo) params.append('date_to', dateTo);
        params.append('limit', conversationsPerPage);
        params.append('offset', 0);
        
        const response = await fetch(url + params.toString());
        const data = await response.json();
        
        displayConversations(data.conversations);
        totalConversations = data.total;
        updateConversationsPagination(1);
        
    } catch (error) {
        console.error('Error buscando conversaciones:', error);
        showAlert('Error al buscar conversaciones', 'danger');
    }
}

// Función para limpiar filtros
function clearConversationFilters() {
    document.getElementById('searchQuery').value = '';
    document.getElementById('filterPlatform').value = '';
    document.getElementById('filterUserId').value = '';
    document.getElementById('filterDateFrom').value = '';
    document.getElementById('filterDateTo').value = '';
    loadConversations(1);
}

// Función para ver detalle de conversación
async function viewConversation(conversationId) {
    try {
        currentConversationId = conversationId;
        const modal = new bootstrap.Modal(document.getElementById('conversationModal'));
        modal.show();
        
        // Mostrar loading
        document.getElementById('conversationMessages').innerHTML = `
            <div class="text-center">
                <div class="spinner-border"></div>
                <p class="mt-2">Cargando mensajes...</p>
            </div>
        `;
        
        // Cargar datos de la conversación
        const response = await fetch(`/api/admin/conversations/${conversationId}/messages`);
        const data = await response.json();
        
        // Mostrar información de la conversación
        document.getElementById('convDetailId').textContent = conversationId;
        document.getElementById('convDetailUser').textContent = data.conversation.user_id;
        document.getElementById('convDetailPlatform').textContent = data.conversation.platform.toUpperCase();
        document.getElementById('convDetailDuration').textContent = 
            data.conversation.duration_minutes ? `${data.conversation.duration_minutes.toFixed(1)} minutos` : 'En curso';
        
        // Mostrar mensajes
        displayConversationMessages(data.messages);
        
    } catch (error) {
        console.error('Error cargando conversación:', error);
        showAlert('Error al cargar detalles de la conversación', 'danger');
    }
}

// Función para mostrar mensajes de conversación
function displayConversationMessages(messages) {
    const container = document.getElementById('conversationMessages');
    
    if (!messages || messages.length === 0) {
        container.innerHTML = '<p class="text-center text-muted">No hay mensajes en esta conversación</p>';
        return;
    }
    
    container.innerHTML = messages.map(msg => `
        <div class="d-flex ${msg.sender_type === 'user' ? 'justify-content-end' : 'justify-content-start'} mb-3">
            <div class="message-bubble ${msg.sender_type === 'user' ? 'message-user' : 'message-bot'}">
                <div>${msg.content}</div>
                <div class="message-time">
                    ${new Date(msg.timestamp).toLocaleTimeString('es-ES')}
                </div>
                ${msg.intent ? `
                    <div class="message-metadata">
                        <span class="message-intent">${msg.intent}</span>
                        ${msg.confidence ? `<small>Confianza: ${(msg.confidence * 100).toFixed(0)}%</small>` : ''}
                    </div>
                ` : ''}
            </div>
        </div>
    `).join('');
    
    // Scroll al final
    container.scrollTop = container.scrollHeight;
}

// Función para exportar conversaciones
async function exportConversations() {
    try {
        const format = confirm('¿Exportar en formato CSV? (Cancelar para JSON)') ? 'csv' : 'json';
        const includeMessages = confirm('¿Incluir mensajes en la exportación?');
        
        const response = await fetch('/api/admin/conversations/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format,
                include_messages: includeMessages
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `conversaciones_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            throw new Error('Error en la exportación');
        }
        
    } catch (error) {
        console.error('Error exportando conversaciones:', error);
        showAlert('Error al exportar conversaciones', 'danger');
    }
}

// Función para exportar una conversación individual
async function exportConversation() {
    if (!currentConversationId) return;
    
    try {
        const format = confirm('¿Exportar en formato CSV? (Cancelar para JSON)') ? 'csv' : 'json';
        
        const response = await fetch('/api/admin/conversations/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                format: format,
                include_messages: true,
                conversation_ids: [currentConversationId]
            })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `conversacion_${currentConversationId}_${new Date().toISOString().split('T')[0]}.${format}`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            throw new Error('Error en la exportación');
        }
        
    } catch (error) {
        console.error('Error exportando conversación:', error);
        showAlert('Error al exportar conversación', 'danger');
    }
}

// Funciones de paginación
function updateConversationsPagination(page) {
    currentConversationPage = page;
    const pagination = document.getElementById('conversationsPagination');
    
    if (totalConversations <= conversationsPerPage) {
        pagination.style.display = 'none';
        return;
    }
    
    pagination.style.display = 'block';
    document.getElementById('currentPage').textContent = page;
}

function previousConversationsPage() {
    if (currentConversationPage > 1) {
        loadConversations(currentConversationPage - 1);
    }
}

function nextConversationsPage() {
    const totalPages = Math.ceil(totalConversations / conversationsPerPage);
    if (currentConversationPage < totalPages) {
        loadConversations(currentConversationPage + 1);
    }
}

// Función auxiliar para mostrar alertas
function showAlert(message, type = 'info') {
    const alertContainer = document.querySelector('.content-wrapper');
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    alertContainer.insertBefore(alert, alertContainer.firstChild);
    
    // Auto-cerrar después de 5 segundos
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

// Hacer las funciones disponibles globalmente
window.togglePasswordVisibility = togglePasswordVisibility;
window.checkPasswordStrength = checkPasswordStrength;
window.checkPasswordMatch = checkPasswordMatch;
window.loadConversations = loadConversations;
window.searchConversations = searchConversations;
window.clearConversationFilters = clearConversationFilters;
window.viewConversation = viewConversation;
window.exportConversations = exportConversations;
window.exportConversation = exportConversation;
window.previousConversationsPage = previousConversationsPage;
window.nextConversationsPage = nextConversationsPage;