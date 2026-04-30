import logging
import asyncio
from typing import List, Dict, Optional
import aiohttp
from groq import AsyncGroq
import google.generativeai as genai
from openai import AsyncOpenAI

from config import *

logger = logging.getLogger(__name__)


class APIHandler:
    """Handles multiple AI APIs with automatic fallback"""
    
    def __init__(self):
        # GROQ clients
        self.groq_clients = []
        for key in GROQ_KEYS:
            try:
                self.groq_clients.append(AsyncGroq(api_key=key))
            except Exception as e:
                logger.warning(f"GROQ init failed: {e}")
        self.groq_index = 0
        
        # Gemini models
        self.gemini_clients = []
        for key in GEMINI_KEYS:
            try:
                genai.configure(api_key=key)
                self.gemini_clients.append(genai.GenerativeModel('gemini-1.5-flash'))
            except Exception as e:
                logger.warning(f"Gemini init failed: {e}")
        self.gemini_index = 0
        
        # OpenRouter keys
        self.openrouter_keys = OPENROUTER_KEYS
        self.openrouter_index = 0
        
        # OpenAI client
        self.openai_client = None
        if OPENAI_API_KEY:
            try:
                self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
            except Exception as e:
                logger.warning(f"OpenAI init failed: {e}")
        
        # Statistics
        self.stats = {
            'groq': {'success': 0, 'failures': 0},
            'gemini': {'success': 0, 'failures': 0},
            'openrouter': {'success': 0, 'failures': 0},
            'openai': {'success': 0, 'failures': 0},
        }
        
        # GROQ models (updated)
        self.groq_models = [
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
            "gemma2-9b-it",
        ]
        self.groq_model_index = 0
        
        logger.info("APIHandler initialized successfully")
    
    async def generate_response(self, messages: List[Dict], max_tokens: int = 1500) -> str:
        """Generate response with automatic fallback"""
        
        for api_name in API_PRIORITY:
            try:
                if api_name == 'groq' and self.groq_clients:
                    response = await self._try_groq(messages, max_tokens)
                    if response:
                        self.stats['groq']['success'] += 1
                        logger.info("✅ GROQ success")
                        return response
                
                elif api_name == 'gemini' and self.gemini_clients:
                    response = await self._try_gemini(messages)
                    if response:
                        self.stats['gemini']['success'] += 1
                        logger.info("✅ Gemini success")
                        return response
                
                elif api_name == 'openrouter' and self.openrouter_keys:
                    response = await self._try_openrouter(messages, max_tokens)
                    if response:
                        self.stats['openrouter']['success'] += 1
                        logger.info("✅ OpenRouter success")
                        return response
                
                elif api_name == 'openai' and self.openai_client:
                    response = await self._try_openai(messages, max_tokens)
                    if response:
                        self.stats['openai']['success'] += 1
                        logger.info("✅ OpenAI success")
                        return response
                        
            except Exception as e:
                logger.warning(f"❌ {api_name} failed: {e}")
                self.stats[api_name]['failures'] += 1
                continue
        
        raise Exception("All AI services failed")
    
    async def _try_groq(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try GROQ with model rotation"""
        for _ in range(len(self.groq_clients)):
            client = self.groq_clients[self.groq_index]
            
            for _ in range(len(self.groq_models)):
                try:
                    model = self.groq_models[self.groq_model_index]
                    
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0.7,
                    )
                    
                    return response.choices[0].message.content
                    
                except Exception as e:
                    if "decommissioned" in str(e).lower():
                        self.groq_model_index = (self.groq_model_index + 1) % len(self.groq_models)
                        continue
                    raise
            
            self.groq_index = (self.groq_index + 1) % len(self.groq_clients)
        
        return None
    
    async def _try_gemini(self, messages: List[Dict]) -> Optional[str]:
        """Try Gemini with key rotation"""
        for _ in range(len(self.gemini_clients)):
            try:
                model = self.gemini_clients[self.gemini_index]
                prompt = self._convert_messages(messages)
                
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1500,
                        temperature=0.7,
                    )
                )
                
                return response.text
                
            except Exception as e:
                logger.warning(f"Gemini key {self.gemini_index} failed: {e}")
                self.gemini_index = (self.gemini_index + 1) % len(self.gemini_clients)
        
        return None
    
    async def _try_openrouter(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try OpenRouter with free models"""
        free_models = [
            "google/gemini-flash-1.5",
            "meta-llama/llama-3.2-3b-instruct:free",
            "qwen/qwen-2-7b-instruct:free",
        ]
        
        for _ in range(len(self.openrouter_keys)):
            key = self.openrouter_keys[self.openrouter_index]
            
            for model in free_models:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            "https://openrouter.ai/api/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {key}",
                                "Content-Type": "application/json",
                            },
                            json={
                                "model": model,
                                "messages": messages,
                                "max_tokens": max_tokens,
                            },
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                return data['choices'][0]['message']['content']
                                
                except Exception as e:
                    logger.warning(f"OpenRouter {model} failed: {e}")
                    continue
            
            self.openrouter_index = (self.openrouter_index + 1) % len(self.openrouter_keys)
        
        return None
    
    async def _try_openai(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try OpenAI"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI failed: {e}")
            raise
    
    def _convert_messages(self, messages: List[Dict]) -> str:
        """Convert messages to prompt"""
        prompt = ""
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                prompt += f"System: {content}\n\n"
            elif role == 'user':
                prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n\n"
        return prompt.strip()
    
    def get_stats(self) -> Dict:
        """Get statistics"""
        return self.stats
