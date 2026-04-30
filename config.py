import os
import sys
from dotenv import load_dotenv

load_dotenv()

# ============================================
# TELEGRAM CONFIGURATION
# ============================================
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()
WEBHOOK_URL = os.getenv('WEBHOOK_URL', '').strip()
OWNER_ID = int(os.getenv('OWNER_ID', '0'))

# Validate Telegram Token
if not TELEGRAM_TOKEN:
    print("\n" + "="*60)
    print("❌ ERROR: TELEGRAM_TOKEN not found in .env file!")
    print("="*60)
    print("\n📝 How to get a Telegram Bot Token:")
    print("1. Open Telegram app")
    print("2. Search for @BotFather")
    print("3. Send: /newbot")
    print("4. Follow the instructions")
    print("5. Copy the token you receive")
    print("6. Add to .env file: TELEGRAM_TOKEN=your_token_here")
    print("\n" + "="*60 + "\n")
    sys.exit(1)

if ':' not in TELEGRAM_TOKEN or len(TELEGRAM_TOKEN) < 20:
    print("\n" + "="*60)
    print("❌ ERROR: Invalid Telegram token format!")
    print("="*60)
    print(f"Current token: {TELEGRAM_TOKEN[:20]}...")
    print("\n✅ Valid format example: 1234567890:ABCdefGHIjklMNOpqrsTUVwxyz")
    print("\n📝 Get a new token from @BotFather on Telegram")
    print("="*60 + "\n")
    sys.exit(1)

# ============================================
# API KEYS CONFIGURATION
# ============================================

# GROQ API Keys (Free, Fast - Primary)
GROQ_KEYS = [
    os.getenv('GROQ_API_KEY'),
    os.getenv('GROQ_API_KEY1'),
    os.getenv('GROQ_API_KEY2'),
    os.getenv('GROQ_API_KEY3'),
]
GROQ_KEYS = [key.strip() for key in GROQ_KEYS if key and len(key.strip()) > 10]

# Gemini API Keys (Free - Secondary)
GEMINI_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_API_KEY1'),
]
GEMINI_KEYS = [key.strip() for key in GEMINI_KEYS if key and len(key.strip()) > 10]

# OpenRouter API Keys (Free tier - Tertiary)
OPENROUTER_KEYS = [
    os.getenv('OPENROUTER_API_KEY'),
    os.getenv('OPENROUTER_API_KEY2'),
]
OPENROUTER_KEYS = [key.strip() for key in OPENROUTER_KEYS if key and len(key.strip()) > 10]

# OpenAI (Paid fallback - Optional)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
OPENAI_API_KEY = OPENAI_API_KEY if len(OPENAI_API_KEY) > 10 else None

# Sarvam AI (Free Indian TTS)
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '').strip()
SARVAM_API_KEY = SARVAM_API_KEY if len(SARVAM_API_KEY) > 10 else None

# Other APIs
NEWS_API_KEY = os.getenv('NEWS_API_KEY', '').strip()
SERPAPI_KEY = os.getenv('SERPAPI_KEY', '').strip()
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY', '').strip()
CITY = os.getenv('CITY', 'Mumbai')

# ============================================
# BOT SETTINGS
# ============================================
MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY_LENGTH = 10
SESSION_TIMEOUT = 3600
AUDIO_DIR = 'audio_files'

# Create directories
os.makedirs(AUDIO_DIR, exist_ok=True)

# ============================================
# API PRIORITY CONFIGURATION
# ============================================
API_PRIORITY = []
if GROQ_KEYS:
    API_PRIORITY.append('groq')
if GEMINI_KEYS:
    API_PRIORITY.append('gemini')
if OPENROUTER_KEYS:
    API_PRIORITY.append('openrouter')
if OPENAI_API_KEY:
    API_PRIORITY.append('openai')

if not API_PRIORITY:
    print("\n" + "="*60)
    print("⚠️  WARNING: No AI API keys found!")
    print("="*60)
    print("\nThe bot needs at least one AI service to work.")
    print("\n📝 Free Options (Recommended):")
    print("1. GROQ - https://console.groq.com (Fast & Free)")
    print("2. Gemini - https://makersuite.google.com/app/apikey")
    print("3. OpenRouter - https://openrouter.ai (Free tier)")
    print("\nAdd keys to your .env file")
    print("="*60 + "\n")

# Voice Provider Priority
VOICE_PRIORITY = ['edge-tts', 'gtts']  # Free options
if SARVAM_API_KEY:
    VOICE_PRIORITY.insert(0, 'sarvam')

# ============================================
# STARTUP CONFIGURATION DISPLAY
# ============================================
def print_config():
    """Print configuration status"""
    print("\n" + "="*60)
    print("🤖 ADIMA BOT CONFIGURATION STATUS")
    print("="*60)
    
    # Telegram
    print(f"\n📱 Telegram:")
    print(f"   Token: ✅ Valid")
    print(f"   Owner ID: {OWNER_ID}")
    
    # AI Services
    print(f"\n🧠 AI Services:")
    print(f"   GROQ Keys: {len(GROQ_KEYS)} {'✅' if GROQ_KEYS else '❌'}")
    print(f"   Gemini Keys: {len(GEMINI_KEYS)} {'✅' if GEMINI_KEYS else '❌'}")
    print(f"   OpenRouter Keys: {len(OPENROUTER_KEYS)} {'✅' if OPENROUTER_KEYS else '❌'}")
    print(f"   OpenAI: {'✅ Yes' if OPENAI_API_KEY else '❌ No'}")
    
    # Voice Services
    print(f"\n🎤 Voice Services:")
    print(f"   Sarvam TTS: {'✅ Yes' if SARVAM_API_KEY else '❌ No'}")
    print(f"   Edge TTS: ✅ Built-in (Free)")
    print(f"   Google TTS: ✅ Built-in (Free)")
    
    # Priority
    print(f"\n📊 Service Priority:")
    print(f"   AI: {' → '.join(API_PRIORITY) if API_PRIORITY else '❌ None'}")
    print(f"   Voice: {' → '.join(VOICE_PRIORITY)}")
    
    print("\n" + "="*60 + "\n")

# Auto-print config on import
print_config()
