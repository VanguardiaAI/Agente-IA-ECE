#!/usr/bin/env python3
"""
Script to patch the conversation tracking issue directly in the existing files
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def patch_metrics_service():
    """Add find_or_create_conversation method to MetricsService"""
    
    # Read the current metrics_service.py
    with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/services/metrics_service.py', 'r') as f:
        content = f.read()
    
    # Check if method already exists
    if 'find_or_create_conversation' in content:
        print("✅ find_or_create_conversation method already exists in metrics_service.py")
        return
    
    # Find where to insert the new method (after __init__)
    init_end = content.find('async def initialize(self):')
    if init_end == -1:
        print("❌ Could not find initialize method in metrics_service.py")
        return
        
    # Add timeout property to __init__
    init_method_start = content.find('def __init__(self, database_url: str):')
    init_method_end = content.find('async def initialize(self):', init_method_start)
    init_section = content[init_method_start:init_method_end]
    
    if 'conversation_timeout_minutes' not in init_section:
        # Add the timeout property
        lines = init_section.split('\n')
        for i, line in enumerate(lines):
            if 'self.active_conversations = {}' in line:
                lines.insert(i + 1, '        self.conversation_timeout_minutes = 30  # Timeout por defecto')
                break
        
        new_init = '\n'.join(lines)
        content = content[:init_method_start] + new_init + content[init_method_end:]
    
    # Insert the new method before start_conversation
    start_conv_pos = content.find('async def start_conversation(')
    if start_conv_pos == -1:
        print("❌ Could not find start_conversation method")
        return
    
    # Find the proper indentation by looking at the line before
    lines_before = content[:start_conv_pos].split('\n')
    last_line = lines_before[-2] if len(lines_before) > 1 else ''
    indent = '    '  # Default 4 spaces
    
    new_method = '''
    async def find_or_create_conversation(
        self,
        user_id: str,
        platform: str = "wordpress",
        channel_details: Dict[str, Any] = None,
        timeout_minutes: Optional[int] = None
    ) -> str:
        """Buscar conversación activa o crear una nueva si no existe o expiró"""
        
        if timeout_minutes is None:
            timeout_minutes = self.conversation_timeout_minutes
            
        async with self.pool.acquire() as conn:
            try:
                # Buscar conversación activa
                result = await conn.fetchrow("""
                    SELECT conversation_id, started_at, messages_count, updated_at
                    FROM conversations
                    WHERE user_id = $1 
                        AND platform = $2
                        AND status = 'active'
                        AND updated_at >= NOW() - INTERVAL '1 minute' * $3
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, user_id, platform, timeout_minutes)
                
                if result:
                    conversation_id = result['conversation_id']
                    logger.info(f"Conversación existente encontrada: {conversation_id} (mensajes: {result['messages_count']})")
                    
                    # Actualizar timestamp de última actividad
                    await conn.execute("""
                        UPDATE conversations 
                        SET updated_at = NOW()
                        WHERE conversation_id = $1
                    """, conversation_id)
                    
                    # Actualizar cache
                    if conversation_id not in self.active_conversations:
                        self.active_conversations[conversation_id] = {
                            'user_id': user_id,
                            'platform': platform,
                            'started_at': result['started_at'],
                            'message_times': []
                        }
                    
                    return conversation_id
                else:
                    # Crear nueva conversación
                    return await self.start_conversation(user_id, platform, channel_details)
                    
            except Exception as e:
                logger.error(f"Error en find_or_create_conversation: {e}")
                # En caso de error, crear nueva conversación
                return await self.start_conversation(user_id, platform, channel_details)
    
'''
    
    # Insert the new method
    new_content = content[:start_conv_pos] + new_method + content[start_conv_pos:]
    
    # Write back the file
    with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/services/metrics_service.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Added find_or_create_conversation method to metrics_service.py")

def patch_app_py():
    """Update app.py to use find_or_create_conversation"""
    
    # Read the current app.py
    with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/app.py', 'r') as f:
        content = f.read()
    
    # Check if already patched
    if 'find_or_create_conversation' in content:
        print("✅ app.py already uses find_or_create_conversation")
        return
    
    # Replace the start_conversation call
    old_code = '''conversation_id = await metrics_service.start_conversation(
                user_id=chat_message.user_id,
                platform=chat_message.platform,
                channel_details={
                    "source": "api",
                    "user_agent": request.headers.get("user-agent", ""),
                    "ip": request.client.host if request.client else None
                }
            )'''
    
    new_code = '''conversation_id = await metrics_service.find_or_create_conversation(
                user_id=chat_message.user_id,
                platform=chat_message.platform,
                channel_details={
                    "source": "api",
                    "user_agent": request.headers.get("user-agent", ""),
                    "ip": request.client.host if request.client else None
                },
                timeout_minutes=30  # Conversations timeout after 30 minutes of inactivity
            )'''
    
    if old_code in content:
        content = content.replace(old_code, new_code)
        
        # Write back the file
        with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/app.py', 'w') as f:
            f.write(content)
        
        print("✅ Updated app.py to use find_or_create_conversation")
    else:
        print("⚠️  Could not find the exact code to replace in app.py")
        print("Please manually update the /api/chat endpoint to use find_or_create_conversation")

def main():
    """Main function"""
    print("🔧 Patching conversation tracking issue...")
    
    # Patch metrics_service.py
    patch_metrics_service()
    
    # Patch app.py
    patch_app_py()
    
    print("""
✅ Patching complete!

The conversation tracking has been fixed. Now:
- Conversations will continue for up to 30 minutes of inactivity
- Each user will have one active conversation per platform
- Messages will be properly grouped in the same conversation

Please restart the application for changes to take effect.
""")

if __name__ == "__main__":
    main()