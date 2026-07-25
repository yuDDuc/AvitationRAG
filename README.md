# Aviation AI Assistant - Backend RAG

Dự án xây dựng hệ thống **Chatbot RAG (Retrieval-Augmented Generation)** chuyên dụng cho Đào tạo Hàng không. Hệ thống được thiết kế với mục tiêu mang lại câu trả lời chính xác dựa trên tài liệu đào tạo nội bộ, bảo mật thông tin và tối ưu hóa tốc độ phản hồi cực nhanh.

---

## 🌟 Các tính năng nổi bật đã thực hiện

### 1. Xử lý Tài liệu Đa định dạng (Document Processing)
- Hỗ trợ trích xuất văn bản từ các định dạng phổ biến: **PDF**, **DOCX (Word)**, và **PPTX (Slide PowerPoint)**.
- Tự động làm sạch dữ liệu (loại bỏ ký tự rác, khoảng trắng thừa).
- Chunking thông minh sử dụng `RecursiveCharacterTextSplitter` giúp giữ nguyên ngữ cảnh.

### 2. Kiến trúc Hybrid RAG & Vector Database
- Sử dụng **FAISS** để lưu trữ vector hoàn toàn tại Local, đảm bảo dữ liệu nội bộ không bị rò rỉ ra ngoài.
- Dùng **HuggingFace Embeddings** (`paraphrase-multilingual-MiniLM-L12-v2`) để tạo vector semantic, hỗ trợ tiếng Việt cực tốt mà không tốn phí API.
- Tích hợp **Gemini API** (`gemini-flash-latest`) để tổng hợp câu trả lời thông minh dựa trên Strict Context (chỉ trả lời dựa trên tài liệu, không "ảo giác").

### 3. Tối ưu hóa Tốc độ Phản hồi (High Performance)
- **Streaming Response:** Trả về kết quả dạng Event-Stream (như ChatGPT), giúp giảm Time-To-First-Token (TTFT) xuống cực thấp. Người dùng thấy chữ xuất hiện ngay lập tức.
- **Semantic Cache:** Sử dụng FAISS độc lập làm bộ nhớ đệm. Nếu câu hỏi tương đồng > 85% với câu đã hỏi trước đó, hệ thống trả về kết quả Cache ngay lập tức (0ms) mà không cần gọi API LLM.
- **Context Compression:** Nén và giới hạn ngữ cảnh (chỉ gửi tối đa 3000 ký tự quan trọng nhất lên LLM), giúp giảm chi phí Token và tăng tốc độ đọc của AI.

### 4. Tiện ích Đào tạo & Bảo mật
- **Tự động tạo Quiz:** AI đọc tài liệu và tự động sinh bộ câu hỏi trắc nghiệm (4 lựa chọn, có đáp án và giải thích).
- **Gợi ý câu hỏi liên quan:** Sau mỗi câu trả lời, chatbot gợi ý thêm 3 câu hỏi liên quan để điều hướng học viên.
- **Bảo mật (Prompt Sanitization):** Kiểm tra và chặn các hành vi cố tình Jailbreak hoặc thao túng Prompt (Prompt Injection).
- **Phản hồi & Thống kê:** Lưu trữ đánh giá của học viên về chất lượng câu trả lời.

---

## 🚀 Hướng dẫn Cài đặt & Khởi chạy

### Cài đặt môi trường
Đảm bảo bạn đã cài đặt Python. Mở terminal tại thư mục `backend`:
```bash
pip install -r requirements.txt
```

### Cấu hình API Key
Tạo file `backend/.env` bằng cách copy (hoặc đổi tên) từ file `.env.example` ở thư mục gốc:
```bash
cp .env.example backend/.env
```
Sau đó mở file `backend/.env` và điền API Key của Google Gemini:
```env
GOOGLE_API_KEY=your_api_key_here
GOOGLE_LLM_MODEL=pickone
```

### Khởi chạy Server
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

### Giao diện Kiểm thử (Frontend)
Bạn có thể chạy giao diện Frontend bằng 1 trong 2 cách sau:
- **Cách 1 (Đơn giản nhất):** Mở trực tiếp file `frontend/index.html` bằng trình duyệt (nhấp đúp vào file).
- **Cách 2 (Khuyên dùng):** Sử dụng extension **Live Server** trên VS Code. Chuột phải vào file `frontend/index.html` và chọn "Open with Live Server" để chạy.
- **Cách 3: ** Mở terminal tại thư mục `frontend` và chạy lệnh:
```bash
cd frontend
python -m http.server 8080
```
---

## 📡 Danh sách API Endpoints

Hệ thống cung cấp RESTful API đầy đủ, tích hợp Swagger UI. Bạn có thể xem và test trực tiếp tại: `http://127.0.0.1:8000/docs`.

### 1. Documents API (`/api/v1/documents`)
| Method   | Endpoint                | Mô tả                                         | Payload/Params                                     |
| :---------| :------------------------| :----------------------------------------------| :---------------------------------------------------|
| `POST`   | `/upload`               | Tải lên 1 file tài liệu và nạp vào FAISS      | `file` (File), `subject` (string)                  |
| `POST`   | `/upload-batch`         | Tải lên hàng loạt nhiều file cùng lúc         | `files` (Array File), `subject` (string)           |
| `POST`   | `/ingest-folder`        | Quét và nạp toàn bộ file từ thư mục Local     | JSON: `{ "folder_path": "...", "subject": "..." }` |
| `GET`    | `/`                     | Lấy danh sách tài liệu hiện có trong hệ thống | -                                                  |
| `POST`   | `/clear-semantic-cache` | Xóa bộ nhớ đệm semantic                       | -                                                  |
| `POST`   | `/clear-all-data`       | Xóa toàn bộ dữ liệu vector và index           | -                                                  |
| `DELETE` | `/{subject}`            | Xóa dữ liệu của một môn học cụ thể            | -                                                  |

### 2. Chat API (`/api/v1/chat`)
| Method | Endpoint | Mô tả | Payload |
| :--- | :--- | :--- | :--- |
| `POST` | `/completions` | Hỏi đáp với RAG. Trả về luồng Streaming (Server-Sent Events) | JSON: `{ "message": "Câu hỏi", "subject": "Tên môn" }` |

### 3. Chat History API (`/api/v1/chat-history`)
| Method | Endpoint | Mô tả | Payload/Params |
| :--- | :--- | :--- | :--- |
| `POST` | `/sessions` | Tạo phiên chat mới | JSON: `{ "subject": "Tên môn" }` |
| `GET` | `/sessions` | Lấy danh sách phiên chat | - |
| `GET` | `/sessions/{id}/messages`| Lấy lịch sử tin nhắn trong 1 phiên | - |
| `PATCH` | `/sessions/{id}` | Cập nhật tên phiên chat | JSON: `{ "title": "Tên mới" }` |
| `DELETE`| `/sessions/{id}` | Xóa một phiên chat | - |

### 4. Quiz API (`/api/v1/quiz`)
| Method | Endpoint | Mô tả | Payload |
| :--- | :--- | :--- | :--- |
| `POST` | `/generate` | Sinh câu hỏi trắc nghiệm từ tài liệu môn học | JSON: `{ "subject": "Môn học", "level": "độ khó", "num_questions": 5 }` |
| `POST` | `/save` | Lưu bài tập trắc nghiệm | JSON: `{ "filename": "...", "quiz_data": {...} }` |
| `GET` | `/list` | Liệt kê các bài tập đã lưu | - |
| `GET` | `/{filename}` | Lấy nội dung chi tiết bài tập | - |

### 5. Feedback API (`/api/v1/feedback`)
| Method | Endpoint | Mô tả | Payload/Params |
| :--- | :--- | :--- | :--- |
| `POST` | `/` | Lưu phản hồi đánh giá của học viên | JSON: `{ "question": "...", "answer": "...", "is_useful": true }` |
| `GET` | `/stats` | Lấy thống kê tổng số phản hồi và tỷ lệ hài lòng | - |
| `GET` | `/unhelpful` | Liệt kê các câu hỏi bị đánh giá không hữu ích | - |
| `GET` | `/gap-analysis` | Phân tích lỗ hổng kiến thức và đề xuất bổ sung | - |

---
## 📝 Ghi chú: Tùy chỉnh Chunking cho Văn bản Pháp luật

Nếu bạn muốn tinh chỉnh cách hệ thống chia nhỏ văn bản (chunking) để tối ưu cho cấu trúc đặc thù của tài liệu pháp luật (ví dụ: chia theo "Điều", "Khoản"), bạn có thể chỉnh sửa logic trong file:

`backend/app/services/document_service.py`

Trong hàm `chunk_text`, hãy điều chỉnh các thông số `chunk_size`, `chunk_overlap` hoặc đặc biệt là mảng `separators` của `RecursiveCharacterTextSplitter` để ưu tiên các dấu phân tách theo cấu trúc văn bản của bạn. Ví dụ: `separators=["\n\nĐiều ", "\n\nKhoản ", "\n\n", "\n", " ", ""]`.

---

## 💡 Giảm Hallucination với Re-ranking (Đề xuất)

Để giảm thiểu hallucination (model bịa thông tin), một kỹ thuật rất hiệu quả là **Re-ranking (Xếp hạng lại)** các tài liệu đã được truy xuất.

**Cách hoạt động:** Sau khi hệ thống Vector Database (FAISS) tìm ra một tập hợp các đoạn văn bản có thể liên quan, một mô hình nhỏ hơn, chuyên biệt hơn (thường là một cross-encoder) sẽ được sử dụng để "xếp hạng lại" (re-rank) các đoạn này. Nó sẽ đánh giá độ liên quan thực sự của từng đoạn với câu hỏi của người dùng và chỉ chọn ra những đoạn **thực sự liên quan nhất** để đưa vào ngữ cảnh cho LLM.

**Lợi ích:**
-   **Giảm Hallucination:** Loại bỏ các đoạn văn bản nhiễu hoặc kém liên quan, giúp LLM tập trung hơn vào thông tin cốt lõi.
-   **Tăng tốc độ:** Giảm lượng token ngữ cảnh gửi lên LLM, giúp LLM xử lý nhanh hơn và giảm chi phí.

Nếu bạn muốn triển khai tính năng này, tôi có thể bắt đầu bằng cách thêm một `RerankerService` vào Backend.
