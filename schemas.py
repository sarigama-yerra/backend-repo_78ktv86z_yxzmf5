"""
Database Schemas for the Dating App

Each Pydantic model maps to a MongoDB collection (lowercased class name).
- User -> "user"
- Like -> "like"
- Match -> "match"
- Message -> "message"
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal

Gender = Literal["male", "female"]
Seeking = Literal["male", "female", "both"]

class User(BaseModel):
    name: str = Field(..., min_length=1, max_length=60, description="Display name")
    gender: Gender = Field(..., description="User gender")
    seeking: Seeking = Field(..., description="Who the user wants to match with")
    bio: Optional[str] = Field(None, max_length=280, description="Short bio")
    avatar_url: Optional[str] = Field(None, description="Avatar image URL")

class Like(BaseModel):
    liker_id: str = Field(..., description="User ID who liked")
    liked_id: str = Field(..., description="User ID who was liked")

class Match(BaseModel):
    user1_id: str = Field(..., description="First user ID")
    user2_id: str = Field(..., description="Second user ID")
    allow_both_first_move: bool = Field(True, description="Whether both can message first")

class Message(BaseModel):
    match_id: str = Field(..., description="Match ID")
    sender_id: str = Field(..., description="Sender user ID")
    text: str = Field(..., min_length=1, max_length=1000, description="Message text")
