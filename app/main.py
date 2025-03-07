from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import time
import uuid
import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .deepseek_wrapper import DeepSeekWrapper

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Hardcoded API key - replace with your actual token
API_KEY = "2zZ7MaVSH+lhKHhrizBi73yAZ26TE+gZPbj/Pxje7QjLezqwqfU4YDsA1fX8eYIv"
deepseek = DeepSeekWrapper(API_KEY)

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
    """Serve the chat interface"""
    try:
        with open("static/index.html", "r") as f:
            content = f.read()
        return HTMLResponse(content=content)
    except Exception:
        # Fallback for Vercel environment
        return JSONResponse(
            content={"message": "API is running. Use /v1/chat/completions endpoint."}
        )

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
        data = await request.json()

        # Process the messages
        processed_messages = []
        for msg in data.get("messages", []):
            processed_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        if not processed_messages:
            return JSONResponse(
                status_code=400,
                content={"error": "No messages provided"}
            )

        model = data.get("model", "deepseek-chat")
        stream = data.get("stream", False)

        try:
            response = deepseek.generate_response(processed_messages, model, stream)

            if stream:
                return StreamingResponse(
                    stream_response(response),
                    media_type="text/event-stream"
                )
            return response

        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"error": f"Generation failed: {str(e)}"}
            )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Request processing failed: {str(e)}"}
        )