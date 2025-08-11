#!/usr/bin/env python3
"""
Check if API keys are properly configured
"""

import os
import sys
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()
load_dotenv('env.agent')

def check_api_keys():
    """Check API keys configuration"""
    
    print("🔑 Checking API Keys Configuration\n")
    print("=" * 60)
    
    # Check OpenAI API Key
    openai_key = os.getenv('OPENAI_API_KEY', '')
    print("\n1️⃣ OpenAI API Key:")
    if not openai_key:
        print("  ❌ Not found - Set OPENAI_API_KEY in env.agent")
    elif openai_key == "sk-demo-key" or openai_key.startswith("sk-demo"):
        print("  ❌ Demo key detected - Please set a valid OpenAI API key")
        print("  💡 Get your key from: https://platform.openai.com/api-keys")
    elif openai_key.startswith("sk-"):
        print("  ✅ Found (starts with 'sk-')")
    else:
        print("  ⚠️ Found but format looks unusual")
    
    # Check Anthropic API Key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY', '')
    print("\n2️⃣ Anthropic API Key:")
    if not anthropic_key:
        print("  ❌ Not found - Set ANTHROPIC_API_KEY in env.agent")
    elif anthropic_key == "sk-demo-key" or anthropic_key.startswith("demo"):
        print("  ❌ Demo key detected - Please set a valid Anthropic API key")
    elif anthropic_key.startswith("sk-"):
        print("  ✅ Found (starts with 'sk-')")
    else:
        print("  ⚠️ Found but format looks unusual")
    
    # Check WooCommerce credentials
    print("\n3️⃣ WooCommerce Credentials:")
    woo_url = os.getenv('WOOCOMMERCE_URL', '')
    woo_key = os.getenv('WOOCOMMERCE_KEY', '')
    woo_secret = os.getenv('WOOCOMMERCE_SECRET', '')
    
    if not woo_url:
        print("  ❌ WOOCOMMERCE_URL not found")
    else:
        print(f"  ✅ URL: {woo_url}")
    
    if not woo_key:
        print("  ❌ WOOCOMMERCE_KEY not found")
    elif woo_key.startswith("ck_"):
        print("  ✅ Consumer Key found (starts with 'ck_')")
    else:
        print("  ⚠️ Consumer Key found but format looks unusual")
    
    if not woo_secret:
        print("  ❌ WOOCOMMERCE_SECRET not found")
    elif woo_secret.startswith("cs_"):
        print("  ✅ Consumer Secret found (starts with 'cs_')")
    else:
        print("  ⚠️ Consumer Secret found but format looks unusual")
    
    # Check database URL
    print("\n4️⃣ Database Configuration:")
    db_url = os.getenv('DATABASE_URL', '')
    if not db_url:
        print("  ❌ DATABASE_URL not found")
    elif "postgresql://" in db_url or "postgres://" in db_url:
        print("  ✅ PostgreSQL URL found")
    else:
        print("  ⚠️ DATABASE_URL found but format looks unusual")
    
    print("\n" + "=" * 60)
    print("📊 SUMMARY")
    print("=" * 60)
    print("\nTo fix missing or invalid keys:")
    print("1. Copy env.agent.example to env.agent if not exists")
    print("2. Edit env.agent and add your actual API keys")
    print("3. For OpenAI: https://platform.openai.com/api-keys")
    print("4. For Anthropic: https://console.anthropic.com/")
    print("5. For WooCommerce: Get from your WordPress admin panel")

if __name__ == "__main__":
    check_api_keys()