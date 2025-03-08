from dsk.api import DeepSeekAPI
import logging
import json
import time
import uuid

logger = logging.getLogger(__name__)

class DeepSeekWrapper:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self.api = DeepSeekAPI(auth_token)
        self.chat_sessions = {}  # Store active chat sessions

    def refresh_cookies(self):
        """Refresh the cookies used for DeepSeek API requests"""
        logger.info("Refreshing DeepSeek API cookies")
        try:
            # Recreate the DeepSeekAPI instance to force it to reload cookies
            self.api = DeepSeekAPI(self.auth_token)
            logger.info("Cookies refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh cookies: {e}")
            raise Exception(f"Failed to refresh cookies: {e}")

    def generate_response(self, messages, model, stream=False):
        """
        Generate a response using the DeepSeek API

        Args:
            messages (list): List of message dictionaries with 'role' and 'content'
            model (str): Model to use for generation
            stream (bool): Whether to stream the response

        Returns:
            Either a complete response object or a generator for streaming
        """
        logger.info(f"Generating response with model: {model}, stream: {stream}")

        try:
            # Get the last user message
            user_message = None
            for msg in reversed(messages):
                if msg['role'] == 'user':
                    user_message = msg['content']
                    break

            if not user_message:
                raise ValueError("No user message found in the conversation")

            # Get chat history
            history = []
            for msg in messages:
                if msg['role'] not in ['user', 'assistant']:
                    continue
                history.append({"role": msg['role'], "content": msg['content']})

            # Create a chat session if needed
            session_id = self.chat_sessions.get(model)
            if not session_id:
                session_id = self.api.create_chat_session()
                self.chat_sessions[model] = session_id
                logger.info(f"Created new chat session: {session_id}")

            # For non-streaming mode
            if not stream:
                full_response = ""
                for chunk in self.api.chat_completion(
                    chat_session_id=session_id,
                    prompt=user_message,
                    parent_message_id=None,  # You may need to track message IDs
                    thinking_enabled=True,
                    search_enabled=False
                ):
                    if 'content' in chunk:
                        full_response += chunk['content']

                # Format as OpenAI-compatible response
                return {
                    "id": f"chatcmpl-{uuid.uuid4()}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": full_response
                            },
                            "finish_reason": "stop"
                        }
                    ]
                }

            # For streaming mode, return a generator that yields OpenAI-compatible chunks
            else:
                def generate_streaming_response():
                    response_id = f"chatcmpl-{uuid.uuid4()}"
                    for chunk in self.api.chat_completion(
                        chat_session_id=session_id,
                        prompt=user_message,
                        parent_message_id=None,  # You may need to track message IDs
                        thinking_enabled=True,
                        search_enabled=False
                    ):
                        if 'content' in chunk and chunk['content']:
                            yield {
                                "id": response_id,
                                "object": "chat.completion.chunk",
                                "created": int(time.time()),
                                "model": model,
                                "choices": [
                                    {
                                        "index": 0,
                                        "delta": {
                                            "content": chunk['content']
                                        },
                                        "finish_reason": chunk.get('finish_reason')
                                    }
                                ]
                            }

                return generate_streaming_response()

        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise