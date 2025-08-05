<?php
/**
 * Eva API Integration Class
 * 
 * @package Eva_Chatbot_Widget
 */

if (!defined('ABSPATH')) {
    exit;
}

class Eva_API {
    
    /**
     * Server URL
     */
    private $server_url;
    
    /**
     * Constructor
     */
    public function __construct() {
        $this->server_url = get_option('eva_chatbot_server_url', 'http://localhost:8080');
    }
    
    /**
     * Send message to chat API
     */
    public function send_message($message, $user_id) {
        $endpoint = $this->server_url . '/api/chat';
        
        $response = wp_remote_post($endpoint, array(
            'timeout' => 30,
            'headers' => array(
                'Content-Type' => 'application/json'
            ),
            'body' => json_encode(array(
                'message' => $message,
                'user_id' => $user_id
            ))
        ));
        
        if (is_wp_error($response)) {
            return array(
                'error' => true,
                'message' => $response->get_error_message()
            );
        }
        
        $body = wp_remote_retrieve_body($response);
        $data = json_decode($body, true);
        
        if (json_last_error() !== JSON_ERROR_NONE) {
            return array(
                'error' => true,
                'message' => 'Invalid response from server'
            );
        }
        
        return $data;
    }
    
    /**
     * Check server health
     */
    public function check_health() {
        $endpoint = $this->server_url . '/health';
        
        $response = wp_remote_get($endpoint, array(
            'timeout' => 5
        ));
        
        if (is_wp_error($response)) {
            return false;
        }
        
        $code = wp_remote_retrieve_response_code($response);
        return $code === 200;
    }
    
    /**
     * Get chat statistics
     */
    public function get_stats() {
        $endpoint = $this->server_url . '/api/chat/stats';
        
        $response = wp_remote_get($endpoint, array(
            'timeout' => 10
        ));
        
        if (is_wp_error($response)) {
            return null;
        }
        
        $body = wp_remote_retrieve_body($response);
        return json_decode($body, true);
    }
    
    /**
     * Reset user conversation
     */
    public function reset_conversation($user_id) {
        $endpoint = $this->server_url . '/api/chat/reset/' . $user_id;
        
        $response = wp_remote_post($endpoint, array(
            'timeout' => 5
        ));
        
        if (is_wp_error($response)) {
            return false;
        }
        
        $code = wp_remote_retrieve_response_code($response);
        return $code === 200;
    }
    
    /**
     * Search products
     */
    public function search_products($query, $limit = 10) {
        $endpoint = $this->server_url . '/api/search';
        
        $response = wp_remote_post($endpoint, array(
            'timeout' => 15,
            'headers' => array(
                'Content-Type' => 'application/json'
            ),
            'body' => json_encode(array(
                'query' => $query,
                'search_type' => 'hybrid',
                'limit' => $limit,
                'content_types' => array('product')
            ))
        ));
        
        if (is_wp_error($response)) {
            return null;
        }
        
        $body = wp_remote_retrieve_body($response);
        return json_decode($body, true);
    }
    
    /**
     * Get WebSocket URL
     */
    public function get_websocket_url($client_id) {
        $ws_url = str_replace(array('http://', 'https://'), array('ws://', 'wss://'), $this->server_url);
        return $ws_url . '/ws/chat/' . $client_id;
    }
    
    /**
     * Validate webhook signature (if implemented)
     */
    public function validate_webhook($payload, $signature) {
        // Implement webhook validation if needed
        $secret = get_option('eva_chatbot_webhook_secret', '');
        
        if (empty($secret)) {
            return true; // No secret configured
        }
        
        $calculated_signature = hash_hmac('sha256', $payload, $secret);
        return hash_equals($calculated_signature, $signature);
    }
}