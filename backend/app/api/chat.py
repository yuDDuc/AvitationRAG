import json
import os
import re
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.core.security import is_prompt_injection, sanitize_input
from app.api.chat_history import chat_history_service
from app.services.cache_service import SemanticCacheService
from app.services.chat_service import ChatService
from app.services.vector_service import VectorService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    subject: Optional[str] = ""
    user_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    k: int = Field(default=4, ge=1, le=10)


class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    suggested_questions: List[str] = []
    status: str


def _normalize_subject(subject_name: str) -> str:
    return subject_name.strip().lower()


def _sse(data: str, event: str = None) -> str:
    prefix = f"event: {event}\n" if event else ""
    return f"{prefix}data: {data}\n\n"


def _dedupe_sources(sources: List[dict]) -> List[dict]:
    seen = set()
    unique_sources = []
    for source in sources:
        key = (
            source.get("source", "N/A"),
            source.get("page", "N/A"),
            source.get("subject", "N/A"),
        )
        if key in seen:
            continue
        seen.add(key)
        unique_sources.append(source)
    return unique_sources


def _extract_suggested_questions(answer: str) -> List[str]:
    match = re.search(r"Cau hoi goi y:\s*(.*)", answer, re.IGNORECASE | re.DOTALL)
    if not match:
        match = re.search(r"Câu hỏi gợi ý:\s*(.*)", answer, re.IGNORECASE | re.DOTALL)
    if not match:
        return []

    suggestions = []
    for line in match.group(1).splitlines():
        cleaned = re.sub(r"^\s*[-*+0-9.)]+\s*", "", line).strip()
        if cleaned.endswith("?") and cleaned not in suggestions:
            suggestions.append(cleaned)
        if len(suggestions) == 5:
            break
    return suggestions


# Singleton-like services
vector_service = VectorService()
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
vector_db_path = os.path.join(base_dir, "data", "vector_db")
if os.path.exists(vector_db_path):
    try:
        vector_service.load_local(vector_db_path)
    except Exception:
        pass

chat_service = ChatService()
semantic_cache = SemanticCacheService()


@router.post("/completions")
async def chat_completions(request: ChatRequest):
    """Stream RAG chat responses for AI-F4 and AI-F5."""
    clean_message = sanitize_input(request.message)
    subject = _normalize_subject(request.subject) if request.subject else ""
    user_id = sanitize_input(request.user_id)

    if not clean_message:
        raise HTTPException(status_code=400, detail="Message is required.")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID is required.")

    session = chat_history_service.get_or_create_session(
        user_id=user_id,
        subject=subject,
        session_id=request.session_id,
        title_seed=clean_message,
    )
    session_payload = json.dumps(session, ensure_ascii=False)
    chat_history_service.add_message(
        session_id=session["id"],
        role="user",
        content=clean_message,
    )

    if is_prompt_injection(clean_message):
        blocked_answer = "He thong phat hien noi dung khong an toan va tu choi xu ly."
        chat_history_service.add_message(
            session_id=session["id"],
            role="assistant",
            content=blocked_answer,
        )

        def blocked_generator():
            yield _sse(session_payload, event="session")
            yield _sse("blocked_by_guardrail", event="status")
            yield _sse("[]", event="sources")
            yield _sse("[]", event="suggestions")
            yield _sse(blocked_answer)

        return StreamingResponse(blocked_generator(), media_type="text/event-stream")

    cache_key = f"session={session['id']}|question={clean_message}"
    cached_answer = semantic_cache.check_cache(cache_key)
    if cached_answer:
        suggestions = _extract_suggested_questions(cached_answer)
        chat_history_service.add_message(
            session_id=session["id"],
            role="assistant",
            content=cached_answer,
            suggested_questions=suggestions,
        )

        def cache_generator():
            yield _sse(session_payload, event="session")
            yield _sse("answered_from_cache", event="status")
            yield _sse("[]", event="sources")
            yield _sse(json.dumps(suggestions, ensure_ascii=False), event="suggestions")
            yield _sse(cached_answer.replace("\n", "\\n"))

        return StreamingResponse(cache_generator(), media_type="text/event-stream")

    docs = vector_service.search(
        clean_message,
        subject=subject,
        k=request.k,
    )


    max_context_length = 3000
    compressed_docs = []
    current_len = 0
    for doc in docs:
        if current_len + len(doc.page_content) > max_context_length:
            remaining_space = max_context_length - current_len
            if remaining_space > 200:
                doc.page_content = doc.page_content[:remaining_space] + "... [trimmed]"
                compressed_docs.append(doc)
            break
        compressed_docs.append(doc)
        current_len += len(doc.page_content)

    sources = _dedupe_sources([doc.metadata for doc in compressed_docs])
    sources_json = json.dumps(sources, ensure_ascii=False)

    def event_generator():
        yield _sse(session_payload, event="session")
        yield _sse("answering", event="status")
        yield _sse(sources_json, event="sources")

        full_answer = ""
        try:
            for chunk in chat_service.stream_answer(clean_message, compressed_docs, subject):
                full_answer += chunk
                yield _sse(chunk.replace("\n", "\\n"))

            suggestions = _extract_suggested_questions(full_answer)
            yield _sse(json.dumps(suggestions, ensure_ascii=False), event="suggestions")

            if full_answer:
                chat_history_service.add_message(
                    session_id=session["id"],
                    role="assistant",
                    content=full_answer,
                    sources=sources,
                    suggested_questions=suggestions,
                )
                semantic_cache.add_to_cache(cache_key, full_answer)
                yield _sse("answered", event="status")
        except Exception as exc:
            yield _sse(f"Loi sinh cau tra loi: {str(exc)}", event="error")

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# Alias for typo in URL (client may call /comppletions)
@router.post("/comppletions")
async def chat_comppletions(request: ChatRequest):
    """Redirect to the correct completions endpoint."""
    return await chat_completions(request)
