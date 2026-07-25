from pydantic import BaseModel
from typing import Optional

class FeedbackEntry(BaseModel):
    question: str
    answer: str
    is_useful: bool
    comment: Optional[str] = None
    subject: str
