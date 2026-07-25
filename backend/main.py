from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

# Tải cấu hình từ file .env
load_dotenv()

from app.api import chat_history_router, chat_router, quiz_router, feedback_router, documents_router

app = FastAPI(title="Aviation RAG API")

# Cấu hình CORS cho phép giao diện Frontend kết nối
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Cho phép tất cả các nguồn (dùng cho test)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đăng ký các router
app.include_router(chat_router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(chat_history_router, prefix="/api/v1/chat-history", tags=["Chat History"])
app.include_router(quiz_router, prefix="/api/v1/quiz", tags=["Quiz"])
app.include_router(feedback_router, prefix="/api/v1/feedback", tags=["Feedback"])
app.include_router(documents_router, prefix="/api/v1/documents", tags=["Documents"])

@app.get("/")
async def root():
    return {"message": "Aviation RAG Backend is running"}
