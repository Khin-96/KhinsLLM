# grok_llm.py
import os
import logging
from typing import List, Optional, Any
from livekit.agents import llm

try:
    from xai_sdk import AsyncClient
    HAS_XAI = True
except ImportError as e:
    logging.error(f"xai-sdk import error: {e}")
    HAS_XAI = False

class GrokModel(llm.LLM):
    def __init__(
        self,
        model: str = "grok-beta",
        temperature: float = 0.8,
        max_tokens: int = 1000,
    ):
        if not HAS_XAI:
            raise ImportError("xai-sdk not installed")
            
        self.model_name = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        
        # Initialize Grok client
        api_key = os.getenv("XAI_API_KEY")
        if not api_key:
            raise ValueError("XAI_API_KEY environment variable is required")
        
        self.client = AsyncClient(api_key=api_key)

    async def chat(
        self,
        *,
        messages: List[llm.ChatMessage],
        tools: Optional[List[Any]] = None,  # Use Any instead of specific Tool class
        max_tokens: Optional[int] = None,
    ) -> llm.LLMStream:
        """Return an LLMStream instead of ChatContext"""
        from livekit.agents.llm import ChatChunk, ChatContent
        
        try:
            # Convert LiveKit messages to xAI format
            conversation = []
            for msg in messages:
                if msg.role == llm.ChatRole.USER:
                    role = "user"
                elif msg.role == llm.ChatRole.ASSISTANT:
                    role = "assistant"
                else:
                    role = "system"
                
                conversation.append({
                    "role": role,
                    "content": msg.content
                })

            # Call Grok API
            response = await self.client.chat.create(
                model=self.model_name,
                messages=conversation,
                temperature=self.temperature,
                max_tokens=max_tokens or self.max_tokens,
            )

            # Extract response content
            content = self._extract_content(response)
            
            # Create a stream with a single chunk containing the complete response
            async def _generate_chunks():
                yield ChatChunk(
                    content=ChatContent(text=content),
                    tool_calls=[]
                )
            
            return llm.LLMStream(_generate_chunks())
            
        except Exception as e:
            logging.error(f"Grok API error: {e}")
            # Return an error response stream
            async def _error_chunks():
                yield ChatChunk(
                    content=ChatContent(text="I encountered an error processing your request."),
                    tool_calls=[]
                )
            
            return llm.LLMStream(_error_chunks())

    def _extract_content(self, response):
        """Extract content from xai-sdk response"""
        try:
            # Try different response structures
            if hasattr(response, 'choices') and len(response.choices) > 0:
                return response.choices[0].message.content
            elif hasattr(response, 'text'):
                return response.text
            elif hasattr(response, 'content'):
                return response.content
            else:
                return str(response)
                
        except Exception as e:
            logging.error(f"Error extracting content: {e}")
            return "I encountered an error processing the response."