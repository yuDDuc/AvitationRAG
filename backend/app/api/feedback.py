from fastapi import APIRouter
from app.models.feedback import FeedbackEntry
from typing import List

router = APIRouter()

# Lưu trữ tạm thời trong memory (AI-F7.1)
# Trong thực tế nên dùng Database chính thức
feedback_db = []

@router.post("/")
async def submit_feedback(feedback: FeedbackEntry):
    """
    Endpoint lưu phản hồi của học viên về câu trả lời AI (AI-F7.1).
    """
    feedback_db.append(feedback.dict())
    return {"message": "Cảm ơn bạn đã phản hồi!"}

@router.get("/stats")
async def get_stats():
    """
    Thống kê tỷ lệ câu trả lời được đánh giá hữu ích (AI-F7.2).
    """
    total = len(feedback_db)
    useful = sum(1 for f in feedback_db if f["is_useful"])
    useful_rate = (useful / total * 100) if total > 0 else 0
    
    return {
        "total_feedback": total,
        "useful_count": useful,
        "useful_rate": f"{useful_rate:.2f}%"
    }

@router.get("/unhelpful")
async def get_unhelpful_feedback():
    """
    Lấy danh sách các phản hồi được đánh giá là Không hữu ích (AI-F7.3).
    """
    unhelpful = [f for f in feedback_db if not f["is_useful"]]
    return {
        "count": len(unhelpful),
        "details": unhelpful
    }

@router.get("/gap-analysis")
async def get_gap_analysis():
    """
    Phân tích lỗ hổng kiến thức (AI-F7.4).
    Lọc các câu hỏi bị đánh giá 'Không hữu ích' VÀ có câu trả lời thông báo thiếu thông tin.
    """
    gap_keywords = ["does not provide this information", "không tìm thấy thông tin", "chưa có trong tài liệu"]
    
    gap_docs = []
    for f in feedback_db:
        if not f["is_useful"]:
            # Kiểm tra xem câu trả lời có chứa từ khóa báo thiếu thông tin không
            if any(kw.lower() in f["answer"].lower() for kw in gap_keywords):
                gap_docs.append(f)
                
    # Gom nhóm theo môn học (subject)
    analysis = {}
    for item in gap_docs:
        subject = item.get("subject", "Unknown")
        if subject not in analysis:
            analysis[subject] = []
        analysis[subject].append({
            "question": item["question"],
            "answer": item["answer"],
            "comment": item.get("comment", "")
        })
        
    return {
        "message": "Phân tích lỗ hổng kiến thức dựa trên phản hồi người dùng.",
        "gap_analysis": analysis,
        "total_gaps_found": len(gap_docs)
    }
