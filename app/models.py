from pydantic import BaseModel, Field, validator
from typing import List, Optional, Union, Dict

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[Dict[str, str]]]

    @validator('content', pre=True)
    def flatten_content(cls, v):
        if isinstance(v, list):
            return "\n".join([item.get('text', '') for item in v if 'text' in item])
        return v

class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = False
    temperature: Optional[float] = Field(default=0.7, ge=0, le=2)
    max_tokens: Optional[int] = None
    top_p: Optional[float] = Field(default=1, ge=0, le=1)
    stream_options: Optional[Dict] = None

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

class ModelListResponse(BaseModel):
    object: str = "list"
    data: List[Dict]