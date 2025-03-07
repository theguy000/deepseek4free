import time
import uuid
import requests
from typing import Dict, Any, Generator, List
import json

class DeepSeekAPI:
    BASE_URL = "https://chat.deepseek.com/api/v0"

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.session = requests.Session()
        self.session.headers.update({
            'accept': '*/*',
            'accept-language': 'en,fr-FR;q=0.9,fr;q=0.8,es-ES;q=0.7,es;q=0.6,en-US;q=0.5,am;q=0.4,de;q=0.3',
            'authorization': f'Bearer {auth_token}',
            'content-type': 'application/json',
            'origin': 'https://chat.deepseek.com',
            'referer': 'https://chat.deepseek.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'x-app-version': '20241129.1',
            'x-client-locale': 'en_US',
        })

    def create_chat_session(self) -> str:
        """Creates a new chat session"""
        response = self.session.post(
            f"{self.BASE_URL}/chat_session/create",
            json={'character_id': None}
        )
        if response.status_code == 200:
            return response.json()['data']['biz_data']['id']
        raise Exception(f"Failed to create session: {response.text}")

    def chat_completion(self, session_id: str, prompt: str) -> Generator[Dict[str, Any], None, None]:
        """Send a message and get streaming response"""
        response = self.session.post(
            f"{self.BASE_URL}/chat/completion",
            json={
                'chat_session_id': session_id,
                'prompt': prompt,
                'ref_file_ids': [],
                'thinking_enabled': False,
                'search_enabled': False,
            },
            stream=True
        )

        for line in response.iter_lines():
            if line:
                try:
                    data = json.loads(line.decode('utf-8').replace('data: ', ''))
                    if 'choices' in data and data['choices']:
                        choice = data['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            yield {
                                "id": data.get("id", f"chatcmpl-{uuid.uuid4()}"),
                                "object": "chat.completion.chunk",
                                "created": data.get("created", int(time.time())),
                                "model": "deepseek-chat",
                                "choices": [{
                                    "delta": {"content": choice['delta']['content']},
                                    "finish_reason": choice.get('finish_reason'),
                                    "index": 0
                                }]
                            }
                except Exception as e:
                    print(f"Error parsing chunk: {e}")
                    continue

class DeepSeekWrapper:
    def __init__(self, api_key: str):
        self.api = DeepSeekAPI(api_key)
        self.sessions = {}

    def generate_response(self, messages: List[Dict[str, str]], model: str, stream: bool = False) -> Generator[Dict[str, Any], None, None] | Dict[str, Any]:
        try:
            # Create or get session
            session_id = self.sessions.get("default")
            if not session_id:
                session_id = self.api.create_chat_session()
                self.sessions["default"] = session_id

            # Combine messages into a single prompt
            prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])

            if stream:
                return self.api.chat_completion(session_id, prompt)
            else:
                # For non-streaming, collect all chunks into a single response
                chunks = list(self.api.chat_completion(session_id, prompt))
                full_content = "".join([
                    chunk["choices"][0]["delta"]["content"]
                    for chunk in chunks
                    if chunk["choices"][0]["delta"].get("content")
                ])

                return {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [{
                        "message": {
                            "role": "assistant",
                            "content": full_content
                        },
                        "finish_reason": "stop",
                        "index": 0
                    }]
                }

        except Exception as e:
            raise Exception(f"Failed to generate response: {str(e)}")