from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from datetime import datetime


class ChatSessionCreate(BaseModel):
    """Schema for creating a new chat session with initial message"""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Hello, I need help with pregnancy nutrition"
            }
        }
    )
    
    message: str = Field(..., min_length=1, max_length=5000, description="First message to start the conversation")


class ChatSessionResponse(BaseModel):
    """Schema for chat session response"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    title: str
    created_at: datetime


class ChatSessionOut(BaseModel):
    """Complete chat session output with messages"""
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    user_id: str
    title: str
    created_at: datetime
    message_count: Optional[int] = 0


class ConversationTitleUpdate(BaseModel):
    title: str
