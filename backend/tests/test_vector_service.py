import os
import tempfile
import pytest
from app.services.vector_service import VectorService

def test_vector_service():
    service = VectorService()
    
    chunks = [
        {"text": "Quy trình an toàn bay số 1.", "metadata": {"subject": "An toàn bay", "source": "doc1.pdf"}},
        {"text": "Bảo dưỡng động cơ định kỳ.", "metadata": {"subject": "Kỹ thuật", "source": "doc2.pdf"}},
        {"text": "Phi công phải kiểm tra trang thiết bị.", "metadata": {"subject": "An toàn bay", "source": "doc3.pdf"}},
    ]
    
    # Test thêm document
    service.add_documents(chunks)
    assert service.vector_store is not None
    
    # Test tìm kiếm không filter
    res = service.search("an toàn", k=1)
    assert len(res) == 1
    assert "an toàn bay" in res[0].page_content.lower()
    
    # Test tìm kiếm có filter
    res_filtered = service.search("kiểm tra", subject="An toàn bay", k=2)
    assert len(res_filtered) > 0
    for doc in res_filtered:
        assert doc.metadata.get("subject") == "An toàn bay"
        
    # Test save và load local
    with tempfile.TemporaryDirectory() as tmpdirname:
        service.save_local(tmpdirname)
        assert os.path.exists(os.path.join(tmpdirname, "index.faiss"))
        
        new_service = VectorService()
        new_service.load_local(tmpdirname)
        assert new_service.vector_store is not None
        
        res_loaded = new_service.search("bảo dưỡng", k=1)
        assert len(res_loaded) == 1
        assert "bảo dưỡng" in res_loaded[0].page_content.lower()
