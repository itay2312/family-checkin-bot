from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, Field

class Family(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    code: str = Field(index=True, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Member(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    family_id: int = Field(index=True)
    telegram_user_id: int = Field(index=True)
    telegram_chat_id: int = Field(index=True)
    display_name: str
    region: Optional[str] = Field(default=None, index=True)
    last_status: str = Field(default="UNKNOWN")  # UNKNOWN / OK / HELP
    last_checkin_event_id: Optional[int] = Field(default=None, index=True)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class AlertEvent(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    last_alert_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    cleared_at: Optional[datetime] = Field(default=None, index=True)
    is_active: bool = Field(default=True, index=True)
    scope: str = Field(default="GLOBAL")
