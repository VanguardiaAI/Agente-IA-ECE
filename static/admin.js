// Admin Panel JavaScript
const API_BASE = window.location.origin;
let currentSection = 'dashboard';
let currentDocument = null;
let settings = {};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    checkAuth();
    loadUserInfo();
    loadDashboard();
    initializeEventListeners();
    loadSettings();
    checkSystemStatus(); // Verificar estado del sistema
    // Verificar estado cada 30 segundos
    setInterval(checkSystemStatus, 30000);
});

// Check authentication
function checkAuth() {
    const token = localStorage.getItem('admin_token');
    if (!token) {
        window.location.href = '/admin/login';
        return;
    }
    
    // Set default authorization header
    setAuthHeader();
}

// Set authorization header for all requests
function setAuthHeader() {
    const token = localStorage.getItem('admin_token');
    window.authHeader = {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
    };
}

// Load user info
function loadUserInfo() {
    // Ya no mostramos el nombre de usuario en la barra superior
    const user = JSON.parse(localStorage.getItem('admin_user') || '{}');
    console.log('Usuario conectado:', user.username || 'Admin');
}

// Initialize event listeners
function initializeEventListeners() {
    // Menu navigation
    document.querySelectorAll('.menu-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            const section = item.dataset.section;
            showSection(section);
            
            // Update active menu
            document.querySelectorAll('.menu-item').forEach(m => m.classList.remove('active'));
            item.classList.add('active');
        });
    });
    
    // Forms
    document.getElementById('identityForm')?.addEventListener('submit', saveIdentitySettings);
    document.getElementById('passwordForm')?.addEventListener('submit', changePassword);
}

// Show section
function showSection(section) {
    // Hide all sections
    document.querySelectorAll('.content-section').forEach(s => {
        s.style.display = 'none';
    });
    
    // Show selected section
    const sectionElement = document.getElementById(`${section}-section`);
    if (sectionElement) {
        sectionElement.style.display = 'block';
        currentSection = section;
        
        // Load section-specific data
        switch(section) {
            case 'dashboard':
                loadDashboard();
                break;
            case 'knowledge':
                loadKnowledgeDocuments();
                break;
        }
    }
}

// Load dashboard
async function loadDashboard() {
    try {
        // Load general stats
        const stats = await fetchAPI('/api/stats');
        
        // Load metrics summary
        const metricsResponse = await fetchAPI('/api/admin/metrics/summary');
        const metrics = metricsResponse?.metrics || {};
        
        // Update dashboard stats with real metrics
        if (metrics.today) {
            document.getElementById('statConversations').textContent = metrics.today.conversations || 0;
            document.getElementById('statUsers').textContent = metrics.today.unique_users || 0;
        }
        
        // Si no hay conversaciones hoy pero hay totales, usar esos
        if (metrics.total && metrics.total.conversations > 0 && (!metrics.today || metrics.today.conversations === 0)) {
            document.getElementById('statConversations').textContent = metrics.total.conversations || 0;
            document.getElementById('statUsers').textContent = metrics.total.users || 0;
        }
        
        // Mostrar total de conversaciones de los últimos 30 días
        if (metrics.total) {
            document.getElementById('statTotalConversations').textContent = metrics.total.conversations || 0;
        }
        
        // Update platform stats (usar platforms_all si platforms está vacío)
        const platformData = (metrics.platforms && Object.keys(metrics.platforms).length > 0) 
            ? metrics.platforms 
            : metrics.platforms_all || {};
            
        document.getElementById('wordpressConversations').textContent = platformData.wordpress || 0;
        document.getElementById('whatsappConversations').textContent = platformData.whatsapp || 0;
        
        // Si hay datos totales, mostrarlos también
        if (metrics.total) {
            console.log('Total de conversaciones (histórico):', metrics.total.conversations);
            console.log('Total de usuarios únicos:', metrics.total.users);
        }
        
        // Documents count from database stats - usar active_entries o total_entries
        if (stats?.database) {
            // Usar active_entries (documentos activos) o total_entries (todos)
            const totalDocs = stats.database.active_entries || stats.database.total_entries || 0;
            document.getElementById('statDocuments').textContent = totalDocs;
            
            // Mostrar detalles en consola para debugging
            console.log('Estadísticas de documentos:', {
                total: stats.database.total_entries,
                activos: stats.database.active_entries,
                productos: stats.database.products,
                categorías: stats.database.categories,
                faqs: stats.database.faqs
            });
        }
        
        // Load activity logs
        const logs = await fetchAPI('/api/admin/activity-logs?limit=10');
        displayActivityLogs(logs);
        
        // Load recent conversations
        const conversations = await fetchAPI('/api/admin/conversations?limit=10');
        displayRecentConversations(conversations?.conversations || []);
        
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

// Display activity logs
function displayActivityLogs(logs) {
    const tbody = document.getElementById('activityLog');
    if (!logs || logs.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="text-center text-muted">No hay actividad reciente</td></tr>';
        return;
    }
    
    tbody.innerHTML = logs.map(log => `
        <tr>
            <td>${new Date(log.created_at).toLocaleString('es-ES')}</td>
            <td>${log.action}</td>
            <td>${log.username}</td>
            <td>${log.entity_type || '-'} ${log.entity_id || ''}</td>
        </tr>
    `).join('');
}

// Display recent conversations
function displayRecentConversations(conversations) {
    // Por ahora, podemos agregar esto a la actividad o crear una nueva sección
    const tbody = document.getElementById('activityLog');
    
    if (conversations && conversations.length > 0) {
        const conversationRows = conversations.slice(0, 5).map(conv => {
            const platform = conv.platform || 'unknown';
            const platformIcon = platform === 'whatsapp' ? '📱' : platform === 'wordpress' ? '🌐' : '💬';
            const duration = conv.duration_minutes ? `${conv.duration_minutes.toFixed(1)} min` : 'En curso';
            
            return `
                <tr>
                    <td>${new Date(conv.started_at).toLocaleString('es-ES')}</td>
                    <td>${platformIcon} Conversación ${platform}</td>
                    <td>${conv.user_id.substring(0, 15)}...</td>
                    <td>${conv.messages_count} mensajes (${duration})</td>
                </tr>
            `;
        }).join('');
        
        // Si hay conversaciones, las agregamos al principio de la tabla
        if (tbody && conversationRows) {
            const currentContent = tbody.innerHTML;
            if (!currentContent.includes('No hay actividad reciente')) {
                tbody.innerHTML = conversationRows + currentContent;
            } else {
                tbody.innerHTML = conversationRows;
            }
        }
    }
}

// Load settings
async function loadSettings() {
    try {
        settings = await fetchAPI('/api/admin/settings/');
        
        // Populate forms with current settings
        populateSettingsForms();
        
    } catch (error) {
        console.error('Error loading settings:', error);
    }
}

// Populate settings forms
function populateSettingsForms() {
    // Identity settings
    setValue('botName', getSettingValue('bot_name'));
    setValue('companyName', getSettingValue('company_name'));
    setValue('welcomeMessage', getSettingValue('welcome_message'));
}

// Helper functions for settings
function getSettingValue(key) {
    for (const category in settings) {
        if (settings[category][key]) {
            return settings[category][key].value;
        }
    }
    return '';
}

function setValue(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.value = value || '';
    }
}

function setChecked(id, value) {
    const element = document.getElementById(id);
    if (element) {
        element.checked = value === true || value === 'true';
    }
}

// Save settings functions
async function saveIdentitySettings(e) {
    e.preventDefault();
    showLoading();
    
    try {
        const updates = [
            { key: 'bot_name', value: document.getElementById('botName').value, category: 'identity' },
            { key: 'company_name', value: document.getElementById('companyName').value, category: 'identity' },
            { key: 'welcome_message', value: document.getElementById('welcomeMessage').value, category: 'identity' }
        ];
        
        const result = await fetchAPI('/api/admin/settings/bulk', {
            method: 'PUT',
            body: JSON.stringify({ settings: updates })
        });
        
        showAlert('success', '✅ Configuración guardada exitosamente');
        await loadSettings();
        
    } catch (error) {
        showAlert('danger', 'Error al guardar configuración');
    } finally {
        hideLoading();
    }
}

// Knowledge Base functions
async function loadKnowledgeDocuments() {
    try {
        const documents = await fetchAPI('/api/admin/knowledge/documents');
        displayKnowledgeDocuments(documents);
        
    } catch (error) {
        console.error('Error loading documents:', error);
    }
}

function displayKnowledgeDocuments(documents) {
    const tbody = document.getElementById('knowledgeList');
    if (!documents || documents.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" class="text-center text-muted">No hay documentos</td></tr>';
        return;
    }
    
    tbody.innerHTML = documents.map(doc => `
        <tr>
            <td>${doc.filename}</td>
            <td>${doc.title}</td>
            <td><span class="badge bg-secondary">${doc.category}</span></td>
            <td>${formatBytes(doc.size)}</td>
            <td>
                <button class="btn btn-sm btn-primary" onclick="editDocument('${doc.filename}')">
                    <i class="bi bi-pencil"></i>
                </button>
                <button class="btn btn-sm btn-danger" onclick="deleteDocument('${doc.filename}')">
                    <i class="bi bi-trash"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

async function editDocument(filename) {
    try {
        const doc = await fetchAPI(`/api/admin/knowledge/document/${filename}`);
        currentDocument = filename;
        
        document.getElementById('docTitle').value = doc.title;
        document.getElementById('docContent').value = doc.content;
        document.getElementById('documentModalTitle').textContent = 'Editar Documento';
        
        new bootstrap.Modal(document.getElementById('documentModal')).show();
        
    } catch (error) {
        showAlert('danger', 'Error al cargar documento');
    }
}

async function createNewDocument() {
    currentDocument = null;
    document.getElementById('docTitle').value = '';
    document.getElementById('docContent').value = '';
    document.getElementById('documentModalTitle').textContent = 'Nuevo Documento';
    
    new bootstrap.Modal(document.getElementById('documentModal')).show();
}

async function saveDocument() {
    showLoading();
    
    try {
        const title = document.getElementById('docTitle').value;
        const content = document.getElementById('docContent').value;
        
        if (currentDocument) {
            // Update existing
            await fetchAPI(`/api/admin/knowledge/document/${currentDocument}`, {
                method: 'PUT',
                body: JSON.stringify({ content, title })
            });
            showAlert('success', 'Documento actualizado');
        } else {
            // Create new
            const filename = prompt('Nombre del archivo (sin extensión):');
            if (!filename) return;
            
            const category = prompt('Categoría (general/policies/faqs):') || 'general';
            
            await fetchAPI('/api/admin/knowledge/document', {
                method: 'POST',
                body: JSON.stringify({
                    filename: `${filename}.md`,
                    content,
                    category,
                    title
                })
            });
            showAlert('success', 'Documento creado');
        }
        
        bootstrap.Modal.getInstance(document.getElementById('documentModal')).hide();
        await loadKnowledgeDocuments();
        
    } catch (error) {
        showAlert('danger', 'Error al guardar documento');
    } finally {
        hideLoading();
    }
}

async function deleteDocument(filename) {
    if (!confirm(`¿Estás seguro de eliminar ${filename}?`)) return;
    
    showLoading();
    
    try {
        await fetchAPI(`/api/admin/knowledge/document/${filename}`, {
            method: 'DELETE'
        });
        
        showAlert('success', 'Documento eliminado');
        await loadKnowledgeDocuments();
        
    } catch (error) {
        showAlert('danger', 'Error al eliminar documento');
    } finally {
        hideLoading();
    }
}

async function reloadKnowledge() {
    if (!confirm('¿Recargar toda la base de conocimiento? Esto puede tomar unos minutos.')) return;
    
    showLoading();
    
    try {
        const result = await fetchAPI('/api/admin/knowledge/reload', {
            method: 'POST'
        });
        
        showAlert('success', `Base de conocimiento recargada: ${result.results.success} exitosos`);
        
    } catch (error) {
        showAlert('danger', 'Error al recargar base de conocimiento');
    } finally {
        hideLoading();
    }
}


// Utility functions
async function fetchAPI(endpoint, options = {}) {
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers: {
            ...window.authHeader,
            ...options.headers
        }
    });
    
    if (!response.ok) {
        if (response.status === 401) {
            // Unauthorized, redirect to login
            localStorage.removeItem('admin_token');
            window.location.href = '/admin/login';
            return;
        }
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

function showLoading() {
    document.getElementById('loadingOverlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('active');
}

function showAlert(type, message) {
    // Create alert element
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show position-fixed top-0 end-0 m-3`;
    alert.style.zIndex = '9999';
    alert.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alert);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        alert.remove();
    }, 5000);
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
}

function toggleSidebar() {
    document.getElementById('sidebar').classList.toggle('active');
}

async function logout() {
    if (!confirm('¿Cerrar sesión?')) return;
    
    try {
        await fetchAPI('/api/admin/logout', { method: 'POST' });
    } catch (error) {
        console.error('Error during logout:', error);
    }
    
    localStorage.removeItem('admin_token');
    localStorage.removeItem('admin_user');
    window.location.href = '/admin/login';
}

// Change password function
async function changePassword(e) {
    e.preventDefault();
    
    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    
    // Validaciones
    if (newPassword.length < 8) {
        showAlert('warning', 'La nueva contraseña debe tener al menos 8 caracteres');
        return;
    }
    
    if (newPassword !== confirmPassword) {
        showAlert('danger', 'Las contraseñas no coinciden');
        return;
    }
    
    if (currentPassword === newPassword) {
        showAlert('warning', 'La nueva contraseña debe ser diferente a la actual');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetchAPI('/api/admin/change-password', {
            method: 'POST',
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });
        
        showAlert('success', '✅ Contraseña actualizada exitosamente');
        
        // Limpiar formulario
        document.getElementById('passwordForm').reset();
        
        // Opcional: Redirigir al login después de cambiar contraseña
        setTimeout(() => {
            showAlert('info', 'Por seguridad, vuelve a iniciar sesión con tu nueva contraseña');
            setTimeout(() => {
                logout();
            }, 2000);
        }, 1500);
        
    } catch (error) {
        console.error('Error cambiando contraseña:', error);
        
        // Manejar errores específicos
        if (error.message && error.message.includes('401')) {
            showAlert('danger', 'Contraseña actual incorrecta');
        } else {
            showAlert('danger', 'Error al cambiar la contraseña. Por favor, intenta de nuevo.');
        }
    } finally {
        hideLoading();
    }
}

// Check system status
async function checkSystemStatus() {
    const statusLed = document.getElementById('statusLed');
    const statusText = document.getElementById('statusText');
    
    if (!statusLed || !statusText) return;
    
    // Mostrar estado verificando
    statusLed.className = 'status-led checking';
    statusText.textContent = 'Verificando...';
    
    try {
        // Verificar el endpoint de salud
        const response = await fetch('/health', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            
            // Verificar el estado de los servicios
            const dbOk = data.services?.database === 'ok';
            const embeddingsOk = data.services?.embeddings === 'ok';
            
            if (data.status === 'healthy' && dbOk && embeddingsOk) {
                // Sistema completamente operativo
                statusLed.className = 'status-led active';
                statusText.textContent = 'Sistema Activo';
            } else if (data.status === 'degraded') {
                // Sistema parcialmente operativo
                statusLed.className = 'status-led checking';
                statusText.textContent = 'Sistema Degradado';
            } else {
                // Sistema con problemas
                statusLed.className = 'status-led inactive';
                statusText.textContent = 'Sistema con Errores';
            }
            
            // Log para debugging
            console.log('Estado del sistema:', data);
            
        } else {
            // Error en la respuesta
            statusLed.className = 'status-led inactive';
            statusText.textContent = 'Sin Conexión';
        }
        
    } catch (error) {
        // Error de red o servidor caído
        console.error('Error verificando estado del sistema:', error);
        statusLed.className = 'status-led inactive';
        statusText.textContent = 'Sin Conexión';
    }
}