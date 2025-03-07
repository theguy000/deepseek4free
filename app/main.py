from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
import json
import time
import uuid
from typing import Dict, List, Optional
from .models import ChatCompletionRequest, ChatCompletionResponse, Choice, ChatMessage, ModelListResponse
from .deepseek_wrapper import DeepSeekWrapper
import os

app = FastAPI()
deepseek = DeepSeekWrapper("2zZ7MaVSH+lhKHhrizBi73yAZ26TE+gZPbj/Pxje7QjLezqwqfU4YDsA1fX8eYIv")

conversation_store = {}

def save_debug_info(message: str, filename: str = "m.txt") -> None:
    # In serverless environments, we might want to log instead of writing to files
    print(f"DEBUG: {message}")

@app.get("/")
async def root():
    return {"message": "DeepSeek API wrapper is running! Use /v1/chat/completions endpoint."}

@app.get("/v1/models")
async def list_models():
    response = ModelListResponse(
        data=[{
            "id": "deepseek-chat",
            "object": "model",
            "created": int(time.time()),
            "owned_by": "custom"
        }]
    )
    return response

@app.post("/v1/chat/completions")
async def create_chat_completion(request: Request):
    try:
        request_data = await request.json()
        chat_request = ChatCompletionRequest(**request_data)
        
        processed_messages = [{
            "role": msg.role,
            "content": msg.content if isinstance(msg.content, str)
                    else "\n".join([item.get('text', '') for item in msg.content])
        } for msg in chat_request.messages]
        
        # Use provided model or default to deepseek-chat
        model = getattr(chat_request, 'model', 'deepseek-chat')
        
        # Stream mode
        stream = getattr(chat_request, 'stream', False)
        
        # Generate the response
        response = deepseek.generate_response(processed_messages, model, stream)
        
        if stream:
            return StreamingResponse(
                response,
                media_type="text/event-stream"
            )
        else:
            return response
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )