import os
from typing import Optional, Dict
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

class SemanticCacheService:
    def __init__(self, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", threshold: float = 0.85):
        """
        Khởi tạo Cache ngữ nghĩa.
        threshold: Ngưỡng độ tương đồng (0.0 đến 1.0). Càng cao càng khắt khe.
        """
        self.embeddings = HuggingFaceEmbeddings(model_name=model_name)
        self.threshold = threshold
        
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.cache_dir = os.path.join(base_dir, "data", "semantic_cache")
        self.cache_store: Optional[FAISS] = None
        
        self.load_cache()

    def check_cache(self, query: str) -> Optional[str]:
        """
        Kiểm tra xem câu hỏi có tương đồng với câu nào đã hỏi trước đó không.
        Trả về câu trả lời đã lưu nếu tìm thấy (điểm tương đồng > threshold).
        """
        if self.cache_store is None:
            return None
            
        try:
            # Tìm kiếm kèm điểm số tương đồng (distance)
            results = self.cache_store.similarity_search_with_score(query, k=1)
            if results:
                doc, distance = results[0]
                # Chuyển đổi distance (thường là L2 distance của FAISS) sang độ tương đồng
                # Với FAISS mặc định (L2), điểm càng thấp càng giống nhau. 
                # Ngưỡng (L2 distance) thông thường cho sự tương đồng cực cao là < 0.3
                if distance < (1.0 - self.threshold) * 2: 
                    return doc.metadata.get("answer")
        except Exception:
            pass
        return None

    def add_to_cache(self, query: str, answer: str):
        """
        Lưu câu hỏi và câu trả lời vào cache sau khi AI trả lời xong.
        """
        doc = Document(page_content=query, metadata={"answer": answer})
        
        if self.cache_store is None:
            self.cache_store = FAISS.from_documents([doc], self.embeddings)
        else:
            self.cache_store.add_documents([doc])
        
        self.save_cache()

    def save_cache(self):
        if self.cache_store:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.cache_store.save_local(self.cache_dir)

    def load_cache(self):
        if os.path.exists(self.cache_dir):
            try:
                self.cache_store = FAISS.load_local(self.cache_dir, self.embeddings, allow_dangerous_deserialization=True)
            except Exception:
                pass
