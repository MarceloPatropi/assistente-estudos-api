from datetime import date, datetime, timezone
from typing import List, Literal, Optional

from pydantic import AnyHttpUrl, BaseModel, Field, HttpUrl, StrictStr, field_validator

WeekdayName = Literal["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
IMPORTANCE = Literal["low", "normal", "high"]
STATUS = Literal["notStarted", "inProgress", "completed", "waitingOnOthers", "deferred"]


class TodoItem(BaseModel):
    external_id: StrictStr = Field(..., description="Stable ID from the source system to guarantee idempotency.")
    title: StrictStr
    description: Optional[StrictStr] = None
    notes: Optional[StrictStr] = None
    categories: list[StrictStr] = Field(default_factory=list)
    importance: IMPORTANCE = "normal"
    status: STATUS = "notStarted"
    due_date: Optional[date] = Field(
        default=None,
        description="Due date in format YYYY-MM-DD."
    )
    reminded_at: Optional[datetime] = None
    web_url: Optional[StrictStr] = Field(default=None, description="Optional source URL to appear under Linked Resources.")
    source: list[StrictStr] = Field(default_factory=lambda: ["assistente_de_estudos"])

    @field_validator("reminded_at")
    @classmethod
    def ensure_timezone(cls, v: Optional[datetime]) -> Optional[datetime]:
        if v and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

class TodoList(BaseModel):
    items: List[TodoItem] = Field(default_factory=list)
