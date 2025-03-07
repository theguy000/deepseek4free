from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import time
import uuid
from typing import AsyncGenerator, Dict, List, Optional
from .models import ChatCompletionRequest, ChatCompletionResponse, Choice, ChatMessage, ModelListResponse
from .deepseek_wrapper import DeepSeekWrapper

app = FastAPI()
deepseek = DeepSeekWrapper("2zZ7MaVSH+lhKHhrizBi73yAZ26TE+gZPbj/Pxje7QjLezqwqfU4YDsA1fX8eYIv")

conversation_store = {}

def save_debug_info(message: str, filename: str = "m.txt") -> None:
    with open(filename, "a+") as f:
        f.write(f"{time.time()}: {message}\n")

@app.get("/v1/models")
async def list_models():
    print("DEBUG: /v1/models endpoint called")
    response = ModelListResponse(
        data=[{
            "id": "deepseek-chat",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "custom"
        }]
    )
    print(f"DEBUG: Returning models response: {response}")
    return response

@app.post("/v1/chat/completions")
async def create_chat_completion(request: Request):
    print("\n--- New Chat Completion Request ---")
    # Add header logging
    print("DEBUG: Request Headers:")
    for header, value in request.headers.items():
        print(f"  {header}: {value}")

    try:
        request_data = await request.json()
        # Create a sanitized version of request data without message content
        sanitized_data = request_data.copy() if isinstance(request_data, dict) else {}
        if "messages" in sanitized_data:
            sanitized_data["messages"] = f"[{len(sanitized_data['messages'])} messages]"

        print(f"DEBUG: Request metadata: {json.dumps(sanitized_data, indent=2)}")

        chat_request = ChatCompletionRequest(**request_data)
        print(f"DEBUG: Model: {chat_request.model}, Stream: {chat_request.stream}, Temperature: {chat_request.temperature}")
        print(f"DEBUG: Message count: {len(chat_request.messages)}")

        # Process messages without printing their content
        processed_messages = [{
            "role": msg.role,
            "content": msg.content if isinstance(msg.content, str)
                    else "\n".join([item.get('text', '') for item in msg.content])
        } for msg in chat_request.messages]

        print(f"DEBUG: Processed {len(processed_messages)} messages")
        print(f"DEBUG: Stream mode: {chat_request.stream}")

        # Extract conversation ID for tracking
        conversation_id = None
        if hasattr(chat_request, 'user') and chat_request.user:
            conversation_id = chat_request.user
            print(f"DEBUG: Using provided user field as conversation ID: {conversation_id}")
        else:
            conversation_id = str(uuid.uuid4())
            print(f"DEBUG: Generated new conversation ID: {conversation_id}")

        save_debug_info(f"Using conversation ID: {conversation_id}", "m.txt")

        # Check if this is a new or continuing conversation
        chat_id = None
        parent_message_id = None

        if conversation_id in conversation_store:
            chat_id = conversation_store[conversation_id]["chat_id"]
            parent_message_id = conversation_store[conversation_id]["last_message_id"]
            print(f"DEBUG: Continuing conversation {conversation_id} with chat_id {chat_id} and parent_message_id {parent_message_id}")
            save_debug_info(f"Continuing conversation with chat_id {chat_id} and parent_message_id {parent_message_id}", "m.txt")
        else:
            # Create a new chat session
            try:
                chat_id = deepseek.create_chat_session()
                conversation_store[conversation_id] = {"chat_id": chat_id, "last_message_id": None}
                print(f"DEBUG: Created new conversation {conversation_id} with chat_id {chat_id}")
                save_debug_info(f"Created new conversation with chat_id {chat_id}", "m.txt")
            except Exception as e:
                error_msg = f"Error creating chat session: {str(e)}"
                print(f"DEBUG: {error_msg}")
                save_debug_info(error_msg, "m.txt")
                raise HTTPException(status_code=500, detail=error_msg)

        # Prepare the input by combining system and user messages
        combined_input = ""
        for msg in processed_messages:
            role = msg["role"]
            content = msg["content"]
            
            if role == "system":
                combined_input += f"System: {content}\n\n"
            elif role == "user":
                # Only add the last user message as the actual prompt
                if msg == processed_messages[-1] or (len(processed_messages) > 1 and processed_messages[-1]["role"] == "assistant" and msg == processed_messages[-2]):
                    last_user_message = content
                else:
                    combined_input += f"User: {content}\n\n"
            elif role == "assistant":
                combined_input += f"Assistant: {content}\n\n"

        # Get the last user message for the actual prompt
        last_user_message = None
        for msg in reversed(processed_messages):
            if msg["role"] == "user":
                last_user_message = msg["content"]
                break

        if not last_user_message:
            error_msg = "No user message found in the conversation"
            print(f"DEBUG: {error_msg}")
            save_debug_info(error_msg, "m.txt")
            raise HTTPException(status_code=400, detail=error_msg)

        # If there's context, prepend it to the user's message
        if combined_input:
            last_user_message = f"{combined_input}User: {last_user_message}"
            
        save_debug_info(f"Combined input: {last_user_message[:500]}...", "m.txt")

        if chat_request.stream:
            print("DEBUG: Returning streaming response")
            return StreamingResponse(
                stream_chat_completion(
                    last_user_message=last_user_message,
                    request=chat_request,
                    chat_id=chat_id,
                    parent_message_id=parent_message_id,
                    conversation_id=conversation_id
                ),
                media_type="text/event-stream"
            )
        else:
            print("DEBUG: Generating non-streaming response")
            response = deepseek.generate_response(
                messages=processed_messages,
                model=chat_request.model,
                stream=False
            )

            # Create sanitized response (without content) for logging
            sanitized_response = {
                "id": response["id"],
                "created": response["created"],
                "model": response.get("model", chat_request.model),
                "choices": [{"index": c.get("index", 0), "finish_reason": c.get("finish_reason", "stop")}
                        for c in response.get("choices", [])]
            }
            print(f"DEBUG: DeepSeek response metadata: {json.dumps(sanitized_response, indent=2)}")

            formatted_response = ChatCompletionResponse(
                id=response["id"],
                created=response["created"],
                model=chat_request.model,
                choices=[Choice(
                    index=0,
                    message=ChatMessage(
                        role="assistant",
                        content=response["choices"][0]["message"]["content"]
                    ),
                    finish_reason="stop"
                )]
            )
            print(f"DEBUG: Response generated successfully")
            return formatted_response

    except Exception as e:
        print(f"DEBUG: ERROR in chat completion: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

async def stream_chat_completion(
    last_user_message: str,
    request: ChatCompletionRequest,
    chat_id: str,
    parent_message_id: Optional[str],
    conversation_id: str
) -> AsyncGenerator[str, None]:
    try:
        print("DEBUG: Starting streaming response generation")
        save_debug_info("Starting streaming response generation", "m.txt")
        save_debug_info(f"Parameters: chat_id={chat_id}, parent_message_id={parent_message_id}", "m.txt")
        save_debug_info(f"Using combined input: {last_user_message[:500]}...", "m.txt")
        
        chunk_count = 0
        message_id = None
        
        # Call DeepSeek API directly with the correct parameters
        for chunk in deepseek.api.chat_completion(
            chat_session_id=chat_id,
            prompt=last_user_message,
            parent_message_id=parent_message_id
        ):
            chunk_count += 1
            # Log metadata about the chunk without the content
            sanitized_chunk = {
                "id": chunk.get("id", ""),
                "created": chunk.get("created", 0),
                "model": chunk.get("model", ""),
            }
            if chunk_count % 10 == 0:  # Log only every 10th chunk to reduce noise
                print(f"DEBUG: Streaming chunk #{chunk_count}")
            yield f"data: {json.dumps(chunk)}\n\n"
        print(f"DEBUG: Stream completed, sent {chunk_count} chunks")
        yield "data: [DONE]\n\n"
    except Exception as e:
        print(f"DEBUG: ERROR in streaming: {str(e)}")
        import traceback
        print(f"DEBUG: Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))