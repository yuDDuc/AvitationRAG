from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.services.quiz_service import QuizService
import os
import json
from datetime import datetime

router = APIRouter()

class QuizRequest(BaseModel):
    subject: str
    num_questions: int = 5
    level: Optional[str] = "Trung bình"

class QuizSaveRequest(BaseModel):
    subject: str
    quiz_data: str # Nhận chuỗi JSON từ LLM

quiz_service = QuizService()

# Tận dụng vector_service đã khởi tạo bên chat api
from app.api.chat import vector_service

# Đường dẫn lưu trữ Quiz
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
QUIZ_STORAGE_DIR = os.path.join(base_dir, "data", "quizzes")

@router.post("/generate")
async def generate_quiz(request: QuizRequest):
    """
    Endpoint sinh câu hỏi ôn tập (AI-F6).
    """
    # 1. Lấy tài liệu liên quan đến môn học để sinh câu hỏi
    docs = vector_service.search(request.subject, subject=request.subject, k=10)
    
    if not docs:
        # Thay vì 404, trả về lỗi với thông báo rõ ràng để FE hiển thị
        raise HTTPException(
            status_code=400, 
            detail=f"Không tìm thấy tài liệu cho môn học '{request.subject}'. Vui lòng kiểm tra lại tên môn học hoặc upload tài liệu trước khi sinh quiz."
        )
    
    # 2. Sinh câu hỏi bằng LLM
    try:
        quiz_data = quiz_service.generate_quiz(request.subject, docs, request.num_questions)
        # Đảm bảo quiz_data là chuỗi JSON hợp lệ
        return {"quiz": quiz_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi hệ thống khi sinh quiz: {str(e)}")

@router.post("/save")
async def save_quiz(request: QuizSaveRequest):
    """
    Lưu bộ câu hỏi Quiz vào file để giáo viên đánh giá (AI-F6.5).
    """
    try:
        # Tạo thư mục lưu trữ nếu chưa có
        os.makedirs(QUIZ_STORAGE_DIR, exist_ok=True)
        
        # Tạo tên file: subject_timestamp.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{request.subject.replace(' ', '_').lower()}_{timestamp}.json"
        file_path = os.path.join(QUIZ_STORAGE_DIR, filename)
        
        # Parse JSON để đảm bảo đúng định dạng trước khi lưu
        quiz_json = json.loads(request.quiz_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(quiz_json, f, ensure_ascii=False, indent=2)
            
        return {"message": f"Đã lưu bộ câu hỏi vào file {filename}", "filename": filename}
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Dữ liệu quiz không phải là JSON hợp lệ.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu quiz: {str(e)}")

@router.get("/list")
async def list_quizzes():
    """
    Liệt kê tất cả các bộ quiz đã lưu.
    """
    if not os.path.exists(QUIZ_STORAGE_DIR):
        return {"quizzes": []}
        
    files = [f for f in os.listdir(QUIZ_STORAGE_DIR) if f.endswith(".json")]
    
    quiz_list = []
    for f in files:
        # Bóc tách subject và thời gian từ tên file
        parts = f.replace(".json", "").split("_")
        # Vì subject có thể chứa gạch dưới, ta lấy phần cuối là timestamp
        timestamp = parts[-1]
        subject = "_".join(parts[:-1])
        
        quiz_list.append({
            "filename": f,
            "subject": subject,
            "created_at": timestamp
        })
        
    return {"quizzes": quiz_list}

@router.get("/{filename}")
async def get_quiz_content(filename: str):
    """
    Lấy nội dung của một bộ quiz cụ thể.
    """
    file_path = os.path.join(QUIZ_STORAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Không tìm thấy file quiz.")
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return {"filename": filename, "quiz": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi đọc file quiz: {str(e)}")
