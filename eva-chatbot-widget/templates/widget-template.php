<?php
/**
 * Widget Template
 * 
 * @package Eva_Chatbot_Widget
 */

if (!defined('ABSPATH')) {
    exit;
}

$position = get_option('eva_chatbot_position', 'bottom-right');
$button_size = get_option('eva_chatbot_button_size', 'medium');
?>

<div id="eva-chatbot-widget" class="eva-chatbot-widget eva-position-<?php echo esc_attr($position); ?>" data-widget-loaded="false">
    <!-- Chat Button -->
    <button id="eva-chat-button" class="eva-chat-button eva-size-<?php echo esc_attr($button_size); ?>" aria-label="<?php esc_attr_e('Abrir chat', 'eva-chatbot'); ?>">
        <svg class="eva-chat-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 2C6.48 2 2 6.48 2 12C2 13.19 2.23 14.33 2.64 15.37L2 22L8.63 21.36C9.67 21.77 10.81 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM17 17H7C6.45 17 6 16.55 6 16V14C6 13.45 6.45 13 7 13H17C17.55 13 18 13.45 18 14V16C18 16.55 17.55 17 17 17ZM17 11H7C6.45 11 6 10.55 6 10V8C6 7.45 6.45 7 7 7H17C17.55 7 18 7.45 18 8V10C18 10.55 17.55 11 17 11Z" fill="currentColor"/>
        </svg>
        <span class="eva-unread-indicator" style="display: none;">
            <span class="eva-unread-count">0</span>
        </span>
    </button>
    
    <!-- Chat Window -->
    <div id="eva-chat-window" class="eva-chat-window" style="display: none;">
        <!-- Header -->
        <div class="eva-chat-header">
            <div class="eva-header-info">
                <div class="eva-avatar">
                    <?php 
                    $avatar_id = get_option('eva_chatbot_avatar_id');
                    if ($avatar_id) :
                        $avatar_url = wp_get_attachment_image_url($avatar_id, 'thumbnail');
                        if ($avatar_url) : ?>
                            <img src="<?php echo esc_url($avatar_url); ?>" alt="<?php echo esc_attr(get_option('eva_chatbot_name', 'Eva')); ?>" />
                        <?php else : ?>
                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.1"/>
                                <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 4C13.66 4 15 5.34 15 7C15 8.66 13.66 10 12 10C10.34 10 9 8.66 9 7C9 5.34 10.34 4 12 4ZM12 20C9.33 20 6.99 18.78 5.49 16.82C5.52 14.41 9.58 13.1 12 13.1C14.41 13.1 18.48 14.41 18.51 16.82C17.01 18.78 14.67 20 12 20Z" fill="currentColor"/>
                            </svg>
                        <?php endif;
                    else : ?>
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.1"/>
                            <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 4C13.66 4 15 5.34 15 7C15 8.66 13.66 10 12 10C10.34 10 9 8.66 9 7C9 5.34 10.34 4 12 4ZM12 20C9.33 20 6.99 18.78 5.49 16.82C5.52 14.41 9.58 13.1 12 13.1C14.41 13.1 18.48 14.41 18.51 16.82C17.01 18.78 14.67 20 12 20Z" fill="currentColor"/>
                        </svg>
                    <?php endif; ?>
                </div>
                <div class="eva-header-text">
                    <h3 class="eva-chat-title"><?php echo esc_html(get_option('eva_chatbot_name', 'Eva')); ?> - <?php esc_html_e('Asistente de IA', 'eva-chatbot'); ?></h3>
                    <span class="eva-status">
                        <span class="eva-status-dot"></span>
                        <span class="eva-status-text"><?php esc_html_e('En línea', 'eva-chatbot'); ?></span>
                    </span>
                </div>
            </div>
            <div class="eva-header-actions">
                <button class="eva-minimize-btn" aria-label="<?php esc_attr_e('Minimizar chat', 'eva-chatbot'); ?>">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M5 7.5L10 12.5L15 7.5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
                <button class="eva-close-btn" aria-label="<?php esc_attr_e('Cerrar chat', 'eva-chatbot'); ?>">
                    <svg width="20" height="20" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
                    </svg>
                </button>
            </div>
        </div>
        
        <!-- Messages Container -->
        <div class="eva-messages-container" id="eva-messages">
            <div class="eva-welcome-message">
                <div class="eva-message eva-bot-message">
                    <div class="eva-message-content">
                        <?php echo esc_html(get_option('eva_chatbot_welcome_message')); ?>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Connection Status -->
        <div class="eva-connection-status" id="eva-connection-status" style="display: none;">
            <span class="eva-connection-icon">⚠️</span>
            <span class="eva-connection-text"><?php esc_html_e('Reconectando...', 'eva-chatbot'); ?></span>
        </div>
        
        <!-- Quick Replies -->
        <div class="eva-quick-replies" id="eva-quick-replies" style="display: none;">
            <!-- Quick reply buttons will be inserted here by JavaScript -->
        </div>
        
        <!-- Input Area -->
        <div class="eva-input-area">
            <form id="eva-chat-form" class="eva-chat-form">
                <div class="eva-input-wrapper">
                    <textarea 
                        id="eva-message-input" 
                        class="eva-message-input" 
                        placeholder="<?php esc_attr_e('Escribe tu mensaje...', 'eva-chatbot'); ?>"
                        rows="1"
                        maxlength="1000"
                    ></textarea>
                    <button type="submit" class="eva-send-btn" aria-label="<?php esc_attr_e('Enviar mensaje', 'eva-chatbot'); ?>">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <path d="M2 21L23 12L2 3V10L17 12L2 14V21Z" fill="currentColor"/>
                        </svg>
                    </button>
                </div>
            </form>
            
            <!-- Typing Indicator -->
            <div class="eva-typing-indicator" id="eva-typing-indicator" style="display: none;">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    </div>
</div>