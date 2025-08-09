#!/usr/bin/env python3
"""
Script to patch WhatsApp webhook processing to use find_or_create_conversation
"""

import re

def patch_whatsapp_processing():
    """Update WhatsApp message processing to use find_or_create_conversation"""
    
    # Read the current app.py
    with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/app.py', 'r') as f:
        content = f.read()
    
    # Find the _process_whatsapp_message function
    pattern = r'(conversation_id = await metrics_service\.start_conversation\(\s*user_id=from_number,\s*platform="whatsapp",\s*channel_details=\{[^}]+\}\s*\))'
    
    replacement = '''conversation_id = await metrics_service.find_or_create_conversation(
                    user_id=from_number,
                    platform="whatsapp",
                    channel_details={
                        "source": "360dialog",
                        "message_id": message_data.get("id"),
                        "phone": from_number
                    },
                    timeout_minutes=30  # Conversations timeout after 30 minutes of inactivity
                )'''
    
    # Check if already patched
    if 'find_or_create_conversation' in content and 'from_number' in content:
        print("✅ WhatsApp webhook processing already uses find_or_create_conversation")
        return True
    
    # Replace the pattern
    new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE | re.DOTALL)
    
    if new_content == content:
        print("⚠️  Could not find the exact code to replace for WhatsApp processing")
        print("Please manually update the _process_whatsapp_message function")
        return False
    
    # Write back the file
    with open('/Users/vanguardia/Desktop/Proyectos/MCP-WC/app.py', 'w') as f:
        f.write(new_content)
    
    print("✅ Updated WhatsApp webhook processing to use find_or_create_conversation")
    return True

def main():
    """Main function"""
    print("🔧 Patching WhatsApp conversation tracking...")
    
    success = patch_whatsapp_processing()
    
    if success:
        print("""
✅ WhatsApp patching complete!

Now all conversation tracking (both REST API and WhatsApp webhooks) will:
- Continue conversations for up to 30 minutes of inactivity
- Properly group messages in the same conversation
- Avoid creating new conversations for each message

Please restart the application for changes to take effect.
""")
    else:
        print("""
⚠️  Manual update needed for WhatsApp webhook processing.

In the _process_whatsapp_message function in app.py, replace:

    conversation_id = await metrics_service.start_conversation(
        user_id=from_number,
        platform="whatsapp",
        channel_details={...}
    )

With:

    conversation_id = await metrics_service.find_or_create_conversation(
        user_id=from_number,
        platform="whatsapp",
        channel_details={...},
        timeout_minutes=30
    )
""")

if __name__ == "__main__":
    main()