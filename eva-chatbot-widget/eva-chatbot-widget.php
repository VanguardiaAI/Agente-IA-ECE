<?php
/**
 * Plugin Name: Eva Chatbot Widget
 * Plugin URI: https://vanguardia.dev/eva-chatbot
 * Description: Widget de chat inteligente para atención al cliente en tiendas WooCommerce
 * Version: 2.2.3
 * Author: Vanguardia.dev
 * Author URI: https://vanguardia.dev
 * License: GPL v2 or later
 * Text Domain: eva-chatbot
 * Domain Path: /languages
 * Requires at least: 5.0
 * Requires PHP: 7.2
 * WC requires at least: 3.0
 * WC tested up to: 8.5
 */

if (!defined('ABSPATH')) {
    exit;
}

define('EVA_CHATBOT_VERSION', '2.2.3');
define('EVA_CHATBOT_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('EVA_CHATBOT_PLUGIN_URL', plugin_dir_url(__FILE__));
define('EVA_CHATBOT_PLUGIN_BASENAME', plugin_basename(__FILE__));

class EvaChatbotWidget {
    
    private static $instance = null;
    
    public static function get_instance() {
        if (null === self::$instance) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        $this->init_hooks();
    }
    
    private function init_hooks() {
        add_action('plugins_loaded', array($this, 'load_plugin'));
        add_action('wp_enqueue_scripts', array($this, 'enqueue_scripts'));
        add_action('wp_footer', array($this, 'render_widget'));
        add_action('admin_menu', array($this, 'add_admin_menu'));
        add_action('admin_init', array($this, 'register_settings'));
        add_action('admin_enqueue_scripts', array($this, 'enqueue_admin_scripts'));
        
        // AJAX actions
        add_action('wp_ajax_eva_get_config', array($this, 'ajax_get_config'));
        add_action('wp_ajax_nopriv_eva_get_config', array($this, 'ajax_get_config'));
        
        // Activation/Deactivation hooks
        register_activation_hook(__FILE__, array($this, 'activate'));
        register_deactivation_hook(__FILE__, array($this, 'deactivate'));
    }
    
    public function load_plugin() {
        // Load text domain
        load_plugin_textdomain('eva-chatbot', false, dirname(EVA_CHATBOT_PLUGIN_BASENAME) . '/languages');
        
        // Include required files
        require_once EVA_CHATBOT_PLUGIN_DIR . 'includes/class-eva-widget.php';
        require_once EVA_CHATBOT_PLUGIN_DIR . 'includes/class-eva-admin.php';
        require_once EVA_CHATBOT_PLUGIN_DIR . 'includes/class-eva-api.php';
    }
    
    public function enqueue_admin_scripts($hook) {
        // Solo cargar en nuestra página de admin
        if ($hook !== 'toplevel_page_eva-chatbot') {
            return;
        }
        
        // Enqueue media scripts
        wp_enqueue_media();
    }
    
    public function enqueue_scripts() {
        if (!$this->should_display_widget()) {
            return;
        }
        
        // CSS
        wp_enqueue_style(
            'eva-chatbot-widget',
            EVA_CHATBOT_PLUGIN_URL . 'assets/css/eva-widget.css',
            array(),
            EVA_CHATBOT_VERSION . '.' . time()
        );
        
        // JavaScript
        wp_enqueue_script(
            'eva-chatbot-widget',
            EVA_CHATBOT_PLUGIN_URL . 'assets/js/eva-widget.js',
            array('jquery'),
            EVA_CHATBOT_VERSION . '.' . time(),
            true
        );
        
        // Get avatar URL if set
        $avatar_id = get_option('eva_chatbot_avatar_id');
        $avatar_url = '';
        if ($avatar_id) {
            $avatar_url = wp_get_attachment_image_url($avatar_id, 'thumbnail');
        }
        
        // Localize script with necessary data
        wp_localize_script('eva-chatbot-widget', 'evaChat', array(
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('eva-chatbot-nonce'),
            'serverUrl' => get_option('eva_chatbot_server_url', 'http://localhost:8080'),
            'wsEndpoint' => '/ws/chat/',
            'apiEndpoint' => '/api/chat',
            'chatbotName' => get_option('eva_chatbot_name', 'Eva'),
            'avatarUrl' => $avatar_url,
            'welcomeMessage' => get_option('eva_chatbot_welcome_message', '¡Hola! Soy Eva, tu asistente virtual. ¿En qué puedo ayudarte hoy?'),
            'typingMessage' => get_option('eva_chatbot_typing_message', 'está escribiendo...'),
            'errorMessage' => get_option('eva_chatbot_error_message', 'Error de conexión. Por favor, intenta de nuevo.'),
            'autoOpenDelay' => '0', // Disabled - widget always starts closed
            'quickReplies' => json_decode(get_option('eva_chatbot_quick_replies', '[]'), true),
            'position' => get_option('eva_chatbot_position', 'bottom-right'),
            'primaryColor' => get_option('eva_chatbot_primary_color', '#54841e'),
            'textColor' => get_option('eva_chatbot_text_color', '#ffffff'),
            'translations' => array(
                'typePlaceholder' => __('Escribe tu mensaje...', 'eva-chatbot'),
                'sendButton' => __('Enviar', 'eva-chatbot'),
                'connectionError' => get_option('eva_chatbot_error_message', __('Error de conexión. Por favor, intenta de nuevo.', 'eva-chatbot')),
                'minimizeChat' => __('Minimizar chat', 'eva-chatbot'),
                'closeChat' => __('Cerrar chat', 'eva-chatbot')
            )
        ));
    }
    
    public function render_widget() {
        if (!$this->should_display_widget()) {
            return;
        }
        
        include EVA_CHATBOT_PLUGIN_DIR . 'templates/widget-template.php';
    }
    
    private function should_display_widget() {
        $enabled = get_option('eva_chatbot_enabled', '1');
        
        if ($enabled !== '1') {
            return false;
        }
        
        // Check display rules
        $display_rules = get_option('eva_chatbot_display_rules', 'all');
        
        if ($display_rules === 'woocommerce' && !class_exists('WooCommerce')) {
            return false;
        }
        
        if ($display_rules === 'specific_pages') {
            $allowed_pages = get_option('eva_chatbot_allowed_pages', array());
            if (!is_array($allowed_pages) || empty($allowed_pages)) {
                return false;
            }
            
            $current_page_id = get_the_ID();
            if (!in_array($current_page_id, $allowed_pages)) {
                return false;
            }
        }
        
        return true;
    }
    
    public function add_admin_menu() {
        add_menu_page(
            __('Eva Chatbot', 'eva-chatbot'),
            __('Eva Chatbot', 'eva-chatbot'),
            'manage_options',
            'eva-chatbot',
            array($this, 'admin_page'),
            'dashicons-format-chat',
            30
        );
    }
    
    public function admin_page() {
        $admin = new Eva_Chatbot_Admin();
        $admin->render();
    }
    
    public function register_settings() {
        // General settings
        register_setting('eva_chatbot_settings', 'eva_chatbot_enabled');
        register_setting('eva_chatbot_settings', 'eva_chatbot_server_url');
        register_setting('eva_chatbot_settings', 'eva_chatbot_name');
        register_setting('eva_chatbot_settings', 'eva_chatbot_avatar_id');
        register_setting('eva_chatbot_settings', 'eva_chatbot_welcome_message');
        register_setting('eva_chatbot_settings', 'eva_chatbot_typing_message');
        register_setting('eva_chatbot_settings', 'eva_chatbot_error_message');
        register_setting('eva_chatbot_settings', 'eva_chatbot_auto_open_delay');
        register_setting('eva_chatbot_settings', 'eva_chatbot_quick_replies');
        
        // Display settings
        register_setting('eva_chatbot_settings', 'eva_chatbot_position');
        register_setting('eva_chatbot_settings', 'eva_chatbot_display_rules');
        register_setting('eva_chatbot_settings', 'eva_chatbot_allowed_pages');
        
        // Style settings
        register_setting('eva_chatbot_settings', 'eva_chatbot_primary_color');
        register_setting('eva_chatbot_settings', 'eva_chatbot_text_color');
        register_setting('eva_chatbot_settings', 'eva_chatbot_button_size');
    }
    
    public function ajax_get_config() {
        check_ajax_referer('eva-chatbot-nonce', 'nonce');
        
        $config = array(
            'serverUrl' => get_option('eva_chatbot_server_url', 'http://localhost:8080'),
            'welcomeMessage' => get_option('eva_chatbot_welcome_message'),
            'position' => get_option('eva_chatbot_position', 'bottom-right'),
            'primaryColor' => get_option('eva_chatbot_primary_color', '#007cba'),
            'textColor' => get_option('eva_chatbot_text_color', '#ffffff')
        );
        
        wp_send_json_success($config);
    }
    
    public function activate() {
        // Set default options
        add_option('eva_chatbot_enabled', '1');
        add_option('eva_chatbot_server_url', 'http://localhost:8080');
        add_option('eva_chatbot_name', 'Eva');
        add_option('eva_chatbot_welcome_message', '¡Hola! Soy Eva, tu asistente virtual. ¿En qué puedo ayudarte hoy?');
        add_option('eva_chatbot_typing_message', 'está escribiendo...');
        add_option('eva_chatbot_error_message', 'Error de conexión. Por favor, intenta de nuevo.');
        add_option('eva_chatbot_auto_open_delay', '0'); // Never auto-open by default
        add_option('eva_chatbot_quick_replies', json_encode(array()));
        add_option('eva_chatbot_position', 'bottom-right');
        add_option('eva_chatbot_display_rules', 'all');
        add_option('eva_chatbot_primary_color', '#54841e');
        add_option('eva_chatbot_text_color', '#ffffff');
        add_option('eva_chatbot_button_size', 'medium');
        
        // Flush rewrite rules
        flush_rewrite_rules();
    }
    
    public function deactivate() {
        // Clean up if needed
        flush_rewrite_rules();
    }
}

// Initialize the plugin
EvaChatbotWidget::get_instance();