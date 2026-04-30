import logging
import os
import uuid
import asyncio
import aiohttp
from typing import Optional
import edge_tts
from gtts import gTTS

from config import SARVAM_API_KEY, AUDIO_DIR, VOICE_PRIORITY

logger = logging.getLogger(__name__)


class VoiceManager:
    """Manages multiple free TTS services with fallback"""
    
    def __init__(self):
        self.sarvam_key = SARVAM_API_KEY
        self.voice_stats = {
            'sarvam': {'success': 0, 'failures': 0},
            'edge-tts': {'success': 0, 'failures': 0},
            'gtts': {'success': 0, 'failures': 0},
        }
    
    async def generate_voice(self, text: str, language: str = 'en') -> Optional[str]:
        """Generate voice using available services"""
        
        for service in VOICE_PRIORITY:
            try:
                if service == 'sarvam' and self.sarvam_key and language in ['en', 'hi']:
                    filepath = await self._try_sarvam(text, language)
                    if filepath:
                        self.voice_stats['sarvam']['success'] += 1
                        return filepath
                
                elif service == 'edge-tts':
                    filepath = await self._try_edge_tts(text, language)
                    if filepath:
                        self.voice_stats['edge-tts']['success'] += 1
                        return filepath
                
                elif service == 'gtts':
                    filepath = await self._try_gtts(text, language)
                    if filepath:
                        self.voice_stats['gtts']['success'] += 1
                        return filepath
            
            except Exception as e:
                logger.warning(f"{service} failed: {e}")
                self.voice_stats[service]['failures'] += 1
                continue
        
        return None
    
    async def _try_sarvam(self, text: str, language: str) -> Optional[str]:
        """Try Sarvam AI (Indian voices, very natural)"""
        try:
            filename = f"{AUDIO_DIR}/voice_{uuid.uuid4()}.mp3"
            
            # Map language codes
            lang_map = {'en': 'en-IN', 'hi': 'hi-IN'}
            target_lang = lang_map.get(language, 'en-IN')
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "https://api.sarvam.ai/text-to-speech",
                    headers={
                        "Authorization": f"Bearer {self.sarvam_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "inputs": [text],
                        "target_language_code": target_lang,
                        "speaker": "meera",  # Female voice, also: "arvind" (male)
                        "pitch": 0,
                        "pace": 1.0,
                        "loudness": 1.5,
                        "speech_sample_rate": 22050,
                        "enable_preprocessing": True,
                        "model": "bulbul:v1"
                    }
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        audio_base64 = data['audios'][0]
                        
                        # Decode and save
                        import base64
                        audio_bytes = base64.b64decode(audio_base64)
                        with open(filename, 'wb') as f:
                            f.write(audio_bytes)
                        
                        return filename
            
        except Exception as e:
            logger.error(f"Sarvam TTS failed: {e}")
            return None
    
    async def _try_edge_tts(self, text: str, language: str) -> Optional[str]:
        """Try Edge TTS (Microsoft, very high quality, FREE!)"""
        try:
            filename = f"{AUDIO_DIR}/voice_{uuid.uuid4()}.mp3"
            
            # Voice selection based on language
            voice_map = {
                'en': 'en-US-AriaNeural',      # Female, very natural
                'hi': 'hi-IN-SwaraNeural',     # Hindi female
                'es': 'es-ES-ElviraNeural',    # Spanish
                'fr': 'fr-FR-DeniseNeural',    # French
                'de': 'de-DE-KatjaNeural',     # German
                'it': 'it-IT-ElsaNeural',      # Italian
            }
            
            voice = voice_map.get(language, 'en-US-AriaNeural')
            
            # Generate audio
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
            
            return filename
        
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")
            return None
    
    async def _try_gtts(self, text: str, language: str) -> Optional[str]:
        """Try Google TTS (Basic but reliable)"""
        try:
            filename = f"{AUDIO_DIR}/voice_{uuid.uuid4()}.mp3"
            
            # Run in thread to avoid blocking
            await asyncio.to_thread(self._gtts_sync, text, language, filename)
            
            return filename
        
        except Exception as e:
            logger.error(f"GTTS failed: {e}")
            return None
    
    def _gtts_sync(self, text: str, language: str, filename: str):
        """Synchronous GTTS generation"""
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(filename)
    
    def get_stats(self) -> dict:
        """Get voice service statistics"""
        return self.voice_stats
