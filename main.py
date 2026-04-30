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
try:
    api_manager = APIManager()
    voice_manager = VoiceManager()
except Exception as e:
    logger.error(f"Failed to initialize managers: {e}")
    raise

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
You provide clear, concise, and accurate responses. You're empathetic and engaging. 
Keep responses conversational and natural."""
    
    def add_message(self, role: str, content: str):
        """Add message to history"""
        self.conversation_history.append({"role": role, "content": content})
        self.last_activity = datetime.now()
        
        # Keep only recent messages
        if len(self.conversation_history) > MAX_HISTORY_LENGTH * 2:
            self.conversation_history = self.conversation_history[-MAX_HISTORY_LENGTH * 2:]
    
    def get_messages(self) -> List[Dict]:
        """Get messages with system prompt"""
        return [{"role": "system", "content": self.system_prompt}] + self.conversation_history
    
    def is_expired(self) -> bool:
        """Check if session expired"""
        return datetime.now() - self.last_activity > timedelta(seconds=SESSION_TIMEOUT)
    
    def clear(self):
        """Clear conversation history"""
        self.conversation_history = []
        self.last_activity = datetime.now()


def get_or_create_session(user_id: int) -> UserSession:
    """Get or create user session"""
    if user_id not in user_sessions or user_sessions[user_id].is_expired():
        user_sessions[user_id] = UserSession(user_id)
    return user_sessions[user_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user = update.effective_user
    
    keyboard = [
        [
            InlineKeyboardButton("🎤 Voice", callback_data='toggle_voice'),
            InlineKeyboardButton("📊 Stats", callback_data='stats')
        ],
        [
            InlineKeyboardButton("🌍 Language", callback_data='language'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""👋 **Welcome {user.first_name}!**

I'm **Adima**, your AI assistant with multi-service support!

✨ **Features:**
• 🤖 Smart AI (GROQ, Gemini, OpenRouter)
• 🎤 Natural voices (Sarvam, Edge TTS, Google)
• 🌍 Multi-language support
• 📊 Real-time statistics
• 🔄 Automatic fallback

**Commands:**
/start - Show menu
/voice - Toggle voice
/clear - Clear history
/stats - View stats
/help - Get help

💬 **Just send me a message to begin!**"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = """🤖 **Adima Bot Help**

**Commands:**
• /start - Start/restart bot
• /voice - Toggle voice responses
• /clear - Clear chat history
• /stats - API usage statistics
• /lang <code> - Set language
• /help - Show this help

**Languages:**
🇬🇧 en - English
🇮🇳 hi - Hindi
🇪🇸 es - Spanish
🇫🇷 fr - French
🇩🇪 de - German
🇮🇹 it - Italian

**AI Services:**
1️⃣ GROQ (Primary)
2️⃣ Gemini (Backup)
3️⃣ OpenRouter (Backup)
4️⃣ OpenAI (Fallback)

**Voice Services:**
1️⃣ Sarvam AI (Indian)
2️⃣ Edge TTS (Microsoft)
3️⃣ Google TTS (Reliable)

💡 **Tip:** Enable voice for audio responses!"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle voice"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    session.voice_enabled = not session.voice_enabled
    
    emoji = "🔊" if session.voice_enabled else "🔇"
    status = "enabled" if session.voice_enabled else "disabled"
    
    await update.message.reply_text(f"{emoji} Voice responses **{status}**!", parse_mode='Markdown')


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear history"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    session.clear()
    
    await update.message.reply_text("✅ **Chat history cleared!** Starting fresh. 🔄", parse_mode='Markdown')


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show statistics"""
    api_stats = api_manager.get_stats()
    voice_stats = voice_manager.get_stats()
    
    stats_text = "📊 **Service Statistics**\n\n"
    
    stats_text += "**🧠 AI Services:**\n"
    for service, data in api_stats.items():
        total = data['success'] + data['failures']
        if total > 0:
            rate = (data['success'] / total) * 100
            stats_text += f"• {service.upper()}: ✅{data['success']} ❌{data['failures']} ({rate:.0f}%)\n"
    
    stats_text += "\n**🎤 Voice Services:**\n"
    for service, data in voice_stats.items():
        total = data['success'] + data['failures']
        if total > 0:
            rate = (data['success'] / total) * 100
            stats_text += f"• {service}: ✅{data['success']} ❌{data['failures']} ({rate:.0f}%)\n"
    
    stats_text += f"\n👥 **Active Users:** {len(user_sessions)}"
    
    await update.message.reply_text(stats_text, parse_mode='Markdown')


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change language"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    
    if context.args:
        lang = context.args[0].lower()
        supported = ['en', 'hi', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh']
        
        if lang in supported:
            session.language = lang
            await update.message.reply_text(f"✅ Language set to: **{lang}**", parse_mode='Markdown')
        else:
            await update.message.reply_text(
                f"❌ Unsupported language.\n\n**Supported:** {', '.join(supported)}"
            )
    else:
        await update.message.reply_text(
            "🌍 **Language Options:**\n\n"
            "• en - English 🇬🇧\n"
            "• hi - Hindi 🇮🇳\n"
            "• es - Spanish 🇪🇸\n"
            "• fr - French 🇫🇷\n"
            "• de - German 🇩🇪\n"
            "• it - Italian 🇮🇹\n\n"
            "**Usage:** `/lang en`",
            parse_mode='Markdown'
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle user messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Validate message length
    if len(user_message) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"⚠️ Message too long! Maximum {MAX_MESSAGE_LENGTH} characters."
        )
        return
    
    # Show typing
    await update.message.chat.send_action("typing")
    
    try:
        session = get_or_create_session(user_id)
        session.add_message("user", user_message)
        
        # Generate AI response
        response_text = await api_manager.generate_response(
            session.get_messages(),
            max_tokens=1000
        )
        
        session.add_message("assistant", response_text)
        
        # Handle voice if enabled
        if session.voice_enabled:
            await update.message.chat.send_action("record_voice")
            
            voice_file = await voice_manager.generate_voice(
                response_text,
                session.language
            )
            
            if voice_file and os.path.exists(voice_file):
                try:
                    with open(voice_file, 'rb') as audio:
                        await update.message.reply_voice(
                            voice=audio,
                            caption=response_text[:1000] if len(response_text) > 1000 else None
                        )
                    
                    # Clean up
                    os.remove(voice_file)
                    
                except Exception as e:
                    logger.error(f"Failed to send voice: {e}")
                    await update.message.reply_text(response_text)
            else:
                # Fallback to text
                await update.message.reply_text(response_text)
        else:
            # Send text response
            await update.message.reply_text(response_text)
    
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text(
            "😔 Sorry, I'm having trouble right now. Please try:\n"
            "• /clear - Reset conversation\n"
            "• Wait a moment and try again\n"
            "• /stats - Check service status"
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button clicks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    
    if query.data == 'toggle_voice':
        session = get_or_create_session(user_id)
        session.voice_enabled = not session.voice_enabled
        
        emoji = "🔊" if session.voice_enabled else "🔇"
        status = "enabled" if session.voice_enabled else "disabled"
        
        await query.edit_message_text(f"{emoji} Voice responses **{status}**!", parse_mode='Markdown')
    
    elif query.data == 'stats':
        # Create a temporary update for stats command
        await stats_command(update, context)
    
    elif query.data == 'help':
        await help_command(update, context)
    
    elif query.data == 'language':
        await lang_command(update, context)


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    logger.error(f"Update {update} caused error: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ An unexpected error occurred. Please try again."
        )


def main():
    """Start the bot"""
    try:
        print("\n🚀 Starting Adima Bot...\n")
        
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("voice", voice_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("lang", lang_command))
        
        # Add message handler
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # Add callback handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Add error handler
        application.add_error_handler(error_handler)
        
        # Start bot
        print("✅ Bot is running! Press Ctrl+C to stop.\n")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
        
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Bot crashed: {e}")


if __name__ == '__main__':
    main()
