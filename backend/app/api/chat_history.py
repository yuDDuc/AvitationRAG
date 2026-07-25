from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.chat_history_service import ChatHistoryService

router = APIRouter()
chat_history_service = ChatHistoryService()


class CreateSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    subject: str = Field(..., min_length=1)
    title: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    user_id: str = Field(..., min_length=1)
    title: Optional[str] = None
    subject: Optional[str] = None


@router.post("/sessions")
async def create_session(request: CreateSessionRequest):
    return chat_history_service.create_session(
        user_id=request.user_id.strip(),
        subject=request.subject.strip().lower(),
        title=request.title,
    )


@router.get("/sessions")
async def list_sessions(user_id: str = Query(..., min_length=1)):
    return {"sessions": chat_history_service.list_sessions(user_id.strip())}


@router.get("/sessions/{session_id}/messages")
async def list_messages(session_id: str, user_id: str = Query(..., min_length=1)):
    session = chat_history_service.get_session(session_id, user_id.strip())
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {
        "session": session,
        "messages": chat_history_service.list_messages(session_id, user_id.strip()),
    }


@router.patch("/sessions/{session_id}")
async def update_session(session_id: str, request: UpdateSessionRequest):
    session = chat_history_service.update_session(
        session_id=session_id,
        user_id=request.user_id.strip(),
        title=request.title,
        subject=request.subject.strip().lower() if request.subject else None,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return session


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, user_id: str = Query(..., min_length=1)):
    deleted = chat_history_service.delete_session(session_id, user_id.strip())
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat session not found.")
    return {"deleted": True}
