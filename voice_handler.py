import logging
import os
import uuid
import asyncio
import aiohttp
from typing import Optional
import edge_tts
from gtts import gTTS

from config import *

logger = logging.getLogger(__name__)


class VoiceHandler:
    """Handles multiple TTS services with fallback"""
    
    def __init__(self):
        self.sarvam_key = SARVAM_API_KEY
        self.stats = {
            'sarvam': {'success': 0, 'failures': 0},
            'edge-tts': {'success': 0, 'failures': 0},
            'gtts': {'success': 0, 'failures': 0},
        }
        logger.info("VoiceHandler initialized")
    
    async def generate_voice(self, text: str, language: str = 'en') -> Optional[str]:
        """Generate voice with fallback"""
        
        # Limit text
        if len(text) > 500:
            text = text[:497] + "..."
        
        for service in VOICE_PRIORITY:
            try:
                if service == 'sarvam' and self.sarvam_key:
                    filepath = await self._try_sarvam(text, language)
                    if filepath:
                        self.stats['sarvam']['success'] += 1
                        return filepath
                
                elif service == 'edge-tts':
                    filepath = await self._try_edge_tts(text, language)
                    if filepath:
                        self.stats['edge-tts']['success'] += 1
                        return filepath
                
                elif service == 'gtts':
                    filepath = await self._try_gtts(text, language)
                    if filepath:
                        self.stats['gtts']['success'] += 1
                        return filepath
                        
            except Exception as e:
                logger.warning(f"{service} failed: {e}")
                self.stats[service]['failures'] += 1
                continue
        
        return None
    
    async def _try_sarvam(self, text: str, language: str) -> Optional[str]:
        """Try Sarvam AI"""
        try:
            filename = f"{AUDIO_DIR}/voice_{uuid.uuid4()}.mp3"
            
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
                        "speaker": "meera",
                        "model": "bulbul:v1"
                    },
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        
                        import base64
                        audio_bytes = base64.b64decode(data['audios'][0])
                        with open(filename, 'wb') as f:
                            f.write(audio_bytes)
                        
                        return filename
        except Exception as e:
            logger.error(f"Sarvam failed: {e}")
            return None
    
    async def _try_edge_tts(self, text: str, language: str) -> Optional[str]:
        """Try Edge TTS"""
        try:
            filename = f"{AUDIO_DIR}/voice_{uuid.uuid4()}.mp3"
            
            voice_map = {
                'en': 'en-US-AriaNeural',
                'hi': 'hi-IN-SwaraNeural',
                'es': 'es-ES-ElviraNeural',
                'fr': 'fr-FR-DeniseNeural',
                'de': 'de-DE-KatjaNeural',
                'it': 'it-IT-ElsaNeural',
            }
            
            voice = voice_map.get(language, 'en-US-AriaNeural')
            
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(filename)
            
            return filename
            
        except Exception as e:
            logger.error(f"Edge TTS failed: {e}")
            return None
    
    async def _try_gtts(self, text: str, language: str) -> Optional[str]:
        """Try Google TTS"""
        try:
            filename = f"{AUDIO_DIR}/voice_{uuid.uuid4()}.mp3"
            
            await asyncio.to_thread(self._gtts_sync, text, language, filename)
            
            return filename
            
        except Exception as e:
            logger.error(f"GTTS failed: {e}")
            return None
    
    def _gtts_sync(self, text: str, language: str, filename: str):
        """Sync GTTS"""
        tts = gTTS(text=text, lang=language, slow=False)
        tts.save(filename)
    
    def get_stats(self) -> dict:
        """Get statistics"""
        return self.stats
