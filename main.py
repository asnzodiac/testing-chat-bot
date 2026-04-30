import logging
import asyncio
import os
from datetime import datetime, timedelta
from typing import Dict, List

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from config import *
from api_handler import APIHandler
from voice_handler import VoiceHandler

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize handlers
api_handler = APIHandler()
voice_handler = VoiceHandler()

# User sessions storage
user_sessions: Dict[int, 'UserSession'] = {}


class UserSession:
    """Manages individual user conversation sessions"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.conversation_history: List[Dict] = []
        self.last_activity = datetime.now()
        self.voice_enabled = False
        self.language = 'en'
        self.system_prompt = """You are Adima, a helpful, friendly, and intelligent AI assistant. 
You provide clear, concise, and accurate responses. You're empathetic and engaging.
Keep responses natural and conversational."""
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
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
        logger.info(f"Created new session for user {user_id}")
    return user_sessions[user_id]


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    keyboard = [
        [
            InlineKeyboardButton("🎤 Voice", callback_data='voice'),
            InlineKeyboardButton("📊 Stats", callback_data='stats')
        ],
        [
            InlineKeyboardButton("🗑️ Clear", callback_data='clear'),
            InlineKeyboardButton("❓ Help", callback_data='help')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = f"""👋 **Welcome {user.first_name}!**

I'm **Adima**, your advanced AI assistant!

✨ **Features:**
• 🤖 Multi-AI Support (GROQ, Gemini, OpenRouter)
• 🎤 Natural Voice (Free TTS)
• 🌍 Multi-language
• 🔄 Auto-fallback
• 💾 Context memory

**Quick Commands:**
/start - Show this menu
/help - Get help
/voice - Toggle voice
/clear - Clear history
/stats - View statistics

💬 **Send me a message to start chatting!**"""
    
    await update.message.reply_text(
        welcome_text,
        parse_mode='Markdown',
        reply_markup=reply_markup
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """🤖 **Adima Bot - Help Guide**

**Available Commands:**
• `/start` - Show welcome menu
• `/help` - Display this help
• `/voice` - Toggle voice responses
• `/clear` - Clear chat history
• `/stats` - View API statistics
• `/lang <code>` - Change language

**Supported Languages:**
🇬🇧 en - English
🇮🇳 hi - Hindi  
🇪🇸 es - Spanish
🇫🇷 fr - French
🇩🇪 de - German
🇮🇹 it - Italian

**AI Services (Auto-fallback):**
1️⃣ GROQ - Fast & Free
2️⃣ Gemini - Google AI
3️⃣ OpenRouter - Multi-model
4️⃣ OpenAI - Premium (if available)

**Voice Services:**
🎙️ Sarvam AI - Indian voices
🎙️ Edge TTS - Microsoft (High quality)
🎙️ Google TTS - Reliable fallback

**How to use:**
Just send me any message and I'll respond!
Enable voice with /voice for audio replies.

Made with ❤️ using free AI services"""
    
    await update.message.reply_text(help_text, parse_mode='Markdown')


async def voice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle voice responses"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    session.voice_enabled = not session.voice_enabled
    
    emoji = "🔊" if session.voice_enabled else "🔇"
    status = "ON" if session.voice_enabled else "OFF"
    
    await update.message.reply_text(
        f"{emoji} **Voice Mode: {status}**\n\n"
        f"Language: {session.language}\n"
        f"You'll receive audio responses now!" if session.voice_enabled else "Text mode enabled.",
        parse_mode='Markdown'
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear conversation history"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    
    msg_count = len(session.conversation_history)
    session.clear()
    
    await update.message.reply_text(
        f"✅ **Chat Cleared!**\n\n"
        f"Removed {msg_count} messages.\n"
        f"Starting fresh conversation! 🔄",
        parse_mode='Markdown'
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show API usage statistics"""
    try:
        api_stats = api_handler.get_stats()
        voice_stats = voice_handler.get_stats()
        
        stats_text = "📊 **Service Statistics**\n\n"
        
        # AI Services
        stats_text += "**🧠 AI Services:**\n"
        total_ai_calls = 0
        for service, data in api_stats.items():
            total = data['success'] + data['failures']
            total_ai_calls += total
            if total > 0:
                rate = (data['success'] / total) * 100
                stats_text += f"• **{service.upper()}**: ✅ {data['success']} | ❌ {data['failures']} ({rate:.1f}%)\n"
        
        # Voice Services
        stats_text += "\n**🎤 Voice Services:**\n"
        total_voice_calls = 0
        for service, data in voice_stats.items():
            total = data['success'] + data['failures']
            total_voice_calls += total
            if total > 0:
                rate = (data['success'] / total) * 100
                stats_text += f"• **{service}**: ✅ {data['success']} | ❌ {data['failures']} ({rate:.1f}%)\n"
        
        # Overall Stats
        stats_text += f"\n**📈 Overall:**\n"
        stats_text += f"• Active Users: {len(user_sessions)}\n"
        stats_text += f"• Total AI Calls: {total_ai_calls}\n"
        stats_text += f"• Total Voice: {total_voice_calls}\n"
        
        await update.message.reply_text(stats_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Stats error: {e}")
        await update.message.reply_text("Error fetching statistics. Try again later.")


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change language"""
    user_id = update.effective_user.id
    session = get_or_create_session(user_id)
    
    if context.args:
        lang = context.args[0].lower()
        supported = ['en', 'hi', 'es', 'fr', 'de', 'it', 'ja', 'ko', 'zh']
        
        if lang in supported:
            session.language = lang
            await update.message.reply_text(
                f"✅ Language changed to: **{lang.upper()}**",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"❌ Unsupported language!\n\n"
                f"**Supported:** {', '.join(supported)}",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            "🌍 **Language Settings**\n\n"
            "**Available:**\n"
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
    """Handle incoming text messages"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Validate message
    if len(user_message) > MAX_MESSAGE_LENGTH:
        await update.message.reply_text(
            f"⚠️ Message too long!\n"
            f"Maximum: {MAX_MESSAGE_LENGTH} characters"
        )
        return
    
    # Show typing
    await update.message.chat.send_action("typing")
    
    try:
        session = get_or_create_session(user_id)
        session.add_message("user", user_message)
        
        # Generate AI response
        logger.info(f"Generating response for user {user_id}")
        response_text = await api_handler.generate_response(session.get_messages())
        
        session.add_message("assistant", response_text)
        
        # Handle voice if enabled
        if session.voice_enabled:
            await update.message.chat.send_action("record_voice")
            
            try:
                voice_file = await voice_handler.generate_voice(
                    response_text[:500],  # Limit length
                    session.language
                )
                
                if voice_file and os.path.exists(voice_file):
                    with open(voice_file, 'rb') as audio:
                        await update.message.reply_voice(
                            voice=audio,
                            caption=response_text[:1000] if len(response_text) > 500 else None
                        )
                    
                    # Cleanup
                    try:
                        os.remove(voice_file)
                    except:
                        pass
                else:
                    # Fallback to text
                    await update.message.reply_text(response_text)
                    
            except Exception as e:
                logger.error(f"Voice generation failed: {e}")
                await update.message.reply_text(response_text)
        else:
            # Send text response
            await update.message.reply_text(response_text)
            
    except Exception as e:
        logger.error(f"Message handling error: {e}")
        await update.message.reply_text(
            "😔 Sorry, I'm having trouble.\n\n"
            "**Try:**\n"
            "• /clear - Reset conversation\n"
            "• Wait a moment and retry\n"
            "• /stats - Check service status"
        )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    
    try:
        if data == 'voice':
            session = get_or_create_session(user_id)
            session.voice_enabled = not session.voice_enabled
            
            emoji = "🔊" if session.voice_enabled else "🔇"
            status = "ON" if session.voice_enabled else "OFF"
            
            await query.message.reply_text(
                f"{emoji} **Voice Mode: {status}**",
                parse_mode='Markdown'
            )
        
        elif data == 'stats':
            # Create temporary update for stats
            await stats_command(update, context)
        
        elif data == 'clear':
            session = get_or_create_session(user_id)
            session.clear()
            await query.message.reply_text("✅ **Chat cleared!**", parse_mode='Markdown')
        
        elif data == 'help':
            await help_command(update, context)
            
    except Exception as e:
        logger.error(f"Callback error: {e}")
        await query.message.reply_text("Error processing request.")


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Global error handler"""
    logger.error(f"Update {update} caused error: {context.error}", exc_info=context.error)


def main():
    """Start the bot"""
    try:
        print("\n" + "="*60)
        print("🚀 Starting Adima Bot...".center(60))
        print("="*60 + "\n")
        
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Add handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("voice", voice_command))
        application.add_handler(CommandHandler("clear", clear_command))
        application.add_handler(CommandHandler("stats", stats_command))
        application.add_handler(CommandHandler("lang", lang_command))
        
        # Message handler
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
        )
        
        # Callback handler
        application.add_handler(CallbackQueryHandler(button_callback))
        
        # Error handler
        application.add_error_handler(error_handler)
        
        # Start bot
        print("✅ Bot is running! Press Ctrl+C to stop.\n")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except KeyboardInterrupt:
        print("\n\n👋 Bot stopped by user.")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n❌ Bot crashed: {e}")


if __name__ == '__main__':
    main()
