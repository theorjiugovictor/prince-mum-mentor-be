import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class AccountDeletionRequest(BaseModel):
    """Schema for account deletion request"""
    password: str = Field(..., min_length=1, description="User password for confirmation")
    confirmation_phrase: str = Field(..., description="Must type 'DELETE MY ACCOUNT' to confirm")
    reason: Optional[str] = Field(None, max_length=500, description="Optional reason for account deletion")

    @field_validator('confirmation_phrase')
    @classmethod
    def validate_confirmation_phrase(cls, v: str) -> str:
        """Validate confirmation phrase"""
        if v.strip().upper() != "DELETE MY ACCOUNT":
            raise ValueError('Must type "DELETE MY ACCOUNT" to confirm deletion')
        return v.strip()
    

    @field_validator('reason')
    @classmethod
    def validate_reason(cls, v: Optional[str]) -> Optional[str]:
        """Validate and clean reason if provided"""
        if v is not None:
            v = v.strip()
            if len(v) == 0:
                return None
            return v
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "password": "UserCurrentPassword123!",
                "confirmation_phrase": "DELETE MY ACCOUNT",
                "reason": "No longer need the service"
            }
        }
    }


class AccountDeletionResponse(BaseModel):
    """Schema for account deletion response"""
    message: str
    deletion_time: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Account and all associated data have been permanently deleted",
                "deletion_time": "2025-11-18T21:30:45Z"
            }
        }
    }