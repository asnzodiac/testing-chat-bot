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
        self.groq_clients = [AsyncGroq(api_key=key) for key in GROQ_KEYS]
        self.groq_index = 0
        
        self.gemini_models = []
        for key in GEMINI_KEYS:
            genai.configure(api_key=key)
            self.gemini_models.append(genai.GenerativeModel('gemini-pro'))
        self.gemini_index = 0
        
        self.openrouter_keys = OPENROUTER_KEYS
        self.openrouter_index = 0
        
        self.openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
        
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
                        return response
                
                elif api_name == 'gemini' and self.gemini_models:
                    response = await self._try_gemini(messages)
                    if response:
                        self.api_stats['gemini']['success'] += 1
                        return response
                
                elif api_name == 'openrouter' and self.openrouter_keys:
                    response = await self._try_openrouter(messages, max_tokens)
                    if response:
                        self.api_stats['openrouter']['success'] += 1
                        return response
                
                elif api_name == 'openai' and self.openai_client:
                    response = await self._try_openai(messages, max_tokens)
                    if response:
                        self.api_stats['openai']['success'] += 1
                        return response
            
            except Exception as e:
                logger.warning(f"{api_name} failed: {e}")
                self.api_stats[api_name]['failures'] += 1
                continue
        
        raise Exception("All APIs failed")
    
    async def _try_groq(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try GROQ API with key rotation"""
        for attempt in range(len(self.groq_clients)):
            try:
                client = self.groq_clients[self.groq_index]
                
                response = await client.chat.completions.create(
                    model="mixtral-8x7b-32768",  # Fast and free
                    messages=messages,
                    max_tokens=max_tokens,
                    temperature=0.7,
                )
                
                return response.choices[0].message.content
            
            except Exception as e:
                logger.warning(f"GROQ key {self.groq_index} failed: {e}")
                self.groq_index = (self.groq_index + 1) % len(self.groq_clients)
        
        return None
    
    async def _try_gemini(self, messages: List[Dict]) -> Optional[str]:
        """Try Gemini API with key rotation"""
        for attempt in range(len(self.gemini_models)):
            try:
                model = self.gemini_models[self.gemini_index]
                
                # Convert messages to Gemini format
                prompt = self._messages_to_prompt(messages)
                
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt
                )
                
                return response.text
            
            except Exception as e:
                logger.warning(f"Gemini key {self.gemini_index} failed: {e}")
                self.gemini_index = (self.gemini_index + 1) % len(self.gemini_models)
        
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
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "meta-llama/llama-3.1-8b-instruct:free",  # Free model
                            "messages": messages,
                            "max_tokens": max_tokens,
                        }
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            return data['choices'][0]['message']['content']
            
            except Exception as e:
                logger.warning(f"OpenRouter key {self.openrouter_index} failed: {e}")
                self.openrouter_index = (self.openrouter_index + 1) % len(self.openrouter_keys)
        
        return None
    
    async def _try_openai(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try OpenAI API (paid fallback)"""
        try:
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",  # Cheaper than GPT-4
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.7,
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            logger.error(f"OpenAI failed: {e}")
            return None
    
    def _messages_to_prompt(self, messages: List[Dict]) -> str:
        """Convert messages to single prompt for Gemini"""
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
        return prompt
    
    def get_stats(self) -> Dict:
        """Get API usage statistics"""
        return self.api_stats
