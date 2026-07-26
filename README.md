# Aviation AI Assistant

Dự án phát triển hệ thống Chatbot RAG (Retrieval-Augmented Generation) phục vụ công tác đào tạo hàng không. Hệ thống giúp trích xuất và trả lời câu hỏi dựa trên tài liệu nội bộ, ưu tiên bảo mật dữ liệu và tối ưu tốc độ xử lý.

---

## Tính năng chính

### 1. Xử lý tài liệu (Document Processing)
- Hỗ trợ các định dạng: PDF, DOCX, PPTX.
- Tự động clean data (loại bỏ khoảng trắng thừa, ký tự rác).
- Sử dụng `RecursiveCharacterTextSplitter` để chia nhỏ văn bản (chunking) nhưng vẫn giữ được ngữ cảnh.

### 2. Kiến trúc Hybrid RAG & Vector Database
- Sử dụng **FAISS** để lưu trữ vector hoàn toàn tại Local, đảm bảo dữ liệu nội bộ không bị rò rỉ ra ngoài.
- Dùng **HuggingFace Embeddings** (`paraphrase-multilingual-MiniLM-L12-v2`) để tạo vector semantic, hỗ trợ tiếng Việt cực tốt mà không tốn phí API.
- Tích hợp **Gemini API** (`gemini-flash-latest`) để tổng hợp câu trả lời thông minh dựa trên Strict Context (chỉ trả lời dựa trên tài liệu, không "ảo giác").

### 3. Tối ưu hiệu năng
- **Streaming Response:** Trả kết quả về client dạng stream (SSE) để giảm độ trễ.
- **Semantic Cache:** Lưu lại kết quả truy vấn vào FAISS. Nếu câu hỏi mới giống > 85% câu cũ, trả về ngay từ cache (0ms) mà không gọi LLM.
- **Context Compression:** Rút gọn nội dung context trước khi gửi cho LLM (tối đa 3000 ký tự) để tiết kiệm token và tăng tốc độ xử lý.

### 4. Tiện ích & Bảo mật
- **Tạo Quiz tự động:** LLM tự động sinh câu hỏi trắc nghiệm (có đáp án và giải thích) từ tài liệu học.
- **Gợi ý câu hỏi:** Tự động tạo 3 câu hỏi follow-up sau mỗi câu trả lời.
- **Prompt Sanitization:** Có cơ chế check và chặn các truy vấn cố tình jailbreak hoặc prompt injection.
- **Feedback System:** API lưu lại đánh giá của người dùng để cải thiện chất lượng AI.

---

## Cài đặt & Chạy local

### 1. Cài package
Yêu cầu: Python 3.9+.
```bash
pip install -r requirements.txt
```

### 2. Cấu hình biến môi trường
Tạo file `.env` trong thư mục `backend`:
```bash
cp .env.example backend/.env
```
Mở `backend/.env` và cấu hình API key:
```env
GOOGLE_API_KEY=your_api_key_here
GOOGLE_LLM_MODEL=pickone
```

### 3. Chạy Backend
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```
API Docs (Swagger UI) sẽ có tại: `http://127.0.0.1:8000/docs`

### 4. Truy cập giao diện (Frontend)
Bạn có thể mở giao diện bằng 1 trong các cách sau:
- **Cách nhanh nhất:** Truy cập `http://127.0.0.1:8000/frontend/` (backend đã tích hợp sẵn để serve thư mục frontend).
- Mở file `frontend/index.html` trực tiếp trên trình duyệt.
- Dùng extension Live Server trên VS Code.
- Chạy http server độc lập:
  ```bash
  cd frontend
  python -m http.server 8080
  ```

---

## API Endpoints cơ bản

Dưới đây là một số route chính. Để xem chi tiết payload/response, vui lòng check Swagger UI.

**Tài liệu (`/api/v1/documents`)**
- `POST /upload` - Upload và xử lý 1 file.
- `POST /upload-batch` - Upload nhiều file cùng lúc.
- `POST /ingest-folder` - Quét và nạp toàn bộ file từ một thư mục ở local.
- `GET /` - Lấy danh sách tài liệu đang có.
- `POST /clear-semantic-cache` - Xóa bộ nhớ đệm semantic.
- `POST /clear-all-data` - Xóa toàn bộ database.
- `DELETE /{subject}` - Xóa dữ liệu của một môn cụ thể.

**Chat (`/api/v1/chat`)**
- `POST /completions` - Gửi câu hỏi, nhận luồng stream trả lời.

**Lịch sử (`/api/v1/chat-history`)**
- `POST /sessions` - Tạo phiên chat mới.
- `GET /sessions` - Lấy danh sách phiên chat.
- `GET /sessions/{id}/messages` - Lấy lịch sử tin nhắn của 1 phiên.
- `DELETE /sessions/{id}` - Xóa một phiên chat.

**Quiz (`/api/v1/quiz`)**
- `POST /generate` - Sinh trắc nghiệm từ tài liệu môn học.
- `POST /save` - Lưu bộ câu hỏi.
- `GET /list` - Lấy danh sách quiz đã lưu.
- `GET /{filename}` - Xem chi tiết một bài quiz.

**Feedback (`/api/v1/feedback`)**
- `POST /` - Lưu đánh giá (hữu ích / không hữu ích) của người dùng.
- `GET /stats` - Xem thống kê tổng quan.
- `GET /unhelpful` - Lấy danh sách các câu trả lời bị đánh giá tệ.
- `GET /gap-analysis` - Phân tích lỗ hổng kiến thức để đề xuất bổ sung tài liệu.| :--- | :--- | :--- |
| `POST` | `/generate` | Sinh câu hỏi trắc nghiệm từ tài liệu môn học | JSON: `{ "subject": "Môn học", "level": "độ khó", "num_questions": 5 }` |
| `POST` | `/save` | Lưu bài tập trắc nghiệm | JSON: `{ "filename": "...", "quiz_data": {...} }` |
| `GET` | `/list` | Liệt kê các bài tập đã lưu | - |
| `GET` | `/{filename}` | Lấy nội dung chi tiết bài tập | - |

### 5. Feedback API (`/api/v1/feedback`)
| Method | Endpoint        | Mô tả                                           | Payload/Params                                                    |
| :-------| :----------------| :------------------------------------------------| :------------------------------------------------------------------|
| `POST` | `/`             | Lưu phản hồi đánh giá của học viên              | JSON: `{ "question": "...", "answer": "...", "is_useful": true }` |
| `GET`  | `/stats`        | Lấy thống kê tổng số phản hồi và tỷ lệ hài lòng | -                                                                 |
| `GET`  | `/unhelpful`    | Liệt kê các câu hỏi bị đánh giá không hữu ích   | -                                                                 |
| `GET`  | `/gap-analysis` | Phân tích lỗ hổng kiến thức và đề xuất bổ sung  | -                                                                 |

---