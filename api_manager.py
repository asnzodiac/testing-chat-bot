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
                # Updated to current model
                self.gemini_models.append(genai.GenerativeModel('gemini-1.5-flash'))
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
        
        # Available GROQ models (current as of 2024)
        self.groq_models = [
            "llama-3.3-70b-versatile",      # Latest Llama 3.3 (Best)
            "llama-3.1-8b-instant",         # Fast Llama 3.1
            "mixtral-8x7b-32768",           # Mixtral (Good fallback)
            "gemma2-9b-it",                 # Gemma 2
        ]
        self.groq_model_index = 0
    
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
        """Try GROQ API with key rotation and model fallback"""
        
        for key_attempt in range(len(self.groq_clients)):
            client = self.groq_clients[self.groq_index]
            
            # Try different models
            for model_attempt in range(len(self.groq_models)):
                try:
                    model = self.groq_models[self.groq_model_index]
                    
                    logger.info(f"Trying GROQ with model: {model}")
                    
                    response = await client.chat.completions.create(
                        model=model,
                        messages=messages,
                        max_tokens=max_tokens,
                        temperature=0.7,
                    )
                    
                    return response.choices[0].message.content
                
                except Exception as e:
                    logger.warning(f"GROQ model {model} failed: {e}")
                    # Try next model
                    self.groq_model_index = (self.groq_model_index + 1) % len(self.groq_models)
            
            # Try next API key
            self.groq_index = (self.groq_index + 1) % len(self.groq_clients)
        
        return None
    
    async def _try_gemini(self, messages: List[Dict]) -> Optional[str]:
        """Try Gemini API with key rotation"""
        for attempt in range(len(self.gemini_models)):
            try:
                model = self.gemini_models[self.gemini_index]
                
                # Convert messages to Gemini format
                prompt = self._messages_to_prompt(messages)
                
                logger.info(f"Trying Gemini Flash 1.5")
                
                # Use asyncio.to_thread for synchronous Gemini API
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        max_output_tokens=1000,
                        temperature=0.7,
                    )
                )
                
                return response.text
            
            except Exception as e:
                logger.warning(f"Gemini key {self.gemini_index} failed: {e}")
                self.gemini_index = (self.gemini_index + 1) % len(self.gemini_models)
        
        return None
    
    async def _try_openrouter(self, messages: List[Dict], max_tokens: int) -> Optional[str]:
        """Try OpenRouter API with multiple free models"""
        
        # Updated free models available on OpenRouter
        free_models = [
            "google/gemini-flash-1.5",              # Google's free model
            "meta-llama/llama-3.2-3b-instruct:free", # Llama 3.2 free
            "qwen/qwen-2-7b-instruct:free",          # Qwen 2 free
            "microsoft/phi-3-mini-128k-instruct:free", # Phi-3 free
        ]
        
        for attempt in range(len(self.openrouter_keys)):
            key = self.openrouter_keys[self.openrouter_index]
            
            # Try each free model
            for model in free_models:
                try:
                    logger.info(f"Trying OpenRouter with model: {model}")
                    
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
                                "model": model,
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
                                logger.warning(f"OpenRouter {model} failed: {error_text}")
                
                except Exception as e:
                    logger.warning(f"OpenRouter {model} error: {e}")
                    continue
            
            # Try next API key
            self.openrouter_index = (self.openrouter_index + 1) % len(self.openrouter_keys)
        
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
