from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse
import json
import time
import uuid
import os
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .deepseek_wrapper import DeepSeekWrapper

app = FastAPI()

# Get the API key from environment variables
api_key = os.environ.get("DEEPSEEK_AUTH_TOKEN", "")
deepseek = DeepSeekWrapper(api_key)

# Pydantic models
class ChatMessage(BaseModel):
    role: str
    content: str
    name: Optional[str] = None

class ChatCompletionRequest(BaseModel):
    model: str = "deepseek-chat"
    messages: List[ChatMessage]
    temperature: float = 0.7
    top_p: float = 1.0
    stream: bool = False
    max_tokens: Optional[int] = None
    user: Optional[str] = None

class Choice(BaseModel):
    index: int
    message: ChatMessage
    finish_reason: str

class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]

class Model(BaseModel):
    id: str
    object: str = "model"
    created: int
    owned_by: str

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[Model]

@app.get("/")
async def root():
    return {"message": "DeepSeek API wrapper is running! Use /v1/chat/completions endpoint."}

@app.get("/v1/models")
async def list_models():
    response = ModelListResponse(
        object="list",
        data=[
            Model(
                id="deepseek-chat",
                object="model",
                created=int(time.time()),
                owned_by="custom"
            ),
            Model(
                id="deepseek-reasoner",
                object="model",
                created=int(time.time()),
                owned_by="custom"
            )
        ]
    )
    return response

async def stream_response(generator):
    for chunk in generator:
        yield f"data: {json.dumps(chunk)}\n\n"
    yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def create_chat_completion(request: Request):
    try:
        # Parse the request
        data = await request.json()
        
        # Process the messages
        processed_messages = []
        for msg in data.get("messages", []):
            processed_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Check if we have any messages
        if not processed_messages:
            return JSONResponse(
                status_code=400,
                content={"error": "No messages provided"}
            )
        
        # Get parameters
        model = data.get("model", "deepseek-chat")
        stream = data.get("stream", False)
        
        # Generate response
        response = deepseek.generate_response(processed_messages, model, stream)
        
        # Return streaming or complete response
        if stream:
            return StreamingResponse(
                stream_response(response),
                media_type="text/event-stream"
            )
        return response
        
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Error processing request: {str(e)}",
                "detail": error_detail
            }
        )

# Vercel serverless handler
def handler(request, response):
    return app