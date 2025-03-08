from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import time
import uuid
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from .deepseek_wrapper import DeepSeekWrapper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
    try:
        for chunk in generator:
            # Log the first few characters of each chunk
            chunk_preview = json.dumps(chunk)[:50] + "..." if len(json.dumps(chunk)) > 50 else json.dumps(chunk)
            logger.debug(f"Streaming chunk: {chunk_preview}")
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as e:
        logger.error(f"Error in stream_response: {str(e)}")
        error_json = {
            "error": True,
            "message": str(e)
        }
        yield f"data: {json.dumps(error_json)}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/v1/chat/completions")
async def create_chat_completion(request: Request):
    try:
        logger.info("Received chat completion request")
        data = await request.json()

        # Process the messages
        processed_messages = []
        for msg in data.get("messages", []):
            processed_messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })

        if not processed_messages:
            logger.warning("No messages provided in request")
            return JSONResponse(
                status_code=400,
                content={"error": "No messages provided"}
            )

        model = data.get("model", "deepseek-chat")
        stream = data.get("stream", False)
        logger.info(f"Processing request: model={model}, stream={stream}")

        try:
            response = deepseek.generate_response(processed_messages, model, stream)

            if stream:
                logger.info("Returning streaming response")
                return StreamingResponse(
                    stream_response(response),
                    media_type="text/event-stream",
                    headers={
                        "Cache-Control": "no-cache",
                        "Connection": "keep-alive"
                    }
                )
                
            logger.info("Returning non-streaming response")
            return response

        except Exception as e:
            logger.error(f"Generation failed: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"error": f"Generation failed: {str(e)}"}
            )

    except Exception as e:
        logger.error(f"Request processing failed: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={"error": f"Request processing failed: {str(e)}"}
        )