import logging
from datetime import datetime, timedelta
from typing import Dict, List
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import (
    TELEGRAM_TOKEN,
    MAX_MESSAGE_LENGTH,
    MAX_HISTORY_LENGTH,
    SESSION_TIMEOUT,
    OWNER_ID,
    AUDIO_DIR
)
from api_manager import APIManager
from voice_manager import VoiceManager

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize managers
api_manager = APIManager()
voice_manager = VoiceManager()

# User sessions
user_sessions: Dict[int, Dict] = {}


class UserSession:
    """User conversation session"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conversation_history: List[Dict] = []
        self.last_activity = datetime.now()
        self.voice_enabled = False
        self.language = 'en'
        self.system_prompt = """You are Adima, a helpful, friendly, and intelligent AI assistant. 
You provide clear, concise, and accurate responses. You're empathetic and engaging."""
    
    def add_message(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        self.last_activity = datetime.now()
        
        if len(self.conversation_history) > MAX_HISTORY_LENGTH * 2:
            self.conversation_history = self.conversation_history[-MAX_HISTORY_LENGTH * 2:]
    
    def get_messages(self) -> List[Dict]:
        return [{"role": "system", "content": self.system_prompt}] + self.conversation_history
    
    def is_expired(self) -> bool:
        return datetime.now() - self.last_activity > timedelta(seconds=SESSION_TIMEOUT)
    
    def clear(self):
        self.conversation_history = []
        self.last_activity = datetime.now()


def get_or_create_session(user_id: int) -> UserSession:
    if user_id not in user_sessions or user_sessions[user_id].is_expired():
        user_sessions[user_id] = UserSession(user_id)
    return user_sessions[user_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command with welcome message"""
    user = update.effective_user
    
    keyboard = [
        [
            InlineKeyboardButton("🎤 Enable Voice", callback_data='toggle_voice'),
            InlineKeyboardButton("📊 Stats", callback_data='stats')
        ],
        [
            InlineKeyboardButton("🌍 Language", callback_data='language'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""👋 **Welcome {user.first_name}!**

I'm **Adima**, your advanced AI assistant powered by multiple AI services!

✨ **Features:**
• 🤖 Smart conversations (Multi-API fallback)
• 🎤 Natural voice responses (FREE TTS)
• 🌍 Multi-language support
• 📊 Real-time stats
• 🔄 100% uptime guarantee

**Quick Commands:**
/start - Show this menu
/voice - Toggle voice responses
/clear - Clear chat history
/stats - View API statistics
/help - Get help

Just send me a message to begin! 💬"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """🤖 **Adima Bot Help**

**Available Commands:**
/start - Start the bot
/voice - Toggle voice responses
/clear - Clear conversation history
/stats - View API usage stats
/lang <code> - Change language (en, hi, es, fr, de, it)
/help - Show this help

**Features:**
✅ Multi-API system (GROQ, Gemini, OpenRouter)
✅ Automatic fallback if one API fails
✅ FREE voice synthesis (Sarvam, Edge TTS, Google)
✅ Conversation memory
✅ Multi-language support

**Voice Services:**
1. Sarvam AI (Indian voices - Premium quality)
2. Edge TTS (Microsoft - Very natural)
3. Google TTS (Reliable fallback)

**Supported Languages:**
🇬🇧 English (en)
🇮🇳 Hindi (hi)
🇪🇸 Spanish (es)
🇫🇷 French (fr)
🇩🇪 German (de)
🇮🇹 Italian (it)

**Tips:**
• Voice responses work best in English and Hindi
• Use /clear if you want to start fresh
• Check /stats to see which APIs are working

Made with ❤️ using free AI services!"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle voice"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    session.voice_enabled = not session.voice_enabled
    
    status = "enabled 🔊" if session.voice_enabled else "disabled 🔇"
    await update.message.reply_text(f"Voice responses {status}")


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear history"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    session.clear()
    
    await update.message.reply_text("✅ Conversation cleared! Starting fresh. 🔄")


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show API statistics"""
    api_stats = api_manager.get_stats()
    voice_stats = voice_manager.get_stats()
    
    stats_text = "📊 **API Usage Statistics**\n\n"
    
    stats_text += "**AI Services:**\n"
    for service, data in api_stats.items():
        total = data['success'] + data['failures']
        if total > 0:
            success_rate = (data['success'] / total) * 100
            stats_text += f"• {service.upper()}: ✅ {data['success']} | ❌ {data['failures']} ({success_rate:.1f}%)\n"
    
    stats_text += "\n**Voice Services:**\n"
    for service, data in voice_stats.items():
        total = data['success'] + data['failures']
        if total > 0:
            success_rate = (data['success'] / total) * 100
            stats_text += f"• {service}: ✅ {data['success']} | ❌ {data['failures']} ({success_rate:.1f}%)\n"
    
    stats_text += f"\n**Active Users:** {len(user_sessions)}"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change language"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    
    if context.args:
        lang = context.args[0].lower()
        if lang in ['en', 'hi', 'es', 'fr', 'de', 'it']:
            session.language = lang
            await update.message.reply_text(f"✅ Language changed to: {lang}")
        else:
            await update.message.reply_text("❌ Unsupported language. Use: en, hi, es, fr, de, it")
    else:
        await update.message.reply_text(
            "🌍 **Available Languages:**\n"
            "• en - English\n"
            "• hi - Hindi\n"
            "• es - Spanish\n"
            "• fr - French\n"
            "• de - German\n"
            "• it - Italian\n\n"
            "Usage: /lang <code>"
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if len(user_message) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"⚠️ Message too long! Max {MAX_MESSAGE_LENGTH} characters."
        )
        return
    
    await update.message.chat.send_action("typing")
    
    try:
        session = get_or_create_session(user_id)
        session.add_message("user", user_message)
        
        # Generate response
        response_text = await api_manager.generate_response(
            session.get_messages(),
            max_tokens=1000
        )
        
        session.add_message("assistant", response_text)
        
        # Send voice if enabled
        if session.voice_enabled:
            await update.message.chat.send_action("record_voice")
            
            voice_file = await voice_manager.generate_voice(
                response_text[:500],  # Limit for voice
                session.language
            )
            
            if voice_file:
                try:
                    with open(voice_file, 'rb') as audio:
                        await update.message.reply_voice(
                            voice=audio,
                            caption=response_text[:1000]
                        )
                    os.remove(voice_file)
                except Exception as e:
                    logger.error(f"Voice send failed: {e}")
                    await update.message.reply_text(response_text)
            else:
                await update.message.reply_text(response_text)
        else:
            await update.message.reply_text(response_text)
    
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text(
            "😔 All services are temporarily busy. Please try again in a moment."
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button clicks"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'toggle_voice':
        user_id = query.from_user.id
        session = get_or_create_session(user_id)
        session.voice_enabled = not session.voice_enabled
        status = "enabled 🔊" if session.voice_enabled else "disabled 🔇"
        await query.edit_message_text(f"Voice responses {status}")
    
    elif query.data == 'stats':
        await stats_command(update, context)
    
    elif query.data == 'help':
        await help_command(update, context)
    
    elif query.data == 'language':
        await lang_command(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Error handler"""
    logger.error(f"Update {update} caused error {context.error}")


def main():
    """Start the bot"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("voice", voice_command))
    application.add_handler(CommandHandler("clear", clear_command))
    application.add_handler(CommandHandler("stats", stats_command))
    application.add_handler(CommandHandler("lang", lang_command))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Button handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    logger.info("🚀 Adima Bot started with multi-API fallback!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
