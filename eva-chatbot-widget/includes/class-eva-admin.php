<?php
/**
 * Eva Chatbot Admin Class
 * 
 * @package Eva_Chatbot_Widget
 */

if (!defined('ABSPATH')) {
    exit;
}

class Eva_Chatbot_Admin {
    
    public function render() {
        // Save settings if form submitted
        if (isset($_POST['eva_chatbot_save_settings']) && check_admin_referer('eva_chatbot_settings_nonce')) {
            $this->save_settings();
            echo '<div class="notice notice-success is-dismissible"><p>' . 
                 esc_html__('Configuración guardada correctamente.', 'eva-chatbot') . 
                 '</p></div>';
        }
        
        // Get current settings
        $enabled = get_option('eva_chatbot_enabled', '1');
        $server_url = get_option('eva_chatbot_server_url', 'http://localhost:8080');
        $chatbot_name = get_option('eva_chatbot_name', 'Eva');
        $avatar_id = get_option('eva_chatbot_avatar_id', '');
        $welcome_message = get_option('eva_chatbot_welcome_message', '¡Hola! Soy Eva, tu asistente virtual. ¿En qué puedo ayudarte hoy?');
        $typing_message = get_option('eva_chatbot_typing_message', 'está escribiendo...');
        $error_message = get_option('eva_chatbot_error_message', 'Error de conexión. Por favor, intenta de nuevo.');
        $auto_open_delay = get_option('eva_chatbot_auto_open_delay', '3');
        $quick_replies = json_decode(get_option('eva_chatbot_quick_replies', '[]'), true);
        $position = get_option('eva_chatbot_position', 'bottom-right');
        $display_rules = get_option('eva_chatbot_display_rules', 'all');
        $allowed_pages = get_option('eva_chatbot_allowed_pages', array());
        $primary_color = get_option('eva_chatbot_primary_color', '#54841e');
        $text_color = get_option('eva_chatbot_text_color', '#ffffff');
        $button_size = get_option('eva_chatbot_button_size', 'medium');
        
        ?>
        <div class="wrap">
            <h1><?php echo esc_html(get_admin_page_title()); ?></h1>
            
            <form method="post" action="">
                <?php wp_nonce_field('eva_chatbot_settings_nonce'); ?>
                
                <div class="eva-admin-container">
                    <!-- General Settings -->
                    <div class="eva-settings-section">
                        <h2><?php esc_html_e('Configuración General', 'eva-chatbot'); ?></h2>
                        
                        <table class="form-table">
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_enabled">
                                        <?php esc_html_e('Activar Widget', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="checkbox" 
                                           id="eva_chatbot_enabled" 
                                           name="eva_chatbot_enabled" 
                                           value="1" 
                                           <?php checked($enabled, '1'); ?> />
                                    <label for="eva_chatbot_enabled">
                                        <?php esc_html_e('Mostrar el widget de chat en el sitio', 'eva-chatbot'); ?>
                                    </label>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_server_url">
                                        <?php esc_html_e('URL del Servidor', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="url" 
                                           id="eva_chatbot_server_url" 
                                           name="eva_chatbot_server_url" 
                                           value="<?php echo esc_url($server_url); ?>" 
                                           class="regular-text" 
                                           required />
                                    <p class="description">
                                        <?php esc_html_e('URL del servidor donde está alojado el chatbot Eva (ej: http://localhost:8080)', 'eva-chatbot'); ?>
                                    </p>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_name">
                                        <?php esc_html_e('Nombre del Chatbot', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="text" 
                                           id="eva_chatbot_name" 
                                           name="eva_chatbot_name" 
                                           value="<?php echo esc_attr($chatbot_name); ?>" 
                                           class="regular-text" 
                                           required />
                                    <p class="description">
                                        <?php esc_html_e('Nombre que aparecerá en el chat (ej: Eva, Asistente, Sofia)', 'eva-chatbot'); ?>
                                    </p>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_avatar">
                                        <?php esc_html_e('Avatar del Chatbot', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <div class="eva-avatar-field">
                                        <input type="hidden" 
                                               id="eva_chatbot_avatar_id" 
                                               name="eva_chatbot_avatar_id" 
                                               value="<?php echo esc_attr($avatar_id); ?>" />
                                        
                                        <div id="eva-avatar-preview" class="eva-avatar-preview">
                                            <?php if ($avatar_id) : 
                                                $avatar_url = wp_get_attachment_image_url($avatar_id, 'thumbnail');
                                                if ($avatar_url) : ?>
                                                    <img src="<?php echo esc_url($avatar_url); ?>" alt="Avatar" />
                                                <?php endif;
                                            else : ?>
                                                <div class="eva-default-avatar">
                                                    <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                                        <circle cx="12" cy="12" r="10" fill="#54841e" opacity="0.1"/>
                                                        <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 4C13.66 4 15 5.34 15 7C15 8.66 13.66 10 12 10C10.34 10 9 8.66 9 7C9 5.34 10.34 4 12 4ZM12 20C9.33 20 6.99 18.78 5.49 16.82C5.52 14.41 9.58 13.1 12 13.1C14.41 13.1 18.48 14.41 18.51 16.82C17.01 18.78 14.67 20 12 20Z" fill="#54841e"/>
                                                    </svg>
                                                </div>
                                            <?php endif; ?>
                                        </div>
                                        
                                        <div class="eva-avatar-buttons">
                                            <button type="button" 
                                                    id="eva-select-avatar" 
                                                    class="button button-secondary">
                                                <?php esc_html_e('Seleccionar Avatar', 'eva-chatbot'); ?>
                                            </button>
                                            <button type="button" 
                                                    id="eva-remove-avatar" 
                                                    class="button button-link-delete"
                                                    <?php echo $avatar_id ? '' : 'style="display:none;"'; ?>>
                                                <?php esc_html_e('Eliminar', 'eva-chatbot'); ?>
                                            </button>
                                        </div>
                                        
                                        <p class="description">
                                            <?php esc_html_e('Tamaño recomendado: 100x100px. Formatos: JPG, PNG, GIF, WebP', 'eva-chatbot'); ?>
                                        </p>
                                    </div>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_welcome_message">
                                        <?php esc_html_e('Mensaje de Bienvenida', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <textarea id="eva_chatbot_welcome_message" 
                                              name="eva_chatbot_welcome_message" 
                                              rows="3" 
                                              class="large-text"><?php echo esc_textarea($welcome_message); ?></textarea>
                                    <p class="description">
                                        <?php esc_html_e('Mensaje que se muestra cuando se abre el chat', 'eva-chatbot'); ?>
                                    </p>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_typing_message">
                                        <?php esc_html_e('Mensaje "Escribiendo"', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="text" 
                                           id="eva_chatbot_typing_message" 
                                           name="eva_chatbot_typing_message" 
                                           value="<?php echo esc_attr($typing_message); ?>" 
                                           class="regular-text" />
                                    <p class="description">
                                        <?php esc_html_e('Texto que aparece cuando el bot está escribiendo', 'eva-chatbot'); ?>
                                    </p>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_error_message">
                                        <?php esc_html_e('Mensaje de Error', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="text" 
                                           id="eva_chatbot_error_message" 
                                           name="eva_chatbot_error_message" 
                                           value="<?php echo esc_attr($error_message); ?>" 
                                           class="regular-text" />
                                    <p class="description">
                                        <?php esc_html_e('Mensaje cuando hay error de conexión', 'eva-chatbot'); ?>
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Behavior Settings -->
                    <div class="eva-settings-section">
                        <h2><?php esc_html_e('Comportamiento', 'eva-chatbot'); ?></h2>
                        
                        <table class="form-table">
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_auto_open_delay">
                                        <?php esc_html_e('Auto-apertura', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <select id="eva_chatbot_auto_open_delay" name="eva_chatbot_auto_open_delay">
                                        <option value="0" <?php selected($auto_open_delay, '0'); ?>>
                                            <?php esc_html_e('Nunca', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="3" <?php selected($auto_open_delay, '3'); ?>>
                                            <?php esc_html_e('3 segundos', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="5" <?php selected($auto_open_delay, '5'); ?>>
                                            <?php esc_html_e('5 segundos', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="10" <?php selected($auto_open_delay, '10'); ?>>
                                            <?php esc_html_e('10 segundos', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="30" <?php selected($auto_open_delay, '30'); ?>>
                                            <?php esc_html_e('30 segundos', 'eva-chatbot'); ?>
                                        </option>
                                    </select>
                                    <p class="description">
                                        <?php esc_html_e('Tiempo para abrir automáticamente el chat en la primera visita', 'eva-chatbot'); ?>
                                    </p>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Quick Replies Settings -->
                    <div class="eva-settings-section">
                        <h2><?php esc_html_e('Respuestas Rápidas', 'eva-chatbot'); ?></h2>
                        
                        <p class="description">
                            <?php esc_html_e('Configura botones de respuesta rápida que aparecerán cuando se abra el chat.', 'eva-chatbot'); ?>
                        </p>
                        
                        <div id="eva-quick-replies-container">
                            <?php
                            if (!empty($quick_replies)) {
                                foreach ($quick_replies as $index => $reply) {
                                    ?>
                                    <div class="eva-quick-reply-item" data-index="<?php echo $index; ?>">
                                        <input type="text" 
                                               name="eva_quick_replies[<?php echo $index; ?>][text]" 
                                               value="<?php echo esc_attr($reply['text']); ?>" 
                                               placeholder="<?php esc_attr_e('Texto del botón', 'eva-chatbot'); ?>"
                                               class="regular-text" />
                                        <input type="text" 
                                               name="eva_quick_replies[<?php echo $index; ?>][message]" 
                                               value="<?php echo esc_attr($reply['message']); ?>" 
                                               placeholder="<?php esc_attr_e('Mensaje a enviar', 'eva-chatbot'); ?>"
                                               class="regular-text" />
                                        <button type="button" class="button eva-remove-reply">
                                            <?php esc_html_e('Eliminar', 'eva-chatbot'); ?>
                                        </button>
                                    </div>
                                    <?php
                                }
                            }
                            ?>
                        </div>
                        
                        <p>
                            <button type="button" id="eva-add-reply" class="button button-secondary">
                                <?php esc_html_e('Añadir Respuesta Rápida', 'eva-chatbot'); ?>
                            </button>
                        </p>
                    </div>
                    
                    <!-- Display Settings -->
                    <div class="eva-settings-section">
                        <h2><?php esc_html_e('Configuración de Visualización', 'eva-chatbot'); ?></h2>
                        
                        <table class="form-table">
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_position">
                                        <?php esc_html_e('Posición del Widget', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <select id="eva_chatbot_position" name="eva_chatbot_position">
                                        <option value="bottom-right" <?php selected($position, 'bottom-right'); ?>>
                                            <?php esc_html_e('Esquina inferior derecha', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="bottom-left" <?php selected($position, 'bottom-left'); ?>>
                                            <?php esc_html_e('Esquina inferior izquierda', 'eva-chatbot'); ?>
                                        </option>
                                    </select>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_display_rules">
                                        <?php esc_html_e('Mostrar en', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <select id="eva_chatbot_display_rules" name="eva_chatbot_display_rules">
                                        <option value="all" <?php selected($display_rules, 'all'); ?>>
                                            <?php esc_html_e('Todas las páginas', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="woocommerce" <?php selected($display_rules, 'woocommerce'); ?>>
                                            <?php esc_html_e('Solo páginas de WooCommerce', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="specific_pages" <?php selected($display_rules, 'specific_pages'); ?>>
                                            <?php esc_html_e('Páginas específicas', 'eva-chatbot'); ?>
                                        </option>
                                    </select>
                                </td>
                            </tr>
                            
                            <tr id="eva_specific_pages_row" style="<?php echo $display_rules === 'specific_pages' ? '' : 'display:none;'; ?>">
                                <th scope="row">
                                    <label for="eva_chatbot_allowed_pages">
                                        <?php esc_html_e('Seleccionar Páginas', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <?php
                                    $pages = get_pages();
                                    if ($pages) {
                                        echo '<select id="eva_chatbot_allowed_pages" name="eva_chatbot_allowed_pages[]" multiple="multiple" size="10" style="width: 100%; max-width: 400px;">';
                                        foreach ($pages as $page) {
                                            $selected = in_array($page->ID, (array)$allowed_pages) ? 'selected="selected"' : '';
                                            echo '<option value="' . esc_attr($page->ID) . '" ' . $selected . '>' . 
                                                 esc_html($page->post_title) . '</option>';
                                        }
                                        echo '</select>';
                                        echo '<p class="description">' . 
                                             esc_html__('Mantén presionado Ctrl/Cmd para seleccionar múltiples páginas', 'eva-chatbot') . 
                                             '</p>';
                                    }
                                    ?>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Style Settings -->
                    <div class="eva-settings-section">
                        <h2><?php esc_html_e('Personalización de Estilo', 'eva-chatbot'); ?></h2>
                        
                        <table class="form-table">
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_primary_color">
                                        <?php esc_html_e('Color Principal', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="color" 
                                           id="eva_chatbot_primary_color" 
                                           name="eva_chatbot_primary_color" 
                                           value="<?php echo esc_attr($primary_color); ?>" />
                                    <span class="description">
                                        <?php esc_html_e('Color del botón y encabezado del chat', 'eva-chatbot'); ?>
                                    </span>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_text_color">
                                        <?php esc_html_e('Color del Texto', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <input type="color" 
                                           id="eva_chatbot_text_color" 
                                           name="eva_chatbot_text_color" 
                                           value="<?php echo esc_attr($text_color); ?>" />
                                    <span class="description">
                                        <?php esc_html_e('Color del texto en el botón y encabezado', 'eva-chatbot'); ?>
                                    </span>
                                </td>
                            </tr>
                            
                            <tr>
                                <th scope="row">
                                    <label for="eva_chatbot_button_size">
                                        <?php esc_html_e('Tamaño del Botón', 'eva-chatbot'); ?>
                                    </label>
                                </th>
                                <td>
                                    <select id="eva_chatbot_button_size" name="eva_chatbot_button_size">
                                        <option value="small" <?php selected($button_size, 'small'); ?>>
                                            <?php esc_html_e('Pequeño (50px)', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="medium" <?php selected($button_size, 'medium'); ?>>
                                            <?php esc_html_e('Mediano (60px)', 'eva-chatbot'); ?>
                                        </option>
                                        <option value="large" <?php selected($button_size, 'large'); ?>>
                                            <?php esc_html_e('Grande (70px)', 'eva-chatbot'); ?>
                                        </option>
                                    </select>
                                </td>
                            </tr>
                        </table>
                    </div>
                    
                    <!-- Test Connection -->
                    <div class="eva-settings-section">
                        <h2><?php esc_html_e('Probar Conexión', 'eva-chatbot'); ?></h2>
                        
                        <p>
                            <button type="button" 
                                    id="eva-test-connection" 
                                    class="button button-secondary">
                                <?php esc_html_e('Probar Conexión con el Servidor', 'eva-chatbot'); ?>
                            </button>
                            <span id="eva-test-result" style="margin-left: 10px;"></span>
                        </p>
                    </div>
                    
                    <p class="submit">
                        <input type="submit" 
                               name="eva_chatbot_save_settings" 
                               class="button button-primary" 
                               value="<?php esc_attr_e('Guardar Cambios', 'eva-chatbot'); ?>" />
                    </p>
                </div>
            </form>
        </div>
        
        <style>
            .eva-admin-container {
                max-width: 800px;
                background: #fff;
                padding: 20px;
                margin-top: 20px;
                border: 1px solid #ccd0d4;
                box-shadow: 0 1px 1px rgba(0,0,0,.04);
            }
            .eva-settings-section {
                margin-bottom: 40px;
                padding-bottom: 20px;
                border-bottom: 1px solid #eee;
            }
            .eva-settings-section:last-child {
                border-bottom: none;
            }
            .eva-settings-section h2 {
                color: #23282d;
                font-size: 1.3em;
                margin-bottom: 15px;
            }
            .eva-quick-reply-item {
                margin-bottom: 10px;
                padding: 10px;
                background: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 4px;
            }
            .eva-quick-reply-item input {
                margin-right: 10px;
                margin-bottom: 5px;
            }
            .eva-remove-reply {
                color: #a00;
            }
            .eva-remove-reply:hover {
                color: #dc3232;
            }
            /* Avatar Field Styles */
            .eva-avatar-field {
                display: flex;
                align-items: flex-start;
                gap: 20px;
            }
            .eva-avatar-preview {
                width: 100px;
                height: 100px;
                border: 2px solid #ddd;
                border-radius: 50%;
                overflow: hidden;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f9f9f9;
            }
            .eva-avatar-preview img {
                width: 100%;
                height: 100%;
                object-fit: cover;
            }
            .eva-default-avatar {
                width: 60px;
                height: 60px;
            }
            .eva-avatar-buttons {
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
        </style>
        
        <script>
        jQuery(document).ready(function($) {
            // Show/hide specific pages selector
            $('#eva_chatbot_display_rules').on('change', function() {
                if ($(this).val() === 'specific_pages') {
                    $('#eva_specific_pages_row').show();
                } else {
                    $('#eva_specific_pages_row').hide();
                }
            });
            
            // Test connection
            $('#eva-test-connection').on('click', function() {
                var button = $(this);
                var resultSpan = $('#eva-test-result');
                var serverUrl = $('#eva_chatbot_server_url').val();
                
                if (!serverUrl) {
                    resultSpan.html('<span style="color: red;"><?php esc_html_e('Por favor ingresa una URL del servidor', 'eva-chatbot'); ?></span>');
                    return;
                }
                
                button.prop('disabled', true).text('<?php esc_html_e('Probando...', 'eva-chatbot'); ?>');
                resultSpan.html('');
                
                $.ajax({
                    url: serverUrl + '/health',
                    method: 'GET',
                    timeout: 5000,
                    success: function(response) {
                        resultSpan.html('<span style="color: green;">✓ <?php esc_html_e('Conexión exitosa', 'eva-chatbot'); ?></span>');
                    },
                    error: function() {
                        resultSpan.html('<span style="color: red;">✗ <?php esc_html_e('No se pudo conectar al servidor', 'eva-chatbot'); ?></span>');
                    },
                    complete: function() {
                        button.prop('disabled', false).text('<?php esc_html_e('Probar Conexión con el Servidor', 'eva-chatbot'); ?>');
                    }
                });
            });
            
            // Quick Replies Management
            var replyIndex = $('#eva-quick-replies-container .eva-quick-reply-item').length;
            
            // Add new reply
            $('#eva-add-reply').on('click', function() {
                if ($('#eva-quick-replies-container .eva-quick-reply-item').length >= 5) {
                    alert('<?php esc_html_e('Máximo 5 respuestas rápidas permitidas', 'eva-chatbot'); ?>');
                    return;
                }
                
                var newReply = '<div class="eva-quick-reply-item" data-index="' + replyIndex + '">' +
                    '<input type="text" name="eva_quick_replies[' + replyIndex + '][text]" ' +
                    'placeholder="<?php esc_attr_e('Texto del botón', 'eva-chatbot'); ?>" class="regular-text" /> ' +
                    '<input type="text" name="eva_quick_replies[' + replyIndex + '][message]" ' +
                    'placeholder="<?php esc_attr_e('Mensaje a enviar', 'eva-chatbot'); ?>" class="regular-text" /> ' +
                    '<button type="button" class="button eva-remove-reply"><?php esc_html_e('Eliminar', 'eva-chatbot'); ?></button>' +
                    '</div>';
                
                $('#eva-quick-replies-container').append(newReply);
                replyIndex++;
            });
            
            // Remove reply
            $(document).on('click', '.eva-remove-reply', function() {
                $(this).closest('.eva-quick-reply-item').remove();
                
                // Reindex remaining items
                $('#eva-quick-replies-container .eva-quick-reply-item').each(function(index) {
                    $(this).attr('data-index', index);
                    $(this).find('input').each(function() {
                        var name = $(this).attr('name');
                        if (name) {
                            name = name.replace(/\[\d+\]/, '[' + index + ']');
                            $(this).attr('name', name);
                        }
                    });
                });
            });
            
            // Media Uploader for Avatar
            var mediaUploader;
            
            $('#eva-select-avatar').on('click', function(e) {
                e.preventDefault();
                
                // If the uploader object has already been created, reopen it
                if (mediaUploader) {
                    mediaUploader.open();
                    return;
                }
                
                // Create the media uploader
                mediaUploader = wp.media({
                    title: '<?php esc_html_e('Seleccionar Avatar del Chatbot', 'eva-chatbot'); ?>',
                    button: {
                        text: '<?php esc_html_e('Usar como Avatar', 'eva-chatbot'); ?>'
                    },
                    multiple: false,
                    library: {
                        type: 'image'
                    }
                });
                
                // When an image is selected
                mediaUploader.on('select', function() {
                    var attachment = mediaUploader.state().get('selection').first().toJSON();
                    
                    // Set the attachment ID
                    $('#eva_chatbot_avatar_id').val(attachment.id);
                    
                    // Update preview
                    var imageUrl = attachment.sizes.thumbnail ? attachment.sizes.thumbnail.url : attachment.url;
                    $('#eva-avatar-preview').html('<img src="' + imageUrl + '" alt="Avatar" />');
                    
                    // Show remove button
                    $('#eva-remove-avatar').show();
                });
                
                // Open the uploader
                mediaUploader.open();
            });
            
            // Remove avatar
            $('#eva-remove-avatar').on('click', function(e) {
                e.preventDefault();
                
                // Clear the ID
                $('#eva_chatbot_avatar_id').val('');
                
                // Restore default avatar
                $('#eva-avatar-preview').html(`
                    <div class="eva-default-avatar">
                        <svg width="60" height="60" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                            <circle cx="12" cy="12" r="10" fill="#54841e" opacity="0.1"/>
                            <path d="M12 2C6.48 2 2 6.48 2 12C2 17.52 6.48 22 12 22C17.52 22 22 17.52 22 12C22 6.48 17.52 2 12 2ZM12 4C13.66 4 15 5.34 15 7C15 8.66 13.66 10 12 10C10.34 10 9 8.66 9 7C9 5.34 10.34 4 12 4ZM12 20C9.33 20 6.99 18.78 5.49 16.82C5.52 14.41 9.58 13.1 12 13.1C14.41 13.1 18.48 14.41 18.51 16.82C17.01 18.78 14.67 20 12 20Z" fill="#54841e"/>
                        </svg>
                    </div>
                `);
                
                // Hide remove button
                $(this).hide();
            });
        });
        </script>
        <?php
    }
    
    private function save_settings() {
        // General settings
        update_option('eva_chatbot_enabled', isset($_POST['eva_chatbot_enabled']) ? '1' : '0');
        update_option('eva_chatbot_server_url', esc_url_raw($_POST['eva_chatbot_server_url']));
        update_option('eva_chatbot_name', sanitize_text_field($_POST['eva_chatbot_name']));
        update_option('eva_chatbot_avatar_id', absint($_POST['eva_chatbot_avatar_id']));
        update_option('eva_chatbot_welcome_message', sanitize_textarea_field($_POST['eva_chatbot_welcome_message']));
        update_option('eva_chatbot_typing_message', sanitize_text_field($_POST['eva_chatbot_typing_message']));
        update_option('eva_chatbot_error_message', sanitize_text_field($_POST['eva_chatbot_error_message']));
        update_option('eva_chatbot_auto_open_delay', sanitize_text_field($_POST['eva_chatbot_auto_open_delay']));
        
        // Quick replies
        $quick_replies = array();
        if (isset($_POST['eva_quick_replies']) && is_array($_POST['eva_quick_replies'])) {
            foreach ($_POST['eva_quick_replies'] as $reply) {
                if (!empty($reply['text']) && !empty($reply['message'])) {
                    $quick_replies[] = array(
                        'text' => sanitize_text_field($reply['text']),
                        'message' => sanitize_text_field($reply['message'])
                    );
                }
            }
        }
        update_option('eva_chatbot_quick_replies', json_encode($quick_replies));
        
        // Display settings
        update_option('eva_chatbot_position', sanitize_text_field($_POST['eva_chatbot_position']));
        update_option('eva_chatbot_display_rules', sanitize_text_field($_POST['eva_chatbot_display_rules']));
        
        if (isset($_POST['eva_chatbot_allowed_pages'])) {
            $allowed_pages = array_map('intval', $_POST['eva_chatbot_allowed_pages']);
            update_option('eva_chatbot_allowed_pages', $allowed_pages);
        } else {
            update_option('eva_chatbot_allowed_pages', array());
        }
        
        // Style settings
        update_option('eva_chatbot_primary_color', sanitize_hex_color($_POST['eva_chatbot_primary_color']));
        update_option('eva_chatbot_text_color', sanitize_hex_color($_POST['eva_chatbot_text_color']));
        update_option('eva_chatbot_button_size', sanitize_text_field($_POST['eva_chatbot_button_size']));
    }
}