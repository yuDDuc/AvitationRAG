import json
import os
import shutil
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any

from app.services.document_service import DocumentService
from app.api.chat import vector_service
from app.api.chat import semantic_cache # Import semantic_cache để clear

router = APIRouter()
doc_service = DocumentService()

# Đường dẫn đến file metadata
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
METADATA_FILE = os.path.join(base_dir, "data", "document_metadata.json")

def _normalize_subject(subject_name: str) -> str:
    """Chuẩn hóa tên môn học về dạng chữ thường và bỏ khoảng trắng thừa."""
    return subject_name.strip().lower()

def _load_metadata() -> Dict[str, Any]:
    """Tải metadata từ file JSON."""
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"documents": []}

def _save_metadata(metadata: Dict[str, Any]):
    """Lưu metadata vào file JSON."""
    os.makedirs(os.path.dirname(METADATA_FILE), exist_ok=True)
    with open(METADATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

def _process_single_file_background(file_location: str, filename: str, normalized_subject: str):
    try:
        # 1. Trích xuất text (AI-F1.1)
        extracted_data = doc_service.extract_text(file_location)

        # 2. Chia nhỏ tài liệu (AI-F2)
        chunks = doc_service.chunk_text(extracted_data, common_metadata={
            "source": filename, 
            "subject": normalized_subject
        })

        # 3. Thêm vào Vector DB (AI-F3)
        vector_service.add_documents(chunks)

        # 4. Lưu index để sử dụng sau này
        vector_service.save_local(os.path.join(base_dir, "data", "vector_db"))

        # 5. Cập nhật metadata
        metadata_store = _load_metadata()
        if not any(d["filename"] == filename and d["subject"] == normalized_subject for d in metadata_store["documents"]):
            metadata_store["documents"].append({"filename": filename, "subject": normalized_subject})
        _save_metadata(metadata_store)
    except Exception as e:
        print(f"[Error processing {filename}]: {e}")

@router.post("/upload")
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject: str = Form(...)
):
    """
    Endpoint tải lên và xử lý 1 tài liệu trong nền (Background Task).
    """
    try:
        normalized_subject = _normalize_subject(subject)
        file_location = os.path.join(base_dir, "data", "docs", file.filename)
        os.makedirs(os.path.dirname(file_location), exist_ok=True)

        with open(file_location, "wb+") as file_object:
            shutil.copyfileobj(file.file, file_object)

        # Cập nhật metadata ngay lập tức để frontend thấy
        metadata_store = _load_metadata()
        if not any(d["filename"] == file.filename and d["subject"] == normalized_subject for d in metadata_store["documents"]):
            metadata_store["documents"].append({"filename": file.filename, "subject": normalized_subject})
        _save_metadata(metadata_store)

        background_tasks.add_task(_process_single_file_background, file_location, file.filename, normalized_subject)

        return {
            "message": f"Đang xử lý tài liệu '{file.filename}' trong nền. Vui lòng chờ vài phút.",
            "subject": normalized_subject
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi lưu tài liệu '{file.filename}': {str(e)}")

@router.post("/upload-batch")
async def upload_documents_batch(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    subject: str = Form(...)
):
    """
    Endpoint tải lên và xử lý hàng loạt tài liệu trong nền.
    """
    normalized_subject = _normalize_subject(subject)
    results = []
    for file in files:
        try:
            file_location = os.path.join(base_dir, "data", "docs", file.filename)
            os.makedirs(os.path.dirname(file_location), exist_ok=True)

            with open(file_location, "wb+") as file_object:
                shutil.copyfileobj(file.file, file_object)
            
            # Cập nhật metadata ngay lập tức
            metadata_store = _load_metadata()
            if not any(d["filename"] == file.filename and d["subject"] == normalized_subject for d in metadata_store["documents"]):
                metadata_store["documents"].append({"filename": file.filename, "subject": normalized_subject})
            _save_metadata(metadata_store)

            background_tasks.add_task(_process_single_file_background, file_location, file.filename, normalized_subject)
            results.append({"file": file.filename, "status": "processing"})
        except Exception as e:
            results.append({"file": file.filename, "status": "error", "message": str(e)})
    
    # Cập nhật metadata sau khi xử lý batch
    metadata_store = _load_metadata()
    for res in results:
        if res["status"] == "success":
            if not any(d["filename"] == res["file"] and d["subject"] == normalized_subject for d in metadata_store["documents"]):
                metadata_store["documents"].append({"filename": res["file"], "subject": normalized_subject})
    _save_metadata(metadata_store)

    return {
        "message": f"Đã hoàn thành xử lý {len(files)} tài liệu",
        "details": results
    }

class FolderIngestRequest(BaseModel):
    folder_path: str
    subject: str

def _process_folder_background(folder_path: str, normalized_subject: str, valid_extensions: tuple):
    files_to_process = [
        f for f in os.listdir(folder_path) 
        if f.lower().endswith(valid_extensions)
    ]

    results = []
    for filename in files_to_process:
        file_path = os.path.join(folder_path, filename)
        try:
            # Sao chép vào thư mục docs của backend để quản lý
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            dest_path = os.path.join(base_dir, "data", "docs", filename)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            shutil.copy2(file_path, dest_path)
            
            # Xử lý RAG
            extracted_data = doc_service.extract_text(dest_path)
            chunks = doc_service.chunk_text(extracted_data, common_metadata={"source": filename, "subject": normalized_subject})
            vector_service.add_documents(chunks)
            
            results.append({"file": filename, "status": "success", "chunks": len(chunks)})
        except Exception as e:
            results.append({"file": filename, "status": "error", "message": str(e)})

    # Lưu vector db sau khi xử lý xong toàn bộ
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    vector_service.save_local(os.path.join(base_dir, "data", "vector_db"))

    # Cập nhật metadata
    metadata_store = _load_metadata()
    for res in results:
        if res["status"] == "success":
            if not any(d["filename"] == res["file"] and d["subject"] == normalized_subject for d in metadata_store["documents"]):
                metadata_store["documents"].append({"filename": res["file"], "subject": normalized_subject})
    _save_metadata(metadata_store)

@router.post("/ingest-folder")
async def ingest_folder_from_path(request: FolderIngestRequest, background_tasks: BackgroundTasks):
    """
    Endpoint nạp toàn bộ tài liệu từ một đường dẫn thư mục local trên server (chạy ngầm).
    """
    normalized_subject = _normalize_subject(request.subject) # Chuẩn hóa subject từ request
    
    if not os.path.exists(request.folder_path):
        raise HTTPException(status_code=404, detail=f"Thư mục không tồn tại: {request.folder_path}")

    valid_extensions = ('.pdf', '.docx', '.pptx')
    files_to_process = [
        f for f in os.listdir(request.folder_path) 
        if f.lower().endswith(valid_extensions)
    ]

    if not files_to_process:
        return {"message": "Không tìm thấy file hợp lệ trong thư mục", "processed": 0}

    background_tasks.add_task(_process_folder_background, request.folder_path, normalized_subject, valid_extensions)

    return {
        "message": f"Đã tiếp nhận yêu cầu quét thư mục {request.folder_path}. Hệ thống đang xử lý ngầm (hãy kiểm tra lại sau ít phút).",
        "processed_count": len(files_to_process),
        "details": []
    }

@router.get("/")
async def list_documents():
    """
    Liệt kê danh sách tài liệu đã upload (AI-F1.3).
    """
    metadata_store = _load_metadata()
    # Kiểm tra xem file vật lý có còn tồn tại không
    # base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    # docs_dir = os.path.join(base_dir, "data", "docs")
    # if os.path.exists(docs_dir):
    #     existing_files = set(os.listdir(docs_dir))
    #     metadata_store["documents"] = [
    #         doc for doc in metadata_store["documents"] if doc["filename"] in existing_files
    #     ]
    #     _save_metadata(metadata_store) # Lưu lại nếu có thay đổi (file bị xóa thủ công)

    return {
        "total_count": len(metadata_store["documents"]),
        "documents": metadata_store["documents"]
    }

@router.post("/clear-semantic-cache")
async def clear_semantic_cache_api():
    """
    Xóa toàn bộ Semantic Cache đã lưu.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cache_dir = os.path.join(base_dir, "data", "semantic_cache")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
    # Re-initialize the cache service to ensure it starts clean
    from app.api.chat import semantic_cache
    semantic_cache.cache_store = None
    semantic_cache.load_cache() # Reloads (which will be empty now)
    return {"message": "Đã xóa toàn bộ Semantic Cache."}

@router.post("/clear-all-data")
async def clear_all_data_api():
    """
    Xóa toàn bộ tài liệu đã upload, Vector DB, Semantic Cache, Metadata và Lịch sử Chat.
    """
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 1. Xóa file metadata
    if os.path.exists(METADATA_FILE):
        os.remove(METADATA_FILE)
        
    # 2. Xóa các thư mục dữ liệu
    docs_dir = os.path.join(base_dir, "data", "docs")
    if os.path.exists(docs_dir):
        shutil.rmtree(docs_dir)
        os.makedirs(docs_dir)
        
    vector_db_dir = os.path.join(base_dir, "data", "vector_db")
    if os.path.exists(vector_db_dir):
        shutil.rmtree(vector_db_dir)
        os.makedirs(vector_db_dir)
    
    cache_dir = os.path.join(base_dir, "data", "semantic_cache")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        os.makedirs(cache_dir)
        
    chat_history_db = os.path.join(base_dir, "data", "chat_history.db")
    if os.path.exists(chat_history_db):
        os.remove(chat_history_db)

    # 3. Re-initialize services một cách an toàn
    from app.api.chat import vector_service, semantic_cache
    try:
        vector_service.vector_store = None
        vector_service.load_local(vector_db_dir)
    except Exception:
        pass # Chấp nhận vì db đang trống
        
    try:
        semantic_cache.cache_store = None
        semantic_cache.load_cache()
    except Exception:
        pass
        
    try:
        from app.api.chat_history import chat_history_service
        chat_history_service._init_db()
    except Exception:
        pass

    return {"message": "Đã xóa sạch toàn bộ tài liệu, metadata, Vector DB, Semantic Cache và Lịch sử Chat."}

@router.delete("/{subject}")
async def delete_subject_documents(subject: str):
    """
    Xóa tất cả tài liệu và vector thuộc một môn học cụ thể (AI-F3.5).
    """
    normalized_subject = _normalize_subject(subject)
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    docs_dir = os.path.join(base_dir, "data", "docs")

    # 1. Tải và cập nhật metadata
    metadata_store = _load_metadata()

    # Lọc ra những tài liệu KHÔNG thuộc môn học bị xóa
    updated_docs = [d for d in metadata_store["documents"] if d["subject"] != normalized_subject]
    deleted_docs = [d for d in metadata_store["documents"] if d["subject"] == normalized_subject]

    if not deleted_docs:
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tài liệu nào thuộc môn học: {subject}")

    # 2. Xóa file vật lý
    for doc in deleted_docs:
        file_path = os.path.join(docs_dir, doc["filename"])
        if os.path.exists(file_path):
            os.remove(file_path)

    # 3. Lưu metadata mới
    metadata_store["documents"] = updated_docs
    _save_metadata(metadata_store)

    # 4. Tái tạo lại Vector Index (Re-index)
    # FAISS không hỗ trợ xóa theo filter hiệu quả, nên cách tốt nhất là rebuild từ các file còn lại
    from app.api.chat import vector_service
    vector_service.clear() # Xóa index hiện tại trong memory

    # Quét lại toàn bộ file còn lại trong docs_dir và nạp lại
    if os.path.exists(docs_dir):
        all_files = os.listdir(docs_dir)
        for filename in all_files:
            # Tìm subject của file này trong metadata mới
            doc_info = next((d for d in updated_docs if d["filename"] == filename), None)
            if doc_info:
                file_path = os.path.join(docs_dir, filename)
                extracted_data = doc_service.extract_text(file_path)
                chunks = doc_service.chunk_text(extracted_data, common_metadata={
                    "source": filename, 
                    "subject": doc_info["subject"]
                })
                vector_service.add_documents(chunks)

    # Lưu lại index mới xuống đĩa
    vector_service.save_local(os.path.join(base_dir, "data", "vector_db"))

    return {
        "message": f"Đã xóa thành công {len(deleted_docs)} tài liệu thuộc môn học '{subject}' và cập nhật lại Vector Index.",
        "deleted_count": len(deleted_docs)
    }