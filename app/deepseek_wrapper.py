import time
import uuid
import os
import json
import requests
from typing import Dict, Any, Generator, List

class DeepSeekAPI:
    """Simplified DeepSeekAPI for Vercel deployment that uses pre-saved cookies"""
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or os.environ.get("DEEPSEEK_AUTH_TOKEN", "")
        # Load cookies from environment variable if available
        cookies_json = os.environ.get("DEEPSEEK_COOKIES", "{}")
        try:
            self.cookies_data = json.loads(cookies_json)
        except:
            self.cookies_data = {"cookies": {}, "user_agent": ""}
    
    def create_chat_session(self) -> str:
        return str(uuid.uuid4())
    
    def chat_completion(self, session_id: str, message: str, thinking_enabled: bool = False) -> Generator[Dict[str, Any], None, None]:
        # In a real implementation, this would call the DeepSeek API
        # For this simplified version, we'll just return a basic response
        yield {"type": "text", "content": f"This is a simulated response from DeepSeek. Your message was: {message}"}

class DeepSeekWrapper:
    def __init__(self, api_key: str = ""):
        self.api = DeepSeekAPI(api_key)
        self.sessions = {}

    def create_chat_session(self) -> str:
        """Create a new chat session using the DeepSeek API"""
        return self.api.create_chat_session()

    def get_or_create_session(self, session_id: str = None) -> str:
        if session_id and session_id in self.sessions:
            return session_id

        new_session = self.api.create_chat_session()
        if session_id:
            self.sessions[session_id] = new_session
            return session_id
        return new_session

    def generate_response(self, messages: List[Dict[str, str]], model: str, stream: bool = False):
        session_id = self.get_or_create_session()

        # Build a combined message from all the messages in the conversation
        combined_message = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")

            if role == "system":
                combined_message += f"System: {content}\n\n"
            elif role == "user":
                combined_message += f"User: {content}\n\n"
            elif role == "assistant":
                combined_message += f"Assistant: {content}\n\n"

        # If there's no combined message (should not happen), use the last message
        if not combined_message:
            combined_message = messages[-1]["content"]

        # Determine thinking_enabled based on model
        thinking_enabled = model == "deepseek-reasoner"

        response_chunks = self.api.chat_completion(
            session_id,
            combined_message.strip(),
            thinking_enabled=thinking_enabled
        )

        return self._stream_response(response_chunks) if stream else self._complete_response(response_chunks)

    def _stream_response(self, chunks):
        for chunk in chunks:
            if chunk['type'] == 'text':
                yield {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "deepseek-chat",
                    "choices": [{
                        "delta": {"content": chunk['content']},
                        "finish_reason": None,
                        "index": 0
                    }]
                }

    def _complete_response(self, chunks):
        full_response = "".join(chunk['content'] for chunk in chunks if chunk['type'] == 'text')
        return {
            "id": f"chatcmpl-{uuid.uuid4()}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": "deepseek-chat",
            "choices": [{
                "message": {
                    "role": "assistant",
                    "content": full_response
                },
                "finish_reason": "stop",
                "index": 0
            }]
        }