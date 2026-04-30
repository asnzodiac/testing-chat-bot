import os
from dotenv import load_dotenv

load_dotenv()

# Telegram Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
OWNER_ID = int(os.getenv('OWNER_ID', '0'))

# GROQ API Keys (Free, Fast - Primary)
GROQ_KEYS = [
    os.getenv('GROQ_API_KEY'),
    os.getenv('GROQ_API_KEY1'),
    os.getenv('GROQ_API_KEY2'),
    os.getenv('GROQ_API_KEY3'),
]
GROQ_KEYS = [key for key in GROQ_KEYS if key]  # Filter out None values

# Gemini API Keys (Free - Secondary)
GEMINI_KEYS = [
    os.getenv('GEMINI_API_KEY'),
    os.getenv('GEMINI_API_KEY1'),
]
GEMINI_KEYS = [key for key in GEMINI_KEYS if key]

# OpenRouter API Keys (Free tier - Tertiary)
OPENROUTER_KEYS = [
    os.getenv('OPENROUTER_API_KEY'),
    os.getenv('OPENROUTER_API_KEY2'),
]
OPENROUTER_KEYS = [key for key in OPENROUTER_KEYS if key]

# OpenAI (Paid fallback)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Sarvam AI (Free Indian TTS)
SARVAM_API_KEY = os.getenv('SARVAM_API_KEY')

# Other APIs
NEWS_API_KEY = os.getenv('NEWS_API_KEY')
SERPAPI_KEY = os.getenv('SERPAPI_KEY')
OPENWEATHER_API_KEY = os.getenv('OPENWEATHER_API_KEY')
CITY = os.getenv('CITY', 'Mumbai')

# Bot Settings
MAX_MESSAGE_LENGTH = 4000
MAX_HISTORY_LENGTH = 10
SESSION_TIMEOUT = 3600
AUDIO_DIR = 'audio_files'

# Create directories
os.makedirs(AUDIO_DIR, exist_ok=True)

# API Priority Order
API_PRIORITY = ['groq', 'gemini', 'openrouter', 'openai']

# Voice Provider Priority
VOICE_PRIORITY = ['sarvam', 'edge-tts', 'gtts']  # All free!

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN is required!")
