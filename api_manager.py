import logging
import asyncio
from typing import List, Dict, Optional
import aiohttp
from groq import AsyncGroq
import google.generativeai as genai
from openai import AsyncOpenAI

from config import (
    GROQ_KEYS, GEMINI_KEYS, OPENROUTER_KEYS, 
    OPENAI_API_KEY, API_PRIORITY
)

logger = logging.getLogger(__name__)


class APIManager:
    """Manages multiple AI APIs with automatic fallback"""
    
    def __init__(self):
        # Initialize GROQ clients
        self.groq_clients = []
        for key in GROQ_KEYS:
            try:
                self.groq_clients.append(AsyncGroq(api_key=key))
            except Exception as e:
                logger.warning(f"Failed to initialize GROQ client: {e}")
        self.groq_index = 0
        
        # Initialize Gemini models
        self.gemini_models = []
        for key in GEMINI_KEYS:
            try:
                genai.configure(api_key=key)
                self.gemini_models.append(genai.GenerativeModel('gemini-pro'))
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini model: {e}")
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
                logger.warning(f"Failed to initialize OpenAI client: {e}")
        
        # Statistics
        self.api_stats = {
            'groq': {'success': 0, 'failures': 0},
            'gemini': {'success': 0, 'failures': 0},
            'openrouter': {'success': 0, 'failures': 0},
            'openai': {'success': 0, 'failures': 0},
        }
    
    async def generate_response(self, messages: List[Dict], max_tokens: int = 1000) -> str:
        """Try APIs in priority order until one succeeds"""
        
        for api_name in API_PRIORITY:
            try:
                if api_name == 'groq' and self.groq_clients:
                    response = await self._try_groq(messages, max_tokens)
                    if response:
                        self.api_stats['groq']['success'] += 1
                        logger.info(f"✅ Response from GROQ")
                        return response
                
                elif api_name == 'gemini' and self.gemini_models:
                    response = await self._try_gemini(messages)
                    if response:
                        self.api_stats['gemini']['success'] += 1
                        logger.info(f"✅ Response from Gemini")
                        return response
                
                elif api_name == 'openrouter' and self.openrouter_keys:
                    response = await self._try_openrouter(messages, max_tokens)
                    if response:
                        self.api_stats['openrouter']['success'] += 1
                        logger.info(f"✅ Response from OpenRouter")
                        return response
                
                elif api_name == 'openai' and self.openai_client:
                    response = await self._try_openai(messages, max_tokens)
                    if response:
                        self.api_stats['openai']['success'] += 1
                        logger.info(f"✅ Response from OpenAI")
                        return response
            
            except Exception as e:
                logger.warning(f"❌ {api_name} failed: {e}")
                self.api_stats[api_name]['failures'] += 1
                continue
        
        raise Exception("❌ All AI services failed. Please try again later.")
    
    async def _try_groq(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try GROQ API with key rotation"""
        for attempt in range(len(self.groq_clients)):
            try:
                client = self.groq_clients[self.groq_index]
                
                response = await client.chat.completions.create(
                    model="llama-3.1-70b-versatile",  # Best free model
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                
                return response.choices[0].message.content
            
            except Exception as e:
                logger.warning(f"GROQ key {self.groq_index} failed: {e}")
                self.groq_index = (self.groq_index + 1) % len(self.groq_clients)
                if attempt == len(self.groq_clients) - 1:
                    raise
        
        return None
    
    async def _try_gemini(self, messages: List[Dict]) -> Optional[str]:
        """Try Gemini API with key rotation"""
        for attempt in range(len(self.gemini_models)):
            try:
                model = self.gemini_models[self.gemini_index]
                
                # Convert messages to Gemini format
                prompt = self._messages_to_prompt(messages)
                
                # Use asyncio.to_thread for synchronous Gemini API
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt
                )
                
                return response.text
            
            except Exception as e:
                logger.warning(f"Gemini key {self.gemini_index} failed: {e}")
                self.gemini_index = (self.gemini_index + 1) % len(self.gemini_models)
                if attempt == len(self.gemini_models) - 1:
                    raise
        
        return None
    
    async def _try_openrouter(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try OpenRouter API with key rotation"""
        for attempt in range(len(self.openrouter_keys)):
            try:
                key = self.openrouter_keys[self.openrouter_index]
                
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {key}",
                            "Content-Type": "application/json",
                            "HTTP-Referer": "https://github.com/asnzodiac/adima_bot",
                            "X-Title": "Adima Bot"
                        },
                        json={
                            "model": "meta-llama/llama-3.1-8b-instruct:free",
                            "messages": messages,
                            "max_tokens": max_tokens,
                        },
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data['choices'][0]['message']['content']
                        else:
                            error_text = await resp.text()
                            raise Exception(f"HTTP {resp.status}: {error_text}")
            
            except Exception as e:
                logger.warning(f"OpenRouter key {self.openrouter_index} failed: {e}")
                self.openrouter_index = (self.openrouter_index + 1) % len(self.openrouter_keys)
                if attempt == len(self.openrouter_keys) - 1:
                    raise
        
        return None
    
    async def _try_openai(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try OpenAI API (paid fallback)"""
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
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert messages to single prompt for Gemini"""
        prompt = ""
        for msg in messages:
            role = msg['role']
            content = msg['content']
            if role == 'system':
                prompt += f"Instructions: {content}\n\n"
            elif role == 'user':
                prompt += f"User: {content}\n\n"
            elif role == 'assistant':
                prompt += f"Assistant: {content}\n\n"
        return prompt.strip()
    
    def get_stats(self) -> Dict:
        """Get API usage statistics"""
        return self.api_stats
