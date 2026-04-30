#!/usr/bin/env python3
"""
Token Validation Script
Checks if Telegram bot token is valid
"""

import asyncio
import sys
import os
from telegram import Bot
from dotenv import load_dotenv

load_dotenv()


async def check_token():
    """Validate Telegram bot token"""
    token = os.getenv('TELEGRAM_TOKEN', '').strip()
    
    print("\n" + "="*60)
    print("🔍 TELEGRAM TOKEN VALIDATOR")
    print("="*60 + "\n")
    
    if not token:
        print("❌ ERROR: No TELEGRAM_TOKEN found in .env file!")
        print("\n📝 Steps to fix:")
        print("1. Create/edit .env file")
        print("2. Add: TELEGRAM_TOKEN=your_token_here")
        print("3. Get token from @BotFather on Telegram")
        return False
    
    print(f"Token (preview): {token[:25]}...")
    print("\nValidating with Telegram API...\n")
    
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        
        print("✅ TOKEN IS VALID!\n")
        print("="*60)
        print(f"🤖 Bot Name: {me.first_name}")
        print(f"👤 Username: @{me.username}")
        print(f"🆔 Bot ID: {me.id}")
        print(f"👥 Can Join Groups: {'Yes' if me.can_join_groups else 'No'}")
        print(f"📖 Can Read All Messages: {'Yes' if me.can_read_all_group_messages else 'No'}")
        print("="*60)
        print("\n✅ Your bot is ready!")
        print("▶️  Run: python main.py\n")
        
        return True
        
    except Exception as e:
        print("❌ TOKEN IS INVALID!\n")
        print("="*60)
        print(f"Error: {str(e)}")
        print("="*60)
        print("\n📝 How to get a valid token:")
        print("1. Open Telegram")
        print("2. Search for: @BotFather")
        print("3. Send: /newbot (or /mybots for existing)")
        print("4. Follow instructions")
        print("5. Copy the token")
        print("6. Update .env: TELEGRAM_TOKEN=paste_token_here")
        print("\n")
        return False


if __name__ == '__main__':
    try:
        result = asyncio.run(check_token())
        sys.exit(0 if result else 1)
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user.")
        sys.exit(1)
