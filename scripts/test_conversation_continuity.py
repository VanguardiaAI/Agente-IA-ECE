#!/usr/bin/env python3
"""
Test script to verify conversation continuity fix
"""

import asyncio
import sys
import os
import json
import time
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.metrics_service import MetricsService
from config.settings import settings
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_conversation_continuity():
    """Test that conversations continue across multiple messages"""
    
    # Initialize metrics service
    metrics = MetricsService(settings.DATABASE_URL)
    await metrics.initialize()
    
    test_user_id = "test_user_123"
    platform = "wordpress"
    
    print("\n🧪 Testing conversation continuity...")
    print("=" * 50)
    
    # Test 1: Create first conversation
    print("\n1️⃣ Creating first message...")
    conv_id_1 = await metrics.find_or_create_conversation(
        user_id=test_user_id,
        platform=platform,
        channel_details={"test": "first_message"}
    )
    print(f"   Conversation ID: {conv_id_1}")
    
    # Track a message
    await metrics.track_message(
        conversation_id=conv_id_1,
        sender_type="user",
        content="Hello, I need help"
    )
    
    # Test 2: Second message should use same conversation
    print("\n2️⃣ Creating second message (should use same conversation)...")
    await asyncio.sleep(1)  # Small delay
    
    conv_id_2 = await metrics.find_or_create_conversation(
        user_id=test_user_id,
        platform=platform,
        channel_details={"test": "second_message"}
    )
    print(f"   Conversation ID: {conv_id_2}")
    
    if conv_id_1 == conv_id_2:
        print("   ✅ SUCCESS: Same conversation ID used!")
    else:
        print("   ❌ FAILURE: Different conversation ID created!")
    
    # Track another message
    await metrics.track_message(
        conversation_id=conv_id_2,
        sender_type="user",
        content="Can you show me your products?"
    )
    
    # Test 3: Check conversation details
    print("\n3️⃣ Checking conversation details...")
    async with metrics.pool.acquire() as conn:
        conv_details = await conn.fetchrow("""
            SELECT messages_count, user_messages_count, bot_messages_count, status
            FROM conversations
            WHERE conversation_id = $1
        """, conv_id_1)
        
        if conv_details:
            print(f"   Total messages: {conv_details['messages_count']}")
            print(f"   User messages: {conv_details['user_messages_count']}")
            print(f"   Bot messages: {conv_details['bot_messages_count']}")
            print(f"   Status: {conv_details['status']}")
            
            if conv_details['messages_count'] >= 2:
                print("   ✅ Messages properly tracked in same conversation!")
            else:
                print("   ❌ Messages not properly tracked!")
    
    # Test 4: Test timeout behavior
    print("\n4️⃣ Testing timeout behavior (waiting 2 seconds with 1 second timeout)...")
    await asyncio.sleep(2)
    
    conv_id_3 = await metrics.find_or_create_conversation(
        user_id=test_user_id,
        platform=platform,
        channel_details={"test": "after_timeout"},
        timeout_minutes=0.0167  # 1 second in minutes
    )
    print(f"   Conversation ID: {conv_id_3}")
    
    if conv_id_1 != conv_id_3:
        print("   ✅ SUCCESS: New conversation created after timeout!")
    else:
        print("   ❌ FAILURE: Same conversation used after timeout!")
    
    # Test 5: Different user should get different conversation
    print("\n5️⃣ Testing different user...")
    conv_id_4 = await metrics.find_or_create_conversation(
        user_id="different_user_456",
        platform=platform,
        channel_details={"test": "different_user"}
    )
    print(f"   Conversation ID: {conv_id_4}")
    
    if conv_id_1 != conv_id_4:
        print("   ✅ SUCCESS: Different conversation for different user!")
    else:
        print("   ❌ FAILURE: Same conversation used for different user!")
    
    # Clean up test data
    print("\n🧹 Cleaning up test data...")
    async with metrics.pool.acquire() as conn:
        await conn.execute("""
            DELETE FROM conversation_messages 
            WHERE conversation_id IN ($1, $2, $3, $4)
        """, conv_id_1, conv_id_2, conv_id_3, conv_id_4)
        
        await conn.execute("""
            DELETE FROM conversations 
            WHERE conversation_id IN ($1, $2, $3, $4)
        """, conv_id_1, conv_id_2, conv_id_3, conv_id_4)
    
    await metrics.close()
    
    print("\n✅ Test completed!")
    print("=" * 50)

async def main():
    """Main function"""
    try:
        await test_conversation_continuity()
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())