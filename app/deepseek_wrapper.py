from dsk.api import DeepSeekAPI
import logging
import json
import time
import uuid

logger = logging.getLogger(__name__)

class DeepSeekWrapper:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        try:
            from dsk.api import DeepSeekAPI
            self.api = DeepSeekAPI(auth_token)
        except Exception as e:
            logger.warning(f"Could not initialize DeepSeekAPI: {e}")
            self.api = None
        self.chat_sessions = {}  # Store active chat sessions

    def refresh_cookies(self):
        """Refresh the cookies used for DeepSeek API requests"""
        logger.info("Refreshing DeepSeek API cookies")
        try:
            # In serverless, return a dummy success response
            if self.api is None:
                return {"success": True, "message": "Dummy cookie refresh (serverless mode)"}
            
            # Recreate the DeepSeekAPI instance to force it to reload cookies
            from dsk.api import DeepSeekAPI
            self.api = DeepSeekAPI(self.auth_token)
            logger.info("Cookies refreshed successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to refresh cookies: {e}")
            raise Exception(f"Failed to refresh cookies: {e}")

    def generate_response(self, messages, model, stream=False):
        """
        Generate a response using the DeepSeek API or return a fallback response
        if in serverless environment
        """
        logger.info(f"Generating response with model: {model}, stream: {stream}")

        # Add fallback for serverless environment
        if self.api is None:
            fallback_msg = "This is a serverless environment where the DeepSeek API can't run directly. Please use the hosted version or run locally."
            if not stream:
                import uuid
                import time
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
                                "content": fallback_msg
                            },
                            "finish_reason": "stop"
                        }
                    ]
                }
            else:
                def generate_fallback():
                    import uuid
                    import time
                    response_id = f"chatcmpl-{uuid.uuid4()}"
                    yield {
                        "id": response_id,
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": model,
                        "choices": [
                            {
                                "index": 0,
                                "delta": {
                                    "content": fallback_msg
                                },
                                "finish_reason": "stop"
                            }
                        ]
                    }
                return generate_fallback()

        # Original implementation for non-serverless environment
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