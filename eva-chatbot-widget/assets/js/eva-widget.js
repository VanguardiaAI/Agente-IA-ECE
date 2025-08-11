/**
 * Eva Chatbot Widget JavaScript
 * Version: 1.0.0
 */

(function($) {
    'use strict';

    class EvaChatbotWidget {
        constructor() {
            this.config = window.evaChat || {};
            this.websocket = null;
            this.clientId = this.getOrCreateClientId();
            this.isOpen = false;
            this.reconnectAttempts = 0;
            this.maxReconnectAttempts = 5;
            this.reconnectDelay = 1000;
            this.messageQueue = [];
            this.isConnected = false;
            
            this.init();
        }

        init() {
            this.bindEvents();
            this.applyCustomStyles();
            this.restoreState();
            
            // Widget always starts closed
            localStorage.setItem('eva_chat_seen', 'true');
        }

        bindEvents() {
            // Chat button click
            $('#eva-chat-button').on('click', () => this.toggleChat());
            
            // Close button
            $('.eva-close-btn').on('click', () => this.closeChat());
            
            // Minimize button
            $('.eva-minimize-btn').on('click', () => this.closeChat());
            
            // Form submission
            $('#eva-chat-form').on('submit', (e) => {
                e.preventDefault();
                this.sendMessage();
            });
            
            // Textarea auto-resize
            $('#eva-message-input').on('input', function() {
                this.style.height = 'auto';
                this.style.height = (this.scrollHeight) + 'px';
            });
            
            // Enter key handling
            $('#eva-message-input').on('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
            
            // Close chat when clicking product links
            $(document).on('click', '.eva-product-link', () => {
                setTimeout(() => {
                    this.closeChat();
                }, 100);
            });
        }

        applyCustomStyles() {
            const root = document.documentElement;
            root.style.setProperty('--eva-primary-color', this.config.primaryColor || '#007cba');
            root.style.setProperty('--eva-text-color', this.config.textColor || '#ffffff');
        }

        getOrCreateClientId() {
            let clientId = localStorage.getItem('eva_client_id');
            if (!clientId) {
                clientId = 'client_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
                localStorage.setItem('eva_client_id', clientId);
            }
            return clientId;
        }

        toggleChat() {
            if (this.isOpen) {
                this.closeChat();
            } else {
                this.openChat();
            }
        }

        openChat() {
            $('#eva-chat-window').fadeIn(300);
            $('#eva-chat-button').hide();
            this.isOpen = true;
            
            // Focus on input and scroll to bottom
            setTimeout(() => {
                $('#eva-message-input').focus();
                // Scroll to the latest message
                const messagesContainer = $('#eva-messages');
                messagesContainer.scrollTop(messagesContainer[0].scrollHeight);
            }, 300);
            
            // Connect WebSocket if not connected
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.connectWebSocket();
            }
            
            // Clear unread indicator
            $('.eva-unread-indicator').hide();
            
            // Show quick replies
            this.showQuickReplies();
        }

        closeChat() {
            $('#eva-chat-window').fadeOut(300);
            $('#eva-chat-button').fadeIn(300);
            this.isOpen = false;
            
            // Don't save closed state - it's the default
        }

        restoreState() {
            // Restore chat history
            const history = this.getChatHistory();
            history.forEach(msg => {
                this.displayMessage(msg.content, msg.isUser, false);
            });
            
            // Scroll to bottom after loading all messages
            setTimeout(() => {
                const messagesContainer = $('#eva-messages');
                messagesContainer.scrollTop(messagesContainer[0].scrollHeight);
            }, 100);
        }

        connectWebSocket() {
            if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                return;
            }

            const wsUrl = this.config.serverUrl.replace(/^http/, 'ws') + 
                         this.config.wsEndpoint + this.clientId;

            try {
                this.websocket = new WebSocket(wsUrl);
                
                this.websocket.onopen = () => {
                    console.log('WebSocket connected');
                    this.isConnected = true;
                    this.reconnectAttempts = 0;
                    this.hideConnectionStatus();
                    
                    // Send queued messages
                    this.processMessageQueue();
                };

                this.websocket.onmessage = (event) => {
                    try {
                        const data = JSON.parse(event.data);
                        this.handleWebSocketMessage(data);
                    } catch (error) {
                        console.error('Error parsing WebSocket message:', error);
                    }
                };

                this.websocket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                    this.handleConnectionError();
                };

                this.websocket.onclose = () => {
                    console.log('WebSocket disconnected');
                    this.isConnected = false;
                    this.handleConnectionError();
                };

            } catch (error) {
                console.error('Error creating WebSocket:', error);
                this.handleConnectionError();
            }
        }

        handleWebSocketMessage(data) {
            if (data.type === 'agent_response') {
                this.displayMessage(data.message, false);
                this.hideTypingIndicator();
                
                // Show notification if chat is closed
                if (!this.isOpen) {
                    this.showNotification();
                }
            } else if (data.type === 'error') {
                this.displayMessage(data.message, false);
                this.hideTypingIndicator();
            }
        }

        handleConnectionError() {
            this.showConnectionStatus();
            
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                this.reconnectAttempts++;
                setTimeout(() => {
                    this.connectWebSocket();
                }, this.reconnectDelay * this.reconnectAttempts);
            }
        }

        showConnectionStatus() {
            $('#eva-connection-status').show();
        }

        hideConnectionStatus() {
            $('#eva-connection-status').hide();
        }

        processMessageQueue() {
            while (this.messageQueue.length > 0) {
                const message = this.messageQueue.shift();
                this.sendViaWebSocket(message);
            }
        }

        sendMessage() {
            const input = $('#eva-message-input');
            const message = input.val().trim();
            
            if (!message) return;
            
            // Display user message
            this.displayMessage(message, true);
            
            // Clear input
            input.val('').css('height', 'auto');
            
            // Show typing indicator
            this.showTypingIndicator();
            
            // Send message
            if (this.isConnected) {
                this.sendViaWebSocket(message);
            } else {
                this.sendViaAPI(message);
            }
        }

        sendViaWebSocket(message) {
            try {
                this.websocket.send(JSON.stringify({
                    message: message,
                    clientId: this.clientId,
                    platform: 'wordpress',
                    timestamp: new Date().toISOString()
                }));
            } catch (error) {
                console.error('Error sending via WebSocket:', error);
                this.messageQueue.push(message);
                this.sendViaAPI(message);
            }
        }

        sendViaAPI(message) {
            $.ajax({
                url: this.config.serverUrl + this.config.apiEndpoint,
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-Platform': 'wordpress'
                },
                data: JSON.stringify({
                    message: message,
                    user_id: this.clientId,
                    platform: 'wordpress'
                }),
                success: (response) => {
                    console.log('Response from server:', response);
                    console.log('Platform:', response.platform);
                    console.log('Response content:', response.response);
                    this.displayMessage(response.response, false);
                    this.hideTypingIndicator();
                },
                error: (xhr, status, error) => {
                    console.error('API Error:', error);
                    this.displayMessage(
                        this.config.errorMessage || 
                        this.config.translations.connectionError || 
                        'Error de conexión. Por favor, intenta de nuevo.',
                        false
                    );
                    this.hideTypingIndicator();
                }
            });
        }

        displayMessage(content, isUser, saveToHistory = true) {
            const messagesContainer = $('#eva-messages');
            const messageClass = isUser ? 'eva-user-message' : 'eva-bot-message';
            
            let messageContent;
            
            if (isUser) {
                // For user messages, always escape HTML
                messageContent = this.escapeHtml(content);
            } else {
                // For bot messages, process formatting
                messageContent = this.formatBotMessage(content);
            }
            
            const messageHtml = `
                <div class="eva-message ${messageClass}">
                    <div class="eva-message-content">${messageContent}</div>
                </div>
            `;
            
            messagesContainer.append(messageHtml);
            
            // Scroll to bottom
            messagesContainer.scrollTop(messagesContainer[0].scrollHeight);
            
            // Save to history
            if (saveToHistory) {
                this.saveToChatHistory(content, isUser);
            }
        }

        showTypingIndicator() {
            const typingHtml = `<span class="eva-typing-message">${this.config.chatbotName} ${this.config.typingMessage}</span>`;
            $('#eva-typing-indicator').html(typingHtml).show();
            const messagesContainer = $('#eva-messages');
            messagesContainer.scrollTop(messagesContainer[0].scrollHeight);
        }

        hideTypingIndicator() {
            $('#eva-typing-indicator').hide();
        }

        showNotification() {
            const indicator = $('.eva-unread-indicator');
            const count = parseInt(indicator.find('.eva-unread-count').text()) || 0;
            indicator.find('.eva-unread-count').text(count + 1);
            indicator.show();
            
            // Play notification sound if enabled
            if (this.config.enableSound) {
                this.playNotificationSound();
            }
        }

        playNotificationSound() {
            const audio = new Audio('data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp66hVFApGn+DyvmwhBSuBzvLZiTYIHGa48OScTgwOUang4LeAHAU0gM3w2IwzCB1kuu7tn1wQDk6k4e3CgB8GN2LGz+TajDQIHla0693BoFEMDUqv49a+hCEGMpHU8eCWOwgZaL3u7alQDg1Kov/144AcBDJ3xtfvkEcJFl+45/GqVQ0MSqzj2sKGIAU1hsHs5Y46CRpgu+3xplANCVGq39jAhB4GLH3L7OGNOwgdX7rn9KdWDAlJo+DyvmwhBSp1yujjizYIG2W86+2jUgwLTqvh26GFIwUvgM7x2oo3CB1kvu3+sVgNDEScz9Lf0tkbBTN+zOziizoJG2K97OugUAwMTKrh1sKGHwUzgM3r4ow6CRphu+3wpVIMCU2rz9LdxdcVBjKBzvLZijYIHWS68OWfUg0NTqPexp6DHQUvgMzx2Ys4CB1mvOzto1ELDUWX2+LftokVCyuAz+/ZjzwLF1+y58WlWgwOSqfj1r6EIAUzgs3v4Ys7Chlkve3nplINClCs3+PZ');
            audio.volume = 0.3;
            audio.play().catch(e => console.log('Could not play notification sound'));
        }

        escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return text.replace(/[&<>"']/g, m => map[m]);
        }

        formatBotMessage(content) {
            // First, check if content already has HTML tags (from WordPress formatting)
            const hasHtmlTags = /<[a-zA-Z][\s\S]*>/i.test(content);
            
            if (hasHtmlTags) {
                // If it has HTML tags, clean them and convert to simple format
                // Remove all HTML tags
                content = content.replace(/<[^>]+>/g, '');
                
                // Convert HTML entities
                content = content.replace(/&nbsp;/g, ' ');
                content = content.replace(/&quot;/g, '"');
                content = content.replace(/&apos;/g, "'");
                content = content.replace(/&lt;/g, '<');
                content = content.replace(/&gt;/g, '>');
                content = content.replace(/&amp;/g, '&');
            }
            
            // Clean up asterisks used for bold in WhatsApp
            content = content.replace(/\*([^*]+)\*/g, '<strong>$1</strong>');
            
            // Clean up underscores used for italic
            content = content.replace(/_([^_]+)_/g, '<em>$1</em>');
            
            // Convert WhatsApp links to clickable links
            content = content.replace(
                /(https?:\/\/wa\.me\/[^\s]+)/g,
                '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #25D366; text-decoration: underline;">💬 Contactar por WhatsApp</a>'
            );
            
            // Convert other URLs to clickable links
            content = content.replace(
                /(https?:\/\/(?!wa\.me)[^\s]+)/g,
                '<a href="$1" target="_blank" rel="noopener noreferrer" style="color: #007cba; text-decoration: underline;">$1</a>'
            );
            
            // Convert line breaks to <br> tags
            content = content.replace(/\n/g, '<br>');
            
            // Handle lists
            const lines = content.split('<br>');
            let inList = false;
            let formattedLines = [];
            
            for (let line of lines) {
                line = line.trim();
                
                // Check if this line is a list item
                if (line.match(/^[•\-\*]\s/)) {
                    if (!inList) {
                        formattedLines.push('<ul style="margin: 10px 0; padding-left: 20px;">');
                        inList = true;
                    }
                    formattedLines.push('<li>' + line.substring(2) + '</li>');
                } else if (line.match(/^\d+\.\s/)) {
                    if (!inList) {
                        formattedLines.push('<ol style="margin: 10px 0; padding-left: 20px;">');
                        inList = true;
                    }
                    formattedLines.push('<li>' + line.replace(/^\d+\.\s/, '') + '</li>');
                } else {
                    if (inList) {
                        formattedLines.push(inList === true ? '</ul>' : '</ol>');
                        inList = false;
                    }
                    if (line) {
                        formattedLines.push(line);
                    }
                }
            }
            
            // Close any open list
            if (inList) {
                formattedLines.push(inList === true ? '</ul>' : '</ol>');
            }
            
            return formattedLines.join('<br>');
        }

        saveToChatHistory(content, isUser) {
            const history = this.getChatHistory();
            history.push({
                content: content,
                isUser: isUser,
                timestamp: new Date().toISOString()
            });
            
            // Keep only last 50 messages
            if (history.length > 50) {
                history.splice(0, history.length - 50);
            }
            
            localStorage.setItem('eva_chat_history', JSON.stringify(history));
        }

        getChatHistory() {
            try {
                return JSON.parse(localStorage.getItem('eva_chat_history') || '[]');
            } catch (e) {
                return [];
            }
        }

        showQuickReplies() {
            const quickReplies = this.config.quickReplies;
            if (!quickReplies || quickReplies.length === 0) {
                $('#eva-quick-replies').hide();
                return;
            }

            let buttonsHtml = '';
            quickReplies.forEach((reply, index) => {
                buttonsHtml += `
                    <button class="eva-quick-reply-btn" data-message="${this.escapeHtml(reply.message)}">
                        ${this.escapeHtml(reply.text)}
                    </button>
                `;
            });

            $('#eva-quick-replies').html(buttonsHtml).show();
            
            // Bind click events
            $('.eva-quick-reply-btn').off('click').on('click', (e) => {
                const message = $(e.target).data('message');
                $('#eva-message-input').val(message);
                this.sendMessage();
                $('#eva-quick-replies').hide();
            });
        }

        hideQuickReplies() {
            $('#eva-quick-replies').hide();
        }
    }

    // Initialize when DOM is ready
    $(document).ready(function() {
        // Wait for widget to be loaded
        const checkWidget = setInterval(() => {
            if ($('#eva-chatbot-widget').length && $('#eva-chatbot-widget').attr('data-widget-loaded') !== 'true') {
                clearInterval(checkWidget);
                $('#eva-chatbot-widget').attr('data-widget-loaded', 'true');
                window.evaChatbotWidget = new EvaChatbotWidget();
            }
        }, 100);
    });

})(jQuery);