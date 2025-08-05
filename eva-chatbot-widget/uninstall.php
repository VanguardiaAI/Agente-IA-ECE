<?php
/**
 * Uninstall Eva Chatbot Widget
 * 
 * @package Eva_Chatbot_Widget
 */

// If uninstall not called from WordPress, then exit
if (!defined('WP_UNINSTALL_PLUGIN')) {
    exit;
}

// Delete all plugin options
$options_to_delete = array(
    'eva_chatbot_enabled',
    'eva_chatbot_server_url',
    'eva_chatbot_name',
    'eva_chatbot_avatar_id',
    'eva_chatbot_welcome_message',
    'eva_chatbot_typing_message',
    'eva_chatbot_error_message',
    'eva_chatbot_auto_open_delay',
    'eva_chatbot_quick_replies',
    'eva_chatbot_position',
    'eva_chatbot_display_rules',
    'eva_chatbot_allowed_pages',
    'eva_chatbot_primary_color',
    'eva_chatbot_text_color',
    'eva_chatbot_button_size'
);

foreach ($options_to_delete as $option) {
    delete_option($option);
}