import os
import sys
from dotenv import load_dotenv

load_dotenv()

# Telegram
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '').strip()
OWNER_ID = int(os.getenv('OWNER_ID', '0'))

# Validate token
if not TELEGRAM_TOKEN or ':' not in TELEGRAM_TOKEN:
    print("\n❌ ERROR: Invalid TELEGRAM_TOKEN in .env file!")
    print("Get token from @BotFather on Telegram\n")
    sys.exit(1)

# GROQ Keys
GROQ_KEYS = [
    os.getenv('GROQ_API_KEY'),
    os.getenv('GROQ_API_KEY1'),
    os.getenv('GROQ_API_KEY2'),
    os.getenv('GROQ_API_KEY3'),
]
GROQ_KEYS = [k.strip() for k in GROQ_KEYS if k and len(k.strip()) > 10]

# Gemini Keys
GEMINI_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_API_KEY1'),
]
GEMINI_KEYS = [k.strip() for k in GEMINI_KEYS if k and len(k.strip()) > 10]

# OpenRouter Keys
OPENROUTER_KEYS = [
    os.getenv('OPENROUTER_API_KEY'),
    os.getenv('OPENROUTER_API_KEY2'),
]
OPENROUTER_KEYS = [k.strip() for k in OPENROUTER_KEYS if k and len(k.strip()) > 10]

# OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '').strip()
OPENAI_API_KEY = OPENAI_API_KEY if len(OPENAI_API_KEY) > 10 else None

# Sarvam
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY', '').strip()
SARVAM_API_KEY = SARVAM_API_KEY if len(SARVAM_API_KEY) > 10 else None

# Settings
MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY_LENGTH = 10
SESSION_TIMEOUT = 3600
AUDIO_DIR = 'audio_files'

# Create dirs
os.makedirs(AUDIO_DIR, exist_ok=True)

# Priority
API_PRIORITY = []
if GROQ_KEYS:
    API_PRIORITY.append('groq')
if GEMINI_KEYS:
    API_PRIORITY.append('gemini')
if OPENROUTER_KEYS:
    API_PRIORITY.append('openrouter')
if OPENAI_API_KEY:
    API_PRIORITY.append('openai')

VOICE_PRIORITY = ['edge-tts', 'gtts']
if SARVAM_API_KEY:
    VOICE_PRIORITY.insert(0, 'sarvam')

# Print config
print("\n" + "="*60)
print("🤖 ADIMA BOT CONFIGURATION")
print("="*60)
print(f"✅ Telegram: OK")
print(f"✅ GROQ Keys: {len(GROQ_KEYS)}")
print(f"✅ Gemini Keys: {len(GEMINI_KEYS)}")
print(f"✅ OpenRouter Keys: {len(OPENROUTER_KEYS)}")
print(f"✅ OpenAI: {'Yes' if OPENAI_API_KEY else 'No'}")
print(f"✅ Sarvam: {'Yes' if SARVAM_API_KEY else 'No'}")
print(f"\n📊 AI Priority: {' → '.join(API_PRIORITY)}")
print(f"🎤 Voice Priority: {' → '.join(VOICE_PRIORITY)}")
print("="*60 + "\n")
