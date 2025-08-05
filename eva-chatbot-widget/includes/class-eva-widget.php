<?php
/**
 * Eva Widget Core Class
 * 
 * @package Eva_Chatbot_Widget
 */

if (!defined('ABSPATH')) {
    exit;
}

class Eva_Widget {
    
    /**
     * Instance
     */
    private static $instance = null;
    
    /**
     * Get instance
     */
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    /**
     * Constructor
     */
    private function __construct() {
        // Widget initialization handled by main plugin class
    }
    
    /**
     * Check if widget should be displayed on current page
     */
    public function should_display() {
        // Check if enabled
        if (get_option('eva_chatbot_enabled', '1') !== '1') {
            return false;
        }
        
        // Check display rules
        $display_rules = get_option('eva_chatbot_display_rules', 'all');
        
        switch ($display_rules) {
            case 'all':
                return true;
                
            case 'woocommerce':
                return $this->is_woocommerce_page();
                
            case 'specific_pages':
                return $this->is_allowed_page();
                
            default:
                return true;
        }
    }
    
    /**
     * Check if current page is a WooCommerce page
     */
    private function is_woocommerce_page() {
        if (!class_exists('WooCommerce')) {
            return false;
        }
        
        return is_woocommerce() || is_cart() || is_checkout() || is_account_page();
    }
    
    /**
     * Check if current page is in allowed pages list
     */
    private function is_allowed_page() {
        $allowed_pages = get_option('eva_chatbot_allowed_pages', array());
        
        if (empty($allowed_pages)) {
            return false;
        }
        
        $current_page_id = get_the_ID();
        
        return in_array($current_page_id, $allowed_pages);
    }
    
    /**
     * Get widget configuration
     */
    public function get_config() {
        return array(
            'enabled' => get_option('eva_chatbot_enabled', '1'),
            'server_url' => get_option('eva_chatbot_server_url', 'http://localhost:8080'),
            'welcome_message' => get_option('eva_chatbot_welcome_message', '¡Hola! Soy Eva, tu asistente virtual. ¿En qué puedo ayudarte hoy?'),
            'position' => get_option('eva_chatbot_position', 'bottom-right'),
            'primary_color' => get_option('eva_chatbot_primary_color', '#007cba'),
            'text_color' => get_option('eva_chatbot_text_color', '#ffffff'),
            'button_size' => get_option('eva_chatbot_button_size', 'medium')
        );
    }
    
    /**
     * Validate server URL
     */
    public function validate_server_url($url) {
        // Remove trailing slash
        $url = rtrim($url, '/');
        
        // Check if valid URL
        if (!filter_var($url, FILTER_VALIDATE_URL)) {
            return false;
        }
        
        // Check if starts with http or https
        if (!preg_match('/^https?:\/\//', $url)) {
            return false;
        }
        
        return $url;
    }
    
    /**
     * Get client ID for current user
     */
    public function get_client_id() {
        if (is_user_logged_in()) {
            $user = wp_get_current_user();
            return 'wp_user_' . $user->ID;
        }
        
        // For guests, use session or cookie
        if (!session_id()) {
            session_start();
        }
        
        if (!isset($_SESSION['eva_client_id'])) {
            $_SESSION['eva_client_id'] = 'guest_' . uniqid();
        }
        
        return $_SESSION['eva_client_id'];
    }
    
    /**
     * Log chat interaction
     */
    public function log_interaction($client_id, $message, $response) {
        // Optional: Log interactions to database for analytics
        do_action('eva_chatbot_log_interaction', array(
            'client_id' => $client_id,
            'message' => $message,
            'response' => $response,
            'timestamp' => current_time('mysql')
        ));
    }
}